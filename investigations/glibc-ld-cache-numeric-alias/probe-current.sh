#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
if [[ -z "$output_dir" ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 64
fi

for command in cc git make bison gawk python3; do
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

work_parent=${RUNNER_TEMP:-/tmp}
work_root=$(mktemp -d "$work_parent/glibc-cache-numeric-alias-current.XXXXXX")
cleanup() {
  chmod -R u+rwX "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
summary="$output_dir/summary-current.tsv"
environment="$output_dir/environment-current.txt"
cache_listing_ab="$output_dir/cache-current-ab.txt"
cache_listing_ba="$output_dir/cache-current-ba.txt"

src="$work_root/glibc-src"
build="$work_root/glibc-build"
etc_dir="$work_root/etc"
mkdir -p "$src" "$build" "$etc_dir"

git -C "$src" init -q
git -C "$src" remote add origin "$glibc_repository"
git -C "$src" -c protocol.version=2 fetch -q --depth=1 origin "$glibc_commit"
git -C "$src" checkout -q --detach FETCH_HEAD
observed_commit=$(git -C "$src" rev-parse HEAD)
if [[ "$observed_commit" != "$glibc_commit" ]]; then
  printf 'glibc source identity mismatch\n' >&2
  exit 65
fi

if ! "$src/configure" \
  --prefix=/usr \
  --sysconfdir="$etc_dir" \
  --disable-werror \
  >"$work_root/configure.log" 2>&1; then
  tail -n 120 "$work_root/configure.log" >&2 || true
  exit 1
fi

build_jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '2')
if ! make -C "$build" -j"$build_jobs" >"$work_root/build.log" 2>&1; then
  tail -n 160 "$work_root/build.log" >&2 || true
  exit 1
fi

current_ldconfig="$build/elf/ldconfig"
current_loader="$build/elf/ld.so"
testrun="$build/testrun.sh"
for path in "$current_ldconfig" "$current_loader" "$testrun"; do
  if [[ ! -x "$path" ]]; then
    printf 'expected current glibc build output is unavailable\n' >&2
    exit 69
  fi
done

# Prove that this loader was built to consult only the private cache path used by
# this fixture rather than the hosted runner's /etc/ld.so.cache.
if ! strings "$current_loader" | grep -Fqx "$etc_dir/ld.so.cache"; then
  printf 'current loader does not contain the expected private cache identity\n' >&2
  exit 65
fi

{
  printf 'uname=%s\n' "$(uname -a)"
  printf 'glibc_repository=%s\n' "$glibc_repository"
  printf 'glibc_commit=%s\n' "$observed_commit"
  printf 'cc=%s\n' "$(cc --version | head -n 1)"
  printf 'make=%s\n' "$(make --version | head -n 1)"
  printf 'build_jobs=%s\n' "$build_jobs"
  printf 'private_cache_bound=true\n'
} >"$environment"

cat >"$work_root/alias-a.c" <<'EOF'
int marker(void) { return 101; }
EOF
cat >"$work_root/alias-b.c" <<'EOF'
int marker(void) { return 202; }
EOF
cat >"$work_root/control-a.c" <<'EOF'
int marker(void) { return 301; }
EOF
cat >"$work_root/control-b.c" <<'EOF'
int marker(void) { return 302; }
EOF
cat >"$work_root/probe.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        return 64;
    }

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
    if (dlclose(handle) != 0) {
        return 5;
    }
    return 0;
}
EOF

lib_a="$work_root/lib-a"
lib_b="$work_root/lib-b"
mkdir -p "$lib_a" "$lib_b"

cc -shared -fPIC -Wl,-soname,libalias.so.1 \
  "$work_root/alias-a.c" -o "$lib_a/libalias-a.so.1.0"
cc -shared -fPIC -Wl,-soname,libalias.so.01 \
  "$work_root/alias-b.c" -o "$lib_b/libalias-b.so.1.0"
cc -shared -fPIC -Wl,-soname,libcontrol.so.1 \
  "$work_root/control-a.c" -o "$lib_a/libcontrol-a.so.1.0"
cc -shared -fPIC -Wl,-soname,libcontrol.so.2 \
  "$work_root/control-b.c" -o "$lib_b/libcontrol-b.so.2.0"
cc -Wall -Wextra -Werror "$work_root/probe.c" -ldl -o "$work_root/probe"

make_cache() {
  local first=$1
  local second=$2
  local listing=$3

  printf '%s\n%s\n' "$first" "$second" >"$etc_dir/ld.so.conf"
  rm -f -- "$etc_dir/ld.so.cache"
  "$current_ldconfig" -i -C "$etc_dir/ld.so.cache" -f "$etc_dir/ld.so.conf"
  if [[ ! -f "$etc_dir/ld.so.cache" ]]; then
    printf 'current ldconfig did not create the private cache\n' >&2
    exit 65
  fi
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
    0)
      printf '%s' "$result"
      ;;
    3)
      printf 'MISSING'
      ;;
    *)
      printf 'current-head probe returned unexpected status %d for %s\n' \
        "$status" "$name" >&2
      cat "$stderr_file" >&2 || true
      exit "$status"
      ;;
  esac
}

lookup() {
  local label=$1
  local name=$2
  awk -F '\t' -v label="$label" -v name="$name" \
    '$1 == label && $2 == name { print $3; exit }' "$summary"
}

printf 'root\trequest\tresult\n' >"$summary"
for label in ab ba; do
  if [[ "$label" == ab ]]; then
    make_cache "$lib_a" "$lib_b" "$cache_listing_ab"
  else
    make_cache "$lib_b" "$lib_a" "$cache_listing_ba"
  fi

  for name in \
    libalias.so.1 \
    libalias.so.01 \
    libalias.so.001 \
    libalias.so.2 \
    libcontrol.so.1 \
    libcontrol.so.2; do
    stderr_file="$work_root/$label-${name//\//_}.stderr"
    result=$(query "$name" "$stderr_file")
    printf '%s\t%s\t%s\n' "$label" "$name" "$result" >>"$summary"
  done
done

for label in ab ba; do
  [[ $(lookup "$label" libcontrol.so.1) == 301 ]]
  [[ $(lookup "$label" libcontrol.so.2) == 302 ]]
  [[ $(lookup "$label" libalias.so.2) == MISSING ]]
done

ab_one=$(lookup ab libalias.so.1)
ab_zero_one=$(lookup ab libalias.so.01)
ab_zero_zero_one=$(lookup ab libalias.so.001)
ba_one=$(lookup ba libalias.so.1)
ba_zero_one=$(lookup ba libalias.so.01)
ba_zero_zero_one=$(lookup ba libalias.so.001)

classification=unexpected
if [[ "$ab_one" == 101 \
   && "$ab_zero_one" == 101 \
   && "$ab_zero_zero_one" == 101 \
   && "$ba_one" == 202 \
   && "$ba_zero_one" == 202 \
   && "$ba_zero_zero_one" == 202 ]]; then
  classification=alias_identity_reproduced
elif [[ "$ab_one" == 101 \
     && "$ab_zero_one" == 202 \
     && "$ab_zero_zero_one" == MISSING \
     && "$ba_one" == 101 \
     && "$ba_zero_one" == 202 \
     && "$ba_zero_zero_one" == MISSING ]]; then
  classification=exact_identity_preserved
fi

printf 'classification\t%s\n' "$classification" >>"$summary"
cat "$summary"

if [[ "$classification" == unexpected ]]; then
  exit 1
fi
