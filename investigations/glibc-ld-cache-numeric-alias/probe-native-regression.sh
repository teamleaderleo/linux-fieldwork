#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
regression_patch=${2:-}
candidate_patch=${3:-}
if [[ -z "$output_dir" || -z "$regression_patch" || -z "$candidate_patch" ]]; then
  printf 'usage: %s OUTPUT_DIR REGRESSION_PATCH CANDIDATE_PATCH\n' "$0" >&2
  exit 64
fi

for command in git make bison gawk python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  fi
done

if [[ $(uname -m) != x86_64 ]]; then
  printf 'this current-head fixture is intentionally x86_64-only\n' >&2
  exit 77
fi

readonly glibc_repository=https://github.com/gnutools/glibc.git
readonly glibc_commit=6288139c32a194e0005593c30af6c79bb698cdf2

regression_patch=$(cd "$(dirname "$regression_patch")" && pwd -P)/$(basename "$regression_patch")
candidate_patch=$(cd "$(dirname "$candidate_patch")" && pwd -P)/$(basename "$candidate_patch")
for path in "$regression_patch" "$candidate_patch"; do
  if [[ ! -f "$path" ]]; then
    printf 'required patch is unavailable\n' >&2
    exit 66
  fi
done

work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-alias-native.XXXXXX")
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
mkdir -p "$src" "$build"

printf 'source_fetch\n' >"$stage"
git -C "$src" init -q
git -C "$src" remote add origin "$glibc_repository"
git -C "$src" -c protocol.version=2 fetch -q --depth=1 origin "$glibc_commit"
git -C "$src" checkout -q --detach FETCH_HEAD
[[ $(git -C "$src" rev-parse HEAD) == "$glibc_commit" ]]

printf 'regression_apply\n' >"$stage"
git -C "$src" apply --check "$regression_patch"
git -C "$src" apply "$regression_patch"
git -C "$src" diff --check
git -C "$src" diff >"$output_dir/regression.diff"

printf 'configure\n' >"$stage"
if ! (cd "$build" && "$src/configure" --prefix=/usr --disable-werror \
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

printf 'baseline_test\n' >"$stage"
set +e
make -C "$build" test t=elf/tst-ld-cache-name-identity \
  >"$output_dir/baseline-test.log" 2>&1
baseline_status=$?
set -e
if [[ "$baseline_status" -eq 0 ]]; then
  printf 'native regression unexpectedly passed on baseline\n' >&2
  tail -n 120 "$output_dir/baseline-test.log" >&2 || true
  exit 1
fi

printf 'candidate_apply\n' >"$stage"
git -C "$src" apply --check "$candidate_patch"
git -C "$src" apply "$candidate_patch"
git -C "$src" diff --check
git -C "$src" diff >"$output_dir/candidate-with-regression.diff"

rm -f -- \
  "$build/elf/tst-ld-cache-name-identity.out" \
  "$build/elf/tst-ld-cache-name-identity.test-result"

printf 'candidate_test\n' >"$stage"
if ! make -C "$build" -j"$build_jobs" test t=elf/tst-ld-cache-name-identity \
  >"$output_dir/candidate-test.log" 2>&1; then
  tail -n 160 "$output_dir/candidate-test.log" >&2 || true
  exit 1
fi

{
  printf 'classification\tnative_regression_distinguishes_candidate\n'
  printf 'glibc_commit\t%s\n' "$glibc_commit"
  printf 'baseline_status\t%s\n' "$baseline_status"
  printf 'candidate_test\tpass\n'
} >"$output_dir/summary.tsv"
printf 'complete\n' >"$stage"
cat "$output_dir/summary.tsv"
