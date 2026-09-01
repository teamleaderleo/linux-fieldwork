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

as_root() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -E "$@"
  else
    printf 'root-capable test execution is unavailable\n' >&2
    return 69
  fi
}

readonly glibc_repository=https://github.com/gnutools/glibc.git
readonly glibc_commit=6288139c32a194e0005593c30af6c79bb698cdf2

patch_file=$(cd "$(dirname "$patch_file")" && pwd -P)/$(basename "$patch_file")
if [[ ! -f "$patch_file" ]]; then
  printf 'candidate patch is unavailable\n' >&2
  exit 66
fi

work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-alias-regressions.XXXXXX")
cleanup() {
  as_root chmod -R u+rwX "$work_root" 2>/dev/null || true
  as_root chown -R "$(id -u):$(id -g)" "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
stage="$output_dir/stage.txt"
src="$work_root/glibc-src"
build="$work_root/glibc-build"
mkdir -p "$src" "$build"

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
  --sysconfdir=/etc \
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

printf 'testroot_init\n' >"$stage"
testroot_stamp="$build/testroot.pristine/install.stamp"
if ! make -C "$build" "$testroot_stamp" >"$output_dir/testroot.log" 2>&1; then
  tail -n 160 "$output_dir/testroot.log" >&2 || true
  exit 1
fi

run_test() {
  local test_name=$1
  local test_base=${test_name#elf/}
  local safe_name=${test_name//\//-}
  local result_file="$build/elf/$test_base.test-result"
  local out_file="$build/elf/$test_base.out"

  printf 'test:%s\n' "$test_name" >"$stage"
  as_root rm -f -- "$result_file" "$out_file"
  set +e
  as_root make -C "$build" test "t=$test_name" >"$output_dir/$safe_name.log" 2>&1
  local make_status=$?
  set -e

  if [[ ! -f "$result_file" ]]; then
    printf 'glibc did not produce a result for %s (make status %d)\n' \
      "$test_name" "$make_status" >&2
    tail -n 160 "$output_dir/$safe_name.log" >&2 || true
    return 1
  fi
  cp "$result_file" "$output_dir/$safe_name.test-result.txt"
  if [[ -f "$out_file" ]]; then
    cp "$out_file" "$output_dir/$safe_name.out.txt"
  fi
  if ! grep -Fqx "PASS: $test_name" "$result_file"; then
    printf 'glibc regression failed: %s\n' "$test_name" >&2
    cat "$result_file" >&2
    tail -n 160 "$out_file" >&2 2>/dev/null || true
    return 1
  fi
}

run_test elf/tst-ldconfig-cache
run_test elf/tst-glibc-hwcaps-prepend-cache

{
  printf 'classification\tcandidate_regressions_passed\n'
  printf 'glibc_commit\t%s\n' "$glibc_commit"
  printf 'execution_uid\t%s\n' "$(id -u)"
  printf 'sysconfdir\t/etc\n'
  printf 'test\telf/tst-ldconfig-cache\tpass\n'
  printf 'test\telf/tst-glibc-hwcaps-prepend-cache\tpass\n'
} >"$output_dir/summary.tsv"
printf 'complete\n' >"$stage"
cat "$output_dir/summary.tsv"
