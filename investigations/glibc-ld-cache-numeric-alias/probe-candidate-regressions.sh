#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
patch_file=${2:-}
if [[ -z "$output_dir" || -z "$patch_file" ]]; then
  printf 'usage: %s OUTPUT_DIR CANDIDATE_PATCH\n' "$0" >&2
  exit 64
fi

for command in git make bison gawk python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  fi
done

readonly glibc_repository=https://github.com/gnutools/glibc.git
readonly glibc_commit=6288139c32a194e0005593c30af6c79bb698cdf2

patch_file=$(cd "$(dirname "$patch_file")" && pwd -P)/$(basename "$patch_file")
if [[ ! -f "$patch_file" ]]; then
  printf 'candidate patch is unavailable\n' >&2
  exit 66
fi

work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-alias-regressions.XXXXXX")
cleanup() {
  chmod -R u+rwX "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
stage="$output_dir/stage.txt"
src="$work_root/glibc-src"
build="$work_root/glibc-build"
etc_dir="$work_root/etc"
mkdir -p "$src" "$build" "$etc_dir"

printf 'source_fetch\n' >"$stage"
git -C "$src" init -q
git -C "$src" remote add origin "$glibc_repository"
git -C "$src" -c protocol.version=2 fetch -q --depth=1 origin "$glibc_commit"
git -C "$src" checkout -q --detach FETCH_HEAD
[[ $(git -C "$src" rev-parse HEAD) == "$glibc_commit" ]]

printf 'candidate_apply\n' >"$stage"
git -C "$src" apply --check "$patch_file"
git -C "$src" apply "$patch_file"
git -C "$src" diff --check

git -C "$src" diff -- elf/dl-cache.c >"$output_dir/candidate.diff"

printf 'configure\n' >"$stage"
if ! (cd "$build" && "$src/configure" \
  --prefix=/usr \
  --sysconfdir="$etc_dir" \
  --disable-werror \
  >"$output_dir/configure.log" 2>&1); then
  tail -n 120 "$output_dir/configure.log" >&2 || true
  exit 1
fi

build_jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '2')
printf 'build\n' >"$stage"
if ! make -C "$build" -j"$build_jobs" >"$output_dir/build.log" 2>&1; then
  tail -n 160 "$output_dir/build.log" >&2 || true
  exit 1
fi

run_test() {
  local test_name=$1
  local safe_name=${test_name//\//-}
  printf 'test:%s\n' "$test_name" >"$stage"
  if ! make -C "$build" test "t=$test_name" \
    >"$output_dir/$safe_name.log" 2>&1; then
    tail -n 160 "$output_dir/$safe_name.log" >&2 || true
    return 1
  fi
}

run_test elf/tst-ldconfig-cache
run_test elf/tst-glibc-hwcaps-prepend-cache

{
  printf 'classification\tcandidate_regressions_passed\n'
  printf 'glibc_commit\t%s\n' "$glibc_commit"
  printf 'test\telf/tst-ldconfig-cache\tpass\n'
  printf 'test\telf/tst-glibc-hwcaps-prepend-cache\tpass\n'
} >"$output_dir/summary.tsv"
printf 'complete\n' >"$stage"
cat "$output_dir/summary.tsv"
