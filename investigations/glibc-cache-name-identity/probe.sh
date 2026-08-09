#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "SKIP: run as root; the probe uses only a disposable chroot" >&2
  exit 77
fi
if [[ $(uname -m) != x86_64 ]]; then
  echo "SKIP: current fixture is x86_64-only" >&2
  exit 77
fi
for tool in gcc ldconfig ldd chroot readlink awk grep sed; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 77; }
done

work=$(mktemp -d /tmp/glibc-cache-name-identity.XXXXXX)
cleanup() {
  case "$work" in
    /tmp/glibc-cache-name-identity.*) rm -rf -- "$work" ;;
    *) echo "refusing unexpected cleanup path: $work" >&2; return 1 ;;
  esac
}
trap cleanup EXIT

src="$work/src"
mkdir -p "$src"
cat >"$src/marker.c" <<'EOF'
#ifndef MARKER
#define MARKER 0
#endif
int alias_marker(void) { return MARKER; }
EOF
cat >"$src/probe.c" <<'EOF'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <stdio.h>

int main(int argc, char **argv)
{
  if (argc != 2)
    return 64;
  void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (handle == NULL)
    {
      fprintf(stderr, "dlopen: %s\n", dlerror());
      return 65;
    }
  int (*marker)(void) = (int (*)(void)) dlsym(handle, "alias_marker");
  if (marker == NULL)
    {
      fprintf(stderr, "dlsym: %s\n", dlerror());
      return 66;
    }
  struct link_map *map = NULL;
  if (dlinfo(handle, RTLD_DI_LINKMAP, &map) != 0 || map == NULL)
    return 67;
  printf("request=%s marker=%d object=%s\n", argv[1], marker(), map->l_name);
  return 0;
}
EOF

gcc -O2 -Wall -Wextra -Werror "$src/probe.c" -ldl -o "$work/probe"

loader=$(readlink -f /lib64/ld-linux-x86-64.so.2)
libc=$(ldd /bin/true | awk '/libc\.so\.6/ { print $3; exit }')
[[ -f "$loader" && -f "$libc" ]]

marker_of() { sed -n 's/.* marker=\([0-9][0-9]*\) .*/\1/p' <<<"$1"; }
object_of() { sed -n 's/.* object=\(.*\)$/\1/p' <<<"$1"; }

run_pair() {
  local label=$1 name_a=$2 marker_a=$3 file_a=$4 name_b=$5 marker_b=$6 file_b=$7
  local root="$work/$label"
  mkdir -p "$root/usr/lib" "$root/lib/x86_64-linux-gnu" "$root/lib64" "$root/etc"
  cp "$loader" "$root/lib64/ld-linux-x86-64.so.2"
  cp "$libc" "$root/lib/x86_64-linux-gnu/libc.so.6"
  cp "$work/probe" "$root/probe"

  gcc -shared -fPIC -O2 -Wall -Wextra -Werror -DMARKER="$marker_a" \
    -Wl,-soname,"$name_a" "$src/marker.c" -o "$root/usr/lib/$file_a"
  gcc -shared -fPIC -O2 -Wall -Wextra -Werror -DMARKER="$marker_b" \
    -Wl,-soname,"$name_b" "$src/marker.c" -o "$root/usr/lib/$file_b"
  printf '/usr/lib\n' >"$root/etc/ld.so.conf"
  ldconfig -r "$root"

  echo "=== $label cache entries ==="
  ldconfig -r "$root" -p | grep -F "$name_a" || true
  ldconfig -r "$root" -p | grep -F "$name_b" || true

  local cached_a cached_b exact_a exact_b
  cached_a=$(chroot "$root" /probe "$name_a")
  cached_b=$(chroot "$root" /probe "$name_b")
  exact_a=$(chroot "$root" /lib64/ld-linux-x86-64.so.2 \
    --inhibit-cache --library-path /usr/lib:/lib/x86_64-linux-gnu /probe "$name_a")
  exact_b=$(chroot "$root" /lib64/ld-linux-x86-64.so.2 \
    --inhibit-cache --library-path /usr/lib:/lib/x86_64-linux-gnu /probe "$name_b")

  printf '%s\n' "cached A: $cached_a" "cached B: $cached_b" \
    "bypass A: $exact_a" "bypass B: $exact_b"

  # The control path must preserve the two exact identities.
  [[ $(marker_of "$exact_a") == "$marker_a" ]]
  [[ $(marker_of "$exact_b") == "$marker_b" ]]
  [[ $(object_of "$exact_a") != $(object_of "$exact_b") ]]

  # The current-cache defect is that byte-distinct requested names collapse
  # into one comparator-equivalent cache identity. Which member wins is a
  # cache-generation detail, so do not bake one winner into the regression.
  [[ $(marker_of "$cached_a") == $(marker_of "$cached_b") ]]
  [[ $(object_of "$cached_a") == $(object_of "$cached_b") ]]
  [[ $(marker_of "$cached_a") == "$marker_a" || $(marker_of "$cached_a") == "$marker_b" ]]

  echo "PASS $label: cache collapses byte-distinct names; cache bypass preserves exact identity"
}

echo "=== environment ==="
ldd --version 2>&1 | sed -n '1p'
uname -a

# Numeric values compare equal in the historical cache comparator even though
# the byte strings and SONAME identities differ.
run_pair leading-zero-direct \
  libalias.so.1 101 libalias.so.1 \
  libalias.so.01 202 libalias.so.01

# Use ordinary versioned files as a packaging-layout control. ldconfig creates
# the SONAME symlinks; the semantic defect remains independent of which alias
# happens to win inside the generated cache.
run_pair leading-zero-versioned \
  libaliasv.so.1 111 libaliasv.so.1.100 \
  libaliasv.so.01 222 libaliasv.so.01.200

# The comparator accumulates arbitrary decimal runs in signed int values.
# 4294967297 and 1 can collapse after overflow on the tested x86_64 glibc.
run_pair wide-decimal \
  libwide.so.1 301 libwide.so.1 \
  libwide.so.4294967297 302 libwide.so.4294967297

echo "PASS: glibc ld.so.cache name-identity aliasing reproduced"
