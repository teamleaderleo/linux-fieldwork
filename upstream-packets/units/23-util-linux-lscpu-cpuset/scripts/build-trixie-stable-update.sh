#!/usr/bin/env bash
set -euo pipefail

outdir=
while (($#)); do
  case "$1" in
    --output-dir)
      outdir=$2
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$outdir" ]] || {
  echo "--output-dir is required" >&2
  exit 2
}
mkdir -p "$outdir"
outdir=$(realpath "$outdir")

umask 022
work=$(mktemp -d /tmp/unit23-stable-update.XXXXXX)
case "$work" in
  /tmp/unit23-stable-update.*) ;;
  *)
    echo "unsafe disposable work path: $work" >&2
    exit 2
    ;;
esac
cleanup() {
  rm -rf --one-file-system -- "$work"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

base_version=2.41-5
update_version=2.41-5+deb13u1
patch_name=lscpu-clear-cpuset-output-after-error.patch
packet_root=/work/upstream-packets/units/23-util-linux-lscpu-cpuset
retained_patch="$packet_root/patches/0001-clear-cpuset-output-after-error.patch"
reproducer="$packet_root/scripts/reproduce-trixie-lscpu-cpuset.sh"

[[ -r "$retained_patch" ]] || {
  echo "missing retained patch: $retained_patch" >&2
  exit 2
}
[[ -x "$reproducer" || -r "$reproducer" ]] || {
  echo "missing reproducer: $reproducer" >&2
  exit 2
}

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kernel=$(uname -srvmo)"
  echo "architecture=$(dpkg --print-architecture)"
  echo "base_version=$base_version"
  echo "update_version=$update_version"
  echo "retained_patch_sha256=$(sha256sum "$retained_patch" | cut -d' ' -f1)"
  dpkg-query -W -f='installed_baseline=${Package} ${Version} ${Architecture}\n' util-linux 2>/dev/null || true
} >"$outdir/environment.txt"

sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources
grep -q '^Types: deb deb-src$' /etc/apt/sources.list.d/debian.sources
apt-get update >"$outdir/apt-update.log" 2>&1
apt-get install -y --no-install-recommends \
  build-essential ca-certificates debhelper devscripts dpkg-dev fakeroot \
  patch python3 quilt >"$outdir/apt-install.log" 2>&1
apt-get build-dep -y util-linux >"$outdir/apt-build-dep.log" 2>&1

build="$work/build"
mkdir -p "$build"
cd "$build"
apt-get source "util-linux=$base_version" >"$outdir/apt-source.log" 2>&1
src=$(find "$build" -mindepth 1 -maxdepth 1 -type d -name 'util-linux-*' -print -quit)
[[ -n "$src" ]]
[[ "$(dpkg-parsechangelog -l"$src/debian/changelog" -S Version)" == "$base_version" ]]

original_dsc="$build/util-linux_${base_version}.dsc"
original_orig="$build/util-linux_2.41.orig.tar.xz"
original_debian="$build/util-linux_${base_version}.debian.tar.xz"
for file in "$original_dsc" "$original_orig" "$original_debian"; do
  [[ -f "$file" ]] || {
    echo "missing exact source artifact: $file" >&2
    exit 1
  }
done

{
  echo "source_directory=$src"
  sha256sum "$original_dsc" "$original_orig" "$original_debian"
  echo "baseline_path_sha256=$(sha256sum "$src/lib/path.c" | cut -d' ' -f1)"
  echo "baseline_error_path:"
  grep -n -A8 -B2 '^out:$' "$src/lib/path.c"
} >"$outdir/source-identity.txt"

install -d "$src/debian/patches"
install -m 0644 "$retained_patch" "$src/debian/patches/$patch_name"
series="$src/debian/patches/series"
touch "$series"
if ! grep -Fxq "$patch_name" "$series"; then
  printf '%s\n' "$patch_name" >>"$series"
fi

cd "$src"
export QUILT_PATCHES=debian/patches
quilt push -a >"$outdir/quilt-push.log" 2>&1
if grep -Eqi 'fuzz|offset' "$outdir/quilt-push.log"; then
  echo "quilt applied with fuzz or offset" >&2
  cat "$outdir/quilt-push.log" >&2
  exit 1
fi

grep -Fq 'cpuset_free(*set);' lib/path.c
grep -Fq '*set = NULL;' lib/path.c

export DEBFULLNAME='Linux Fieldwork'
export DEBEMAIL='linux-fieldwork@example.invalid'
dch --newversion "$update_version" \
  --distribution trixie \
  --force-distribution \
  --urgency medium \
  'Backport the canonical util-linux cpuset ownership fix so lscpu does not abort after malformed cpuset input.'
[[ "$(dpkg-parsechangelog -S Version)" == "$update_version" ]]
[[ "$(dpkg-parsechangelog -S Distribution)" == trixie ]]

{
  echo "candidate_path_sha256=$(sha256sum lib/path.c | cut -d' ' -f1)"
  echo "debian_patch_sha256=$(sha256sum "debian/patches/$patch_name" | cut -d' ' -f1)"
  echo "series:"
  cat debian/patches/series
  echo "changelog_entry:"
  sed -n '1,/^ -- /p' debian/changelog
  echo "candidate_error_path:"
  grep -n -A10 -B2 '^out:$' lib/path.c
} >"$outdir/composition.txt"

# Build the source package first so the exact Debian delta and .dsc exist.
dpkg-buildpackage -S -us -uc \
  >"$outdir/dpkg-buildpackage-source.stdout" \
  2>"$outdir/dpkg-buildpackage-source.stderr"

new_dsc="$build/util-linux_${update_version}.dsc"
[[ -f "$new_dsc" ]]
set +e
debdiff "$original_dsc" "$new_dsc" >"$outdir/source.debdiff"
debdiff_rc=$?
set -e
case "$debdiff_rc" in
  1) ;; # expected: the stable-update source packages differ
  0)
    echo "source debdiff unexpectedly reported no changes" >&2
    exit 1
    ;;
  *)
    echo "source debdiff failed with status $debdiff_rc" >&2
    exit "$debdiff_rc"
    ;;
esac
[[ -s "$outdir/source.debdiff" ]]

# Build binary packages without suppressing tests.
unset DEB_BUILD_OPTIONS
dpkg-buildpackage -b -uc -us -j2 \
  >"$outdir/dpkg-buildpackage-binary.stdout" \
  2>"$outdir/dpkg-buildpackage-binary.stderr"

# Run the project-native focused lscpu suite twice on the final composed tree.
make check-programs >"$outdir/native-check-programs.stdout" 2>"$outdir/native-check-programs.stderr"
for pass in 1 2; do
  make check TS_OPTS='--parallel=1 lscpu' \
    >"$outdir/native-lscpu-pass-${pass}.stdout" \
    2>"$outdir/native-lscpu-pass-${pass}.stderr"
done

arch=$(dpkg --print-architecture)
candidate_deb="$build/util-linux_${update_version}_${arch}.deb"
[[ -f "$candidate_deb" ]]
candidate_root="$work/candidate-root"
mkdir -p "$candidate_root"
dpkg-deb -x "$candidate_deb" "$candidate_root"
candidate="$candidate_root/usr/bin/lscpu"
[[ -x "$candidate" ]]

{
  sha256sum "$new_dsc" "$candidate_deb" "$candidate"
  echo "new_source_version=$(dpkg-parsechangelog -S Version)"
  echo "new_source_distribution=$(dpkg-parsechangelog -S Distribution)"
} >"$outdir/final-identities.txt"

for pass in 1 2; do
  bash "$reproducer" \
    --baseline /usr/bin/lscpu \
    --candidate "$candidate" \
    --output-dir "$outdir/matrix-pass-${pass}" \
    >"$outdir/matrix-pass-${pass}.stdout" \
    2>"$outdir/matrix-pass-${pass}.stderr"
done
cmp "$outdir/matrix-pass-1/results.txt" "$outdir/matrix-pass-2/results.txt"

# The disposable source and extracted package roots are removed by the EXIT trap.
echo 'result=PASS' | tee "$outdir/result.txt"
