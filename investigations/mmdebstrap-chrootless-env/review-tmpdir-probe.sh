#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-chrootless-env/tmpdir-review-results"
runtime="${RUNNER_TEMP:-/tmp}/mmdebstrap-chrootless-tmpdir-review"

case "$runtime" in
  /|/tmp|/var/tmp) echo "refusing unsafe runtime: $runtime" >&2; exit 2 ;;
  /tmp/*|/var/tmp/*|/home/runner/work/_temp/*) ;;
  *) echo "runtime must be below a disposable temporary root: $runtime" >&2; exit 2 ;;
esac

cleanup() {
  rm -rf -- "$runtime"
}
trap cleanup EXIT INT TERM

rm -rf -- "$runtime" "$result_dir"
fixture="$runtime/fixture"
package="$runtime/lf-chrootless-tmpdir-probe_1.0_all.deb"
target="$runtime/target"
caller_tmp="$runtime/caller-tmp"
mkdir -p "$fixture/DEBIAN" "$result_dir" "$caller_tmp"

cat >"$fixture/DEBIAN/control" <<'EOF'
Package: lf-chrootless-tmpdir-probe
Version: 1.0
Section: misc
Priority: optional
Architecture: all
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: review fixture for chrootless temporary directory handling
EOF

cat >"$fixture/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu
log="$DPKG_ROOT/var/lib/lf-chrootless-tmpdir-probe/result.log"
mkdir -p "$(dirname "$log")"
created="$(mktemp -d -t lf-chrootless-tmp.XXXXXX)"
{
  printf 'TMPDIR=%s\n' "${TMPDIR-<unset>}"
  printf 'created=%s\n' "$created"
  printf 'DPKG_ROOT=%s\n' "$DPKG_ROOT"
} >"$log"
rmdir "$created"
EOF
chmod 0755 "$fixture/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "$fixture" "$package" \
  >"$result_dir/build.stdout" 2>"$result_dir/build.stderr"

package_dir="$(dirname "$package")"
printf -v hook 'mkdir -p "$1%s"; cp "%s" "$1%s"' \
  "$package_dir" "$package" "$package"

chmod 0755 "$source_root/mmdebstrap"
set +e
env -i \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  HOME="$runtime/home" \
  TMPDIR="$caller_tmp" \
  LC_ALL=C.UTF-8 \
  "$source_root/mmdebstrap" \
    --mode=chrootless \
    --variant=custom \
    --format=directory \
    --skip=update \
    --skip=check/chrootless/environment \
    --include="$package" \
    --setup-hook="$hook" \
    '' "$target" \
    >"$result_dir/mmdebstrap.stdout" \
    2>"$result_dir/mmdebstrap.stderr"
status=$?
set -e
printf '%s\n' "$status" >"$result_dir/status.txt"
if [[ $status -ne 0 ]]; then
  cat "$result_dir/mmdebstrap.stderr" >&2
  exit "$status"
fi

log="$target/var/lib/lf-chrootless-tmpdir-probe/result.log"
cp "$log" "$result_dir/package-script.log"
tmp_value="$(sed -n 's/^TMPDIR=//p' "$log")"
created="$(sed -n 's/^created=//p' "$log")"
printf 'caller_tmp=%s\ntarget=%s\nscript_tmpdir=%s\ncreated=%s\n' \
  "$caller_tmp" "$target" "$tmp_value" "$created" \
  >"$result_dir/summary.txt"

# The mitigation strips the caller TMPDIR, so ordinary temporary-file helpers
# fall back to the host /tmp namespace instead of a target-contained directory.
[[ "$tmp_value" == '<unset>' ]]
[[ "$created" == /tmp/* ]]
if [[ "$created" != "$target"/* ]]; then
  printf 'outside_target_temp=yes\n' >>"$result_dir/summary.txt"
  cat "$result_dir/summary.txt"
  echo "chrootless package script created its default temporary directory outside the target" >&2
  exit 1
fi

printf 'outside_target_temp=no\n' >>"$result_dir/summary.txt"
cat "$result_dir/summary.txt"
