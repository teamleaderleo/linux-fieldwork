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
readonly test_name=elf/tst-ld-cache-name-identity
readonly test_base=tst-ld-cache-name-identity

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

printf 'testroot_init\n' >"$stage"
testroot_stamp="$build/testroot.pristine/install.stamp"
if ! make -C "$build" "$testroot_stamp" >"$output_dir/testroot.log" 2>&1; then
  tail -n 160 "$output_dir/testroot.log" >&2 || true
  exit 1
fi

run_test() {
  local label=$1
  local result_file="$build/elf/$test_base.test-result"
  local out_file="$build/elf/$test_base.out"

  rm -f -- "$result_file" "$out_file"
  set +e
  make -C "$build" test "t=$test_name" >"$output_dir/$label-make.log" 2>&1
  local make_status=$?
  set -e

  if [[ ! -f "$result_file" ]]; then
    printf 'glibc did not produce %s test result (make status %d)\n' \
      "$label" "$make_status" >&2
    tail -n 160 "$output_dir/$label-make.log" >&2 || true
    return 2
  fi

  cp "$result_file" "$output_dir/$label-test-result.txt"
  if [[ -f "$out_file" ]]; then
    cp "$out_file" "$output_dir/$label-test-output.txt"
  fi
  printf '%s\tmake_status\t%d\n' "$label" "$make_status" >>"$output_dir/test-status.tsv"
}

: >"$output_dir/test-status.tsv"
printf 'baseline_test\n' >"$stage"
run_test baseline
if ! grep -Fqx "FAIL: $test_name" "$output_dir/baseline-test-result.txt"; then
  printf 'native regression did not fail on baseline\n' >&2
  cat "$output_dir/baseline-test-result.txt" >&2
  tail -n 120 "$output_dir/baseline-test-output.txt" >&2 2>/dev/null || true
  exit 1
fi
if grep -Fq 'Cannot create testroot lock' "$output_dir/baseline-test-output.txt" 2>/dev/null; then
  printf 'baseline failed in container setup instead of the cache identity assertion\n' >&2
  exit 1
fi

printf 'candidate_apply\n' >"$stage"
git -C "$src" apply --check "$candidate_patch"
git -C "$src" apply "$candidate_patch"
git -C "$src" diff --check
git -C "$src" diff >"$output_dir/candidate-with-regression.diff"

# `make test t=...` rebuilds the test itself but deliberately does not rebuild
# ordinary library objects. Rebuild the current glibc tree so the changed
# loader participates in the candidate run.
printf 'candidate_rebuild\n' >"$stage"
if ! make -C "$build" -j"$build_jobs" >"$output_dir/candidate-build.log" 2>&1; then
  tail -n 160 "$output_dir/candidate-build.log" >&2 || true
  exit 1
fi

printf 'candidate_test\n' >"$stage"
run_test candidate
if ! grep -Fqx "PASS: $test_name" "$output_dir/candidate-test-result.txt"; then
  printf 'native regression did not pass with exact-key candidate\n' >&2
  cat "$output_dir/candidate-test-result.txt" >&2
  tail -n 160 "$output_dir/candidate-test-output.txt" >&2 2>/dev/null || true
  exit 1
fi

{
  printf 'classification\tnative_regression_distinguishes_candidate\n'
  printf 'glibc_commit\t%s\n' "$glibc_commit"
  printf 'baseline_test\tfail_as_expected\n'
  printf 'candidate_test\tpass\n'
} >"$output_dir/summary.tsv"
printf 'complete\n' >"$stage"
cat "$output_dir/summary.tsv"
