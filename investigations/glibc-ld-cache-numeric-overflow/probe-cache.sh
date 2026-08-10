#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
if [[ -z "$output_dir" ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 64
fi

for command in cc ldd ldconfig chroot sudo grep; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  fi
done

if [[ $(uname -m) != x86_64 ]]; then
  printf 'this first cache-level fixture is intentionally x86_64-only\n' >&2
  exit 77
fi

loader=/lib64/ld-linux-x86-64.so.2
if [[ ! -x "$loader" ]]; then
  printf 'expected glibc loader is unavailable\n' >&2
  exit 69
fi

work_parent=${RUNNER_TEMP:-/tmp}
work_root=$(mktemp -d "$work_parent/glibc-cache-numeric-overflow-cache.XXXXXX")
cleanup() {
  chmod -R u+rwX "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
summary="$output_dir/cache-summary.tsv"
environment="$output_dir/cache-environment.txt"

{
  printf 'uname=%s\n' "$(uname -a)"
  printf 'ldconfig=%s\n' "$(ldconfig --version 2>&1 | head -n 1)"
  printf 'cc=%s\n' "$(cc --version | head -n 1)"
} >"$environment"

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

base="$work_root/base"
mkdir -p \
  "$base/etc" \
  "$base/opt/a" \
  "$base/opt/b" \
  "$base/opt/c" \
  "$base/opt/d" \
  "$base/runtime-libs" \
  "$base/lib64" \
  "$base/var/cache/ldconfig"

cc -shared -fPIC -Wl,-soname,libwide.so.0 \
  "$work_root/zero.c" -o "$base/opt/a/libwide-zero.so.0.0"
cc -shared -fPIC -Wl,-soname,libwide.so.1 \
  "$work_root/one.c" -o "$base/opt/b/libwide-one.so.1.0"
cc -shared -fPIC -Wl,-soname,libwide.so.2147483648 \
  "$work_root/int-over.c" -o "$base/opt/c/libwide-int-over.so.2147483648.0"
cc -shared -fPIC -Wl,-soname,libwide.so.4294967296 \
  "$work_root/u32-wrap.c" -o "$base/opt/d/libwide-u32-wrap.so.4294967296.0"
cc -shared -fPIC -Wl,-soname,libcontrol.so.1 \
  "$work_root/control.c" -o "$base/opt/a/libcontrol.so.1.0"
cc -Wall -Wextra -Werror "$work_root/probe.c" -ldl -o "$base/probe"

cp -L "$loader" "$base/lib64/ld-linux-x86-64.so.2"
while IFS= read -r library; do
  [[ -n "$library" ]] || continue
  cp -L "$library" "$base/runtime-libs/$(basename "$library")"
done < <(ldd "$base/probe" | awk '$2 == "=>" && $3 ~ /^\// { print $3 }')

if [[ ! -e "$base/runtime-libs/libc.so.6" ]]; then
  printf 'probe dependency collection did not retain libc.so.6\n' >&2
  exit 69
fi

make_root() {
  local label=$1
  shift
  local root="$work_root/root-$label"

  cp -a "$base" "$root"
  printf '%s\n' "$@" >"$root/etc/ld.so.conf"
  sudo ldconfig -r "$root" -i
  sudo ldconfig -r "$root" -p >"$output_dir/cache-$label.txt"
  printf '%s\n' "$root"
}

root_abcd=$(make_root abcd /opt/a /opt/b /opt/c /opt/d)
root_dcba=$(make_root dcba /opt/d /opt/c /opt/b /opt/a)

query() {
  local root=$1
  local name=$2
  local stderr_file=$3
  local result status

  set +e
  result=$(sudo env -i /usr/sbin/chroot "$root" \
    /lib64/ld-linux-x86-64.so.2 \
    --library-path /runtime-libs \
    /probe "$name" 2>"$stderr_file")
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
      printf 'probe returned unexpected status %d for %s\n' "$status" "$name" >&2
      cat "$stderr_file" >&2 || true
      exit "$status"
      ;;
  esac
}

printf 'root\trequest\tresult\n' >"$summary"
for label in abcd dcba; do
  if [[ "$label" == abcd ]]; then
    root=$root_abcd
  else
    root=$root_dcba
  fi

  for name in \
    libwide.so.0 \
    libwide.so.1 \
    libwide.so.2147483648 \
    libwide.so.4294967296 \
    libwide.so.8589934592 \
    libwide.so.2 \
    libcontrol.so.1; do
    stderr_file="$work_root/$label-${name//\//_}.stderr"
    result=$(query "$root" "$name" "$stderr_file")
    printf '%s\t%s\t%s\n' "$label" "$name" "$result" >>"$summary"
  done
done

lookup() {
  local label=$1
  local name=$2
  awk -F '\t' -v label="$label" -v name="$name" \
    '$1 == label && $2 == name { print $3; exit }' "$summary"
}

# The unrelated short control must remain usable in both roots.  If this fails,
# the private-root harness did not reach the intended cache comparison boundary.
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

for label in abcd dcba; do
  for name in \
    libwide.so.0 \
    libwide.so.1 \
    libwide.so.2147483648 \
    libwide.so.4294967296; do
    if ! grep -Fq "$name " "$output_dir/cache-$label.txt"; then
      classification=overflow_cache_identity_or_lookup_effect_reproduced
    fi
  done
done

printf 'classification\t%s\n' "$classification" >>"$summary"
cat "$summary"
