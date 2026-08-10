#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
candidate_patch=${2:-}
if [[ -z "$output_dir" || -z "$candidate_patch" ]]; then
  printf 'usage: %s OUTPUT_DIR CANDIDATE_PATCH\n' "$0" >&2
  exit 64
fi

for command in cc git make bison gawk python3 strings grep sha256sum; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  fi
done

if [[ $(uname -m) != x86_64 ]]; then
  printf 'this mixed-generation fixture is intentionally x86_64-only\n' >&2
  exit 77
fi

candidate_patch=$(cd "$(dirname "$candidate_patch")" && pwd -P)/$(basename "$candidate_patch")
if [[ ! -f "$candidate_patch" ]]; then
  printf 'candidate patch is unavailable\n' >&2
  exit 66
fi

readonly glibc_repository=https://github.com/gnutools/glibc.git
readonly glibc_commit=6288139c32a194e0005593c30af6c79bb698cdf2

work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-overflow-mixed.XXXXXX")
cleanup() {
  chmod -R u+rwX "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
summary="$output_dir/mixed-generation-summary.tsv"
stage="$output_dir/mixed-generation-stage.txt"
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

printf 'baseline_configure\n' >"$stage"
if ! (cd "$build" && "$src/configure" \
  --prefix=/usr \
  --sysconfdir="$etc_dir" \
  --disable-werror \
  >"$output_dir/configure.log" 2>&1); then
  tail -n 120 "$output_dir/configure.log" >&2 || true
  exit 1
fi

build_jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '2')
printf 'baseline_build\n' >"$stage"
if ! make -C "$build" -j"$build_jobs" >"$output_dir/baseline-build.log" 2>&1; then
  tail -n 160 "$output_dir/baseline-build.log" >&2 || true
  exit 1
fi

current_ldconfig="$build/elf/ldconfig"
current_loader="$build/elf/ld.so"
testrun="$build/testrun.sh"
for path in "$current_ldconfig" "$current_loader" "$testrun"; do
  [[ -x "$path" ]] || {
    printf 'expected current glibc build output is unavailable\n' >&2
    exit 69
  }
done
if ! strings "$current_loader" | grep -Fqx "$etc_dir/ld.so.cache"; then
  printf 'loader does not contain the expected private cache identity\n' >&2
  exit 65
fi

printf 'fixture_build\n' >"$stage"
cat >"$work_root/zero.c" <<'EOF'
int marker(void) { return 100; }
EOF
cat >"$work_root/one.c" <<'EOF'
int marker(void) { return 101; }
EOF
cat >"$work_root/int-over.c" <<'EOF'
int marker(void) { return 102; }
EOF
cat >"$work_root/u32-wrap.c" <<'EOF'
int marker(void) { return 103; }
EOF
cat >"$work_root/control.c" <<'EOF'
int marker(void) { return 401; }
EOF
cat >"$work_root/probe.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc != 2)
        return 64;
    dlerror();
    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        puts("MISSING");
        return 3;
    }
    int (*marker)(void) = (int (*)(void)) dlsym(handle, "marker");
    const char *error = dlerror();
    if (error != NULL || marker == NULL) {
        puts("NO_MARKER");
        return 4;
    }
    printf("%d\n", marker());
    if (dlclose(handle) != 0)
        return 5;
    return 0;
}
EOF

lib_a="$work_root/lib-a"
lib_b="$work_root/lib-b"
lib_c="$work_root/lib-c"
lib_d="$work_root/lib-d"
mkdir -p "$lib_a" "$lib_b" "$lib_c" "$lib_d"
cc -shared -fPIC -Wl,-soname,libwide.so.0 \
  "$work_root/zero.c" -o "$lib_a/libwide-zero.so.0.0"
cc -shared -fPIC -Wl,-soname,libwide.so.1 \
  "$work_root/one.c" -o "$lib_b/libwide-one.so.1.0"
cc -shared -fPIC -Wl,-soname,libwide.so.2147483648 \
  "$work_root/int-over.c" -o "$lib_c/libwide-int-over.so.2147483648.0"
cc -shared -fPIC -Wl,-soname,libwide.so.4294967296 \
  "$work_root/u32-wrap.c" -o "$lib_d/libwide-u32-wrap.so.4294967296.0"
cc -shared -fPIC -Wl,-soname,libcontrol.so.1 \
  "$work_root/control.c" -o "$lib_a/libcontrol.so.1.0"
cc -Wall -Wextra -Werror "$work_root/probe.c" -ldl -o "$work_root/probe"

write_conf() {
  local order=$1
  if [[ "$order" == abcd ]]; then
    printf '%s\n%s\n%s\n%s\n' "$lib_a" "$lib_b" "$lib_c" "$lib_d" \
      >"$etc_dir/ld.so.conf"
  else
    printf '%s\n%s\n%s\n%s\n' "$lib_d" "$lib_c" "$lib_b" "$lib_a" \
      >"$etc_dir/ld.so.conf"
  fi
}

generate_cache() {
  local order=$1
  local listing=$2
  write_conf "$order"
  rm -f -- "$etc_dir/ld.so.cache"
  "$current_ldconfig" -i -C "$etc_dir/ld.so.cache" -f "$etc_dir/ld.so.conf"
  [[ -f "$etc_dir/ld.so.cache" ]]
  "$current_ldconfig" -C "$etc_dir/ld.so.cache" -p >"$listing"
}

query() {
  local name=$1
  local stderr_file=$2
  local result status
  set +e
  result=$(env -i PATH=/usr/bin:/bin "$testrun" "$work_root/probe" "$name" \
    2>"$stderr_file")
  status=$?
  set -e
  case "$status" in
    0) printf '%s' "$result" ;;
    3) printf 'MISSING' ;;
    *)
      printf 'probe returned unexpected status %d for %s\n' "$status" "$name" >&2
      cat "$stderr_file" >&2 || true
      exit "$status"
      ;;
  esac
}

record_queries() {
  local phase=$1
  local order=$2
  for name in \
    libwide.so.0 \
    libwide.so.1 \
    libwide.so.2147483648 \
    libwide.so.4294967296 \
    libwide.so.8589934592 \
    libwide.so.2 \
    libcontrol.so.1; do
    result=$(query "$name" "$work_root/$phase-$order-${name}.stderr")
    printf '%s\t%s\t%s\t%s\n' "$phase" "$order" "$name" "$result" >>"$summary"
  done
}

printf 'phase\torder\trequest\tresult\n' >"$summary"
printf 'legacy_cache_generation\n' >"$stage"
for order in abcd dcba; do
  generate_cache "$order" "$output_dir/legacy-$order-listing.txt"
  cp "$etc_dir/ld.so.cache" "$output_dir/legacy-$order.cache"
  sha256sum "$output_dir/legacy-$order.cache" >"$output_dir/legacy-$order.sha256"
  record_queries baseline "$order"
done

printf 'candidate_apply\n' >"$stage"
git -C "$src" apply --check "$candidate_patch"
git -C "$src" apply "$candidate_patch"
git -C "$src" diff --check
git -C "$src" diff -- elf/dl-cache.c >"$output_dir/candidate.diff"

printf 'candidate_rebuild\n' >"$stage"
if ! make -C "$build" -j"$build_jobs" >"$output_dir/candidate-build.log" 2>&1; then
  tail -n 160 "$output_dir/candidate-build.log" >&2 || true
  exit 1
fi

printf 'legacy_cache_candidate_lookup\n' >"$stage"
for order in abcd dcba; do
  cp "$output_dir/legacy-$order.cache" "$etc_dir/ld.so.cache"
  expected_hash=$(cut -d' ' -f1 "$output_dir/legacy-$order.sha256")
  actual_hash=$(sha256sum "$etc_dir/ld.so.cache" | cut -d' ' -f1)
  [[ "$actual_hash" == "$expected_hash" ]]
  record_queries candidate_legacy_cache "$order"
done

printf 'fresh_candidate_cache_lookup\n' >"$stage"
for order in abcd dcba; do
  generate_cache "$order" "$output_dir/candidate-$order-listing.txt"
  record_queries candidate_fresh_cache "$order"
done

lookup() {
  local phase=$1
  local order=$2
  local name=$3
  awk -F '\t' -v phase="$phase" -v order="$order" -v name="$name" \
    '$1 == phase && $2 == order && $3 == name { print $4; exit }' "$summary"
}

phase_is_exact() {
  local phase=$1
  local order
  for order in abcd dcba; do
    [[ $(lookup "$phase" "$order" libwide.so.0) == 100 ]] || return 1
    [[ $(lookup "$phase" "$order" libwide.so.1) == 101 ]] || return 1
    [[ $(lookup "$phase" "$order" libwide.so.2147483648) == 102 ]] || return 1
    [[ $(lookup "$phase" "$order" libwide.so.4294967296) == 103 ]] || return 1
    [[ $(lookup "$phase" "$order" libwide.so.8589934592) == MISSING ]] || return 1
    [[ $(lookup "$phase" "$order" libwide.so.2) == MISSING ]] || return 1
    [[ $(lookup "$phase" "$order" libcontrol.so.1) == 401 ]] || return 1
  done
}

fresh_candidate=not_exact
if phase_is_exact candidate_fresh_cache; then
  fresh_candidate=exact
fi
legacy_candidate=incompatible
if phase_is_exact candidate_legacy_cache; then
  legacy_candidate=exact
fi

printf 'candidate_fresh_cache\t%s\n' "$fresh_candidate" >>"$summary"
printf 'candidate_legacy_cache\t%s\n' "$legacy_candidate" >>"$summary"
if [[ "$fresh_candidate" != exact ]]; then
  printf 'candidate failed its same-generation control\n' >&2
  cat "$summary" >&2
  exit 1
fi

if [[ "$legacy_candidate" == exact ]]; then
  printf 'classification\tlegacy_cache_compatible_with_candidate\n' >>"$summary"
else
  printf 'classification\tlegacy_cache_incompatible_with_candidate\n' >>"$summary"
fi
printf 'complete\n' >"$stage"
cat "$summary"
