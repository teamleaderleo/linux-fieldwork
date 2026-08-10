#!/usr/bin/env bash
set -euo pipefail

umask 077

output_dir=${1:-}
if [[ -z "$output_dir" ]]; then
  printf 'usage: %s OUTPUT_DIR\n' "$0" >&2
  exit 64
fi

for command in apt-cache apt-mark dpkg-query sha256sum uname; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 69
  fi
done

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)

{
  printf 'uname=%s\n' "$(uname -a)"
  printf 'architecture=%s\n' "$(dpkg --print-architecture)"
  printf 'image_os=%s\n' "${ImageOS:-unknown}"
  printf 'image_version=%s\n' "${ImageVersion:-unknown}"
  printf 'runner_arch=%s\n' "${RUNNER_ARCH:-unknown}"
  printf 'runner_os=%s\n' "${RUNNER_OS:-unknown}"
} >"$output_dir/environment.txt"

packages=(
  libc6
  libc6-dev
  libc6-i386
  fakeroot
  libfakeroot
  lib32gcc-s1
  lib32stdc++6
  libclang-rt-16-dev
  libclang-rt-18-dev
)

printf 'package\tversion\tstatus\n' >"$output_dir/packages.tsv"
for package in "${packages[@]}"; do
  if dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' "$package" \
      >>"$output_dir/packages.tsv" 2>/dev/null; then
    :
  else
    printf '%s\t-\tmissing\n' "$package" >>"$output_dir/packages.tsv"
  fi
done

apt-mark showmanual | LC_ALL=C sort >"$output_dir/apt-manual.txt"
apt-mark showauto | LC_ALL=C sort >"$output_dir/apt-auto.txt"

printf 'package\tmark\n' >"$output_dir/package-marks.tsv"
for package in "${packages[@]}"; do
  if grep -Fqx "$package" "$output_dir/apt-manual.txt"; then
    mark=manual
  elif grep -Fqx "$package" "$output_dir/apt-auto.txt"; then
    mark=auto
  elif dpkg-query -W "$package" >/dev/null 2>&1; then
    mark=installed-unclassified
  else
    mark=missing
  fi
  printf '%s\t%s\n' "$package" "$mark" >>"$output_dir/package-marks.tsv"
done

apt-cache rdepends --installed libc6-i386 \
  >"$output_dir/libc6-i386-rdepends-installed.txt" 2>&1 || true
apt-cache showpkg libc6-i386 \
  >"$output_dir/libc6-i386-showpkg.txt" 2>&1 || true

for package in libclang-rt-16-dev libclang-rt-18-dev lib32gcc-s1 lib32stdc++6; do
  apt-cache depends --recurse \
    --no-recommends --no-suggests --no-conflicts --no-breaks --no-replaces --no-enhances \
    "$package" >"$output_dir/${package}-depends.txt" 2>&1 || true
done

printf 'fragment\towner\tsha256\n' >"$output_dir/loader-fragments.tsv"
: >"$output_dir/loader-fragments-content.txt"
shopt -s nullglob
for path in /etc/ld.so.conf.d/*; do
  [[ -f "$path" ]] || continue
  owner=$(dpkg-query -S "$path" 2>/dev/null | head -n 1 || true)
  [[ -n "$owner" ]] || owner=unowned
  digest=$(sha256sum "$path" | awk '{print $1}')
  printf '%s\t%s\t%s\n' "${path#/etc/ld.so.conf.d/}" "$owner" "$digest" \
    >>"$output_dir/loader-fragments.tsv"
  {
    printf '===== %s =====\n' "${path#/etc/ld.so.conf.d/}"
    cat "$path"
    printf '\n'
  } >>"$output_dir/loader-fragments-content.txt"
done

{
  printf 'libc6_i386_installed\t'
  if dpkg-query -W libc6-i386 >/dev/null 2>&1; then printf 'true\n'; else printf 'false\n'; fi
  printf 'libc6_i386_mark\t%s\n' "$(awk -F '\t' '$1 == "libc6-i386" { print $2 }' "$output_dir/package-marks.tsv")"
  printf 'zz_i386_fragment_present\t'
  if [[ -f /etc/ld.so.conf.d/zz_i386-biarch-compat.conf ]]; then printf 'true\n'; else printf 'false\n'; fi
  printf 'complete\ttrue\n'
} >"$output_dir/summary.tsv"

cat "$output_dir/summary.tsv"
