#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
patch_file="$repo_root/investigations/mmdebstrap-chrootless-env/mmdebstrap-chrootless-target-tmpdir.patch"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/target-tmpdir-results"
temp_root="$(realpath -m -- "${RUNNER_TEMP:-/tmp}")"
case "$temp_root" in
  /tmp|/tmp/*|/var/tmp|/var/tmp/*|/home/runner/work/_temp|/home/runner/work/_temp/*)
    ;;
  /)
    echo "refusing unsafe temporary root: $temp_root" >&2
    exit 2
    ;;
  *)
    echo "temporary root must be disposable: $temp_root" >&2
    exit 2
    ;;
esac
runtime="$(realpath -m -- "$temp_root/mmdebstrap-chrootless-target-tmpdir")"
case "$runtime" in
  "$temp_root"/*)
    ;;
  *)
    echo "runtime must be a strict child of $temp_root: $runtime" >&2
    exit 2
    ;;
esac

cleanup() {
  rm -rf -- "$runtime"
}
trap cleanup EXIT INT TERM

for command in dpkg-deb dpkg-query patch perl python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "missing required command: $command" >&2
    exit 2
  }
done

rm -rf -- "$runtime" "$result_dir"
mkdir -p "$runtime" "$result_dir"

candidate_repo="$runtime/candidate-repo"
mkdir -p "$candidate_repo/upstream"
cp -a "$repo_root/upstream/mmdebstrap" "$candidate_repo/upstream/mmdebstrap"
patch -p1 -d "$candidate_repo" -i "$patch_file" \
  >"$result_dir/patch.stdout" 2>"$result_dir/patch.stderr"
perl -c "$candidate_repo/upstream/mmdebstrap/mmdebstrap" \
  >"$result_dir/perl.stdout" 2>"$result_dir/perl.stderr"
chmod 0755 "$repo_root/upstream/mmdebstrap/mmdebstrap"
chmod 0755 "$candidate_repo/upstream/mmdebstrap/mmdebstrap"

fixture="$runtime/fixture"
package="$runtime/lf-chrootless-target-tmpdir_1.0_all.deb"
mkdir -p "$fixture/DEBIAN" "$fixture/usr/lib/lf-chrootless-target-tmpdir"
cat >"$fixture/DEBIAN/control" <<'EOF'
Package: lf-chrootless-target-tmpdir
Version: 1.0
Section: misc
Priority: optional
Architecture: all
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: target-contained TMPDIR regression fixture
EOF
cat >"$fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu
log="$DPKG_ROOT/var/lib/lf-chrootless-target-tmpdir/result.log"
mkdir -p "$(dirname "$log")"
created="$(mktemp -d -t lf-chrootless-target-tmp.XXXXXX)"
{
  printf 'TMPDIR=%s\n' "${TMPDIR-<unset>}"
  printf 'created=%s\n' "$created"
  printf 'DPKG_ROOT=%s\n' "$DPKG_ROOT"
  stat -c 'target_tmp_mode=%a' "$DPKG_ROOT/tmp"
} >"$log"
rmdir "$created"
EOF
chmod 0755 "$fixture/DEBIAN/postinst"
printf 'payload\n' >"$fixture/usr/lib/lf-chrootless-target-tmpdir/payload"
dpkg-deb --build --root-owner-group "$fixture" "$package" \
  >"$result_dir/build.stdout" 2>"$result_dir/build.stderr"

run_case() {
  local label=$1 source_root=$2 use_fakeroot=$3
  local target="$runtime/$label-target"
  local caller_tmp="$runtime/$label-caller-tmp"
  local package_dir hook
  mkdir -p "$caller_tmp"
  package_dir="$(dirname "$package")"
  printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
    "$package_dir" "$package" "$package"
  local -a command=(
    "$source_root/mmdebstrap"
    --mode=chrootless
    --variant=custom
    --format=directory
    --skip=update
    --include="$package"
    --setup-hook="$hook"
    '' "$target"
  )
  if [[ $use_fakeroot == yes ]]; then
    command=(fakeroot -- "${command[@]}")
  fi
  env -i \
    PATH=/usr/sbin:/usr/bin:/sbin:/bin \
    HOME="$runtime/home" \
    TMPDIR="$caller_tmp" \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    SOURCE_DATE_EPOCH=1700000000 \
    "${command[@]}" \
    >"$result_dir/$label.stdout" \
    2>"$result_dir/$label.stderr"

  dpkg-query --admindir="$target/var/lib/dpkg" \
    -W -f='${db:Status-Status}\n' lf-chrootless-target-tmpdir \
    | grep -Fx installed >/dev/null
  local log="$target/var/lib/lf-chrootless-target-tmpdir/result.log"
  cp "$log" "$result_dir/$label-package-script.log"
  local observed created mode
  observed="$(sed -n 's/^TMPDIR=//p' "$log")"
  created="$(sed -n 's/^created=//p' "$log")"
  mode="$(sed -n 's/^target_tmp_mode=//p' "$log")"
  {
    printf 'label=%s\n' "$label"
    printf 'caller_tmp=%s\n' "$caller_tmp"
    printf 'target=%s\n' "$target"
    printf 'observed_tmpdir=%s\n' "$observed"
    printf 'created=%s\n' "$created"
    printf 'target_tmp_mode=%s\n' "$mode"
    printf 'created_survives=%s\n' "$([[ -e "$created" ]] && echo yes || echo no)"
  } >"$result_dir/$label-summary.txt"
}

# Negative control: the environment-scrub candidate without this one-line
# repair removes mmdebstrap's already target-contained TMPDIR assignment.
run_case baseline "$repo_root/upstream/mmdebstrap" no
baseline_target="$runtime/baseline-target"
baseline_log="$result_dir/baseline-package-script.log"
grep -Fx 'TMPDIR=<unset>' "$baseline_log"
baseline_created="$(sed -n 's/^created=//p' "$baseline_log")"
[[ "$baseline_created" == /tmp/* ]]
[[ "$baseline_created" != "$baseline_target"/* ]]
[[ ! -e "$baseline_created" ]]

# Candidate: run_setup() has already replaced the caller TMPDIR with
# <target>/tmp. Preserving that value keeps ordinary temporary helpers beneath
# the selected root while still refusing arbitrary caller paths.
run_case candidate "$candidate_repo/upstream/mmdebstrap" no
candidate_target="$runtime/candidate-target"
candidate_log="$result_dir/candidate-package-script.log"
grep -Fx "TMPDIR=$candidate_target/tmp" "$candidate_log"
candidate_created="$(sed -n 's/^created=//p' "$candidate_log")"
[[ "$candidate_created" == "$candidate_target/tmp/"* ]]
grep -Fx 'target_tmp_mode=1777' "$candidate_log"
[[ ! -e "$candidate_created" ]]

# Fresh rerun and fakeroot both use the same target-derived invariant.
run_case candidate-rerun "$candidate_repo/upstream/mmdebstrap" no
rerun_target="$runtime/candidate-rerun-target"
grep -Fx "TMPDIR=$rerun_target/tmp" \
  "$result_dir/candidate-rerun-package-script.log"

if command -v fakeroot >/dev/null 2>&1; then
  run_case candidate-fakeroot "$candidate_repo/upstream/mmdebstrap" yes
  fakeroot_target="$runtime/candidate-fakeroot-target"
  grep -Fx "TMPDIR=$fakeroot_target/tmp" \
    "$result_dir/candidate-fakeroot-package-script.log"
  fakeroot_result=passed
else
  fakeroot_result=skipped
fi

cat >"$result_dir/summary.txt" <<EOF
negative_control_host_tmp=yes
baseline_tmpdir_unset=yes
candidate_target_tmpdir=yes
candidate_target_tmp_mode_1777=yes
candidate_temp_cleanup=yes
candidate_clean_rerun=yes
candidate_fakeroot=$fakeroot_result
direct_run_essential_static_shared_helper=yes
EOF
cat "$result_dir/summary.txt"
echo "chrootless target TMPDIR regression passed"
