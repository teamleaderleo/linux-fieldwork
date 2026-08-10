#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
if [[ -z "$output_dir" ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 64
fi

for command in cc git make bison gawk python3 strings grep; do
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

work_root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/glibc-cache-overflow-current.XXXXXX")
cleanup() {
  chmod -R u+rwX "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
summary="$output_dir/current-cache-summary.tsv"
environment="$output_dir/current-cache-environment.txt"
stage="$output_dir/current-cache-stage.txt"

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

current_ldconfig="$build/elf/ldconfig"
current_loader="$build/elf/ld.so"
testrun="$build/testrun.sh"
for path in "$current_ldconfig" "$current_loader" "$testrun"; do
  [[ -x "$path" ]] || {
    printf 'expected current glibc build output is unavailable\n' >&2
    exit 69
  }
done

printf 'private_cache_check\n' >"$stage"
if ! strings "$current_loader" | grep -Fqx "$etc_dir/ld.so.cache"; then
  printf 'current loader does not contain the expected private cache identity\n' >&2
  exit 65
fi

{
  printf 'uname=%s\n' "$(uname -a)"
  printf 'glibc_repository=%s\n' "$glibc_repository"
  printf 'glibc_commit=%s\n' "$glibc_commit"
  printf 'cc=%s\n' "$(cc --version | head -n 1)"
  printf 'make=%s\n' "$(make --version | head -n 1)"
  printf 'private_cache_bound=true\n'
} >"$environment"

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

make_cache() {
  local label=$1
  shift

  printf '%s\n' "$@" >"$etc_dir/ld.so.conf"
  rm -f -- "$etc_dir/ld.so.cache"
  "$current_ldconfig" -i -C "$etc_dir/ld.so.cache" -f "$etc_dir/ld.so.conf"
  [[ -f "$etc_dir/ld.so.cache" ]]
  "$current_ldconfig" -C "$etc_dir/ld.so.cache" -p >"$output_dir/current-cache-$label.txt"
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
      printf 'current-head probe returned unexpected status %d for %s\n' \
        "$status" "$name" >&2
      cat "$stderr_file" >&2 || true
      exit "$status"
      ;;
  esac
}

printf 'cache_matrix\n' >"$stage"
printf 'root\trequest\tresult\n' >"$summary"
for label in abcd dcba; do
  if [[ "$label" == abcd ]]; then
    make_cache "$label" "$lib_a" "$lib_b" "$lib_c" "$lib_d"
  else
    make_cache "$label" "$lib_d" "$lib_c" "$lib_b" "$lib_a"
  fi

  for name in \
    libwide.so.0 \
    libwide.so.1 \
    libwide.so.2147483648 \
    libwide.so.4294967296 \
    libwide.so.8589934592 \
    libwide.so.2 \
    libcontrol.so.1; do
    result=$(query "$name" "$work_root/$label-${name}.stderr")
    printf '%s\t%s\t%s\n' "$label" "$name" "$result" >>"$summary"
  done
done

lookup() {
  local label=$1
  local name=$2
  awk -F '\t' -v label="$label" -v name="$name" \
    '$1 == label && $2 == name { print $3; exit }' "$summary"
}

for label in abcd dcba; do
  [[ $(lookup "$label" libcontrol.so.1) == 401 ]]
done

classification=cache_lookup_stable_under_fixture
for label in abcd dcba; do
  [[ $(lookup "$label" libwide.so.0) == 100 ]] \
    || classification=overflow_cache_identity_or_lookup_effect_reproduced
  [[ $(lookup "$label" libwide.so.1) == 101 ]] \
    || classification=overflow_cache_identity_or_lookup_effect_reproduced
  [[ $(lookup "$label" libwide.so.2147483648) == 102 ]] \
    || classification=overflow_cache_identity_or_lookup_effect_reproduced
  [[ $(lookup "$label" libwide.so.4294967296) == 103 ]] \
    || classification=overflow_cache_identity_or_lookup_effect_reproduced
  [[ $(lookup "$label" libwide.so.8589934592) == MISSING ]] \
    || classification=overflow_cache_identity_or_lookup_effect_reproduced
  [[ $(lookup "$label" libwide.so.2) == MISSING ]] \
    || classification=overflow_cache_identity_or_lookup_effect_reproduced
done

printf 'classification\t%s\n' "$classification" >>"$summary"
printf 'complete\n' >"$stage"
cat "$summary"
