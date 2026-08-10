#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
if [[ -z "$output_dir" ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 64
fi

for command in cc ldd ldconfig chroot sudo; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  fi
done

if [[ $(uname -m) != x86_64 ]]; then
  printf 'this first executable fixture is intentionally x86_64-only\n' >&2
  exit 77
fi

loader=/lib64/ld-linux-x86-64.so.2
if [[ ! -x "$loader" ]]; then
  printf 'expected glibc loader is unavailable\n' >&2
  exit 69
fi

work_parent=${RUNNER_TEMP:-/tmp}
work_root=$(mktemp -d "$work_parent/glibc-cache-numeric-alias.XXXXXX")
cleanup() {
  chmod -R u+rwX "$work_root" 2>/dev/null || true
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
summary="$output_dir/summary.tsv"
environment="$output_dir/environment.txt"
cache_listing_ab="$output_dir/cache-ab.txt"
cache_listing_ba="$output_dir/cache-ba.txt"

{
  printf 'uname=%s\n' "$(uname -a)"
  printf 'ldconfig=%s\n' "$(ldconfig --version 2>&1 | head -n 1)"
  printf 'cc=%s\n' "$(cc --version | head -n 1)"
  printf 'runner_temp_parent=%s\n' "${RUNNER_TEMP:+RUNNER_TEMP}"
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

base="$work_root/base"
mkdir -p \
  "$base/etc" \
  "$base/opt/a" \
  "$base/opt/b" \
  "$base/runtime-libs" \
  "$base/lib64" \
  "$base/var/cache/ldconfig"

cc -shared -fPIC -Wl,-soname,libalias.so.1 \
  "$work_root/alias-a.c" -o "$base/opt/a/libalias-a.so.1.0"
cc -shared -fPIC -Wl,-soname,libalias.so.01 \
  "$work_root/alias-b.c" -o "$base/opt/b/libalias-b.so.1.0"
cc -shared -fPIC -Wl,-soname,libcontrol.so.1 \
  "$work_root/control-a.c" -o "$base/opt/a/libcontrol-a.so.1.0"
cc -shared -fPIC -Wl,-soname,libcontrol.so.2 \
  "$work_root/control-b.c" -o "$base/opt/b/libcontrol-b.so.2.0"
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
  local first=$2
  local second=$3
  local root="$work_root/root-$label"

  cp -a "$base" "$root"
  printf '%s\n%s\n' "$first" "$second" >"$root/etc/ld.so.conf"
  sudo ldconfig -r "$root" -i
  printf '%s\n' "$root"
}

root_ab=$(make_root ab /opt/a /opt/b)
root_ba=$(make_root ba /opt/b /opt/a)

sudo ldconfig -r "$root_ab" -p >"$cache_listing_ab"
sudo ldconfig -r "$root_ba" -p >"$cache_listing_ba"

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
for label in ab ba; do
  if [[ "$label" == ab ]]; then
    root=$root_ab
  else
    root=$root_ba
  fi
  for name in \
    libalias.so.1 \
    libalias.so.01 \
    libalias.so.001 \
    libalias.so.2 \
    libcontrol.so.1 \
    libcontrol.so.2; do
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

# Harness controls: comparator-distinct exact names must select their own marker
# regardless of configured directory order, and an absent comparator-distinct
# alias must remain missing.
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
