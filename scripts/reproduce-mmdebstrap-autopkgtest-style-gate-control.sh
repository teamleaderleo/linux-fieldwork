#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_tree="$repo_root/upstream/mmdebstrap"
patch_file="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/installed-command-wrapper.patch"
output_input=${1:-"$repo_root/investigations/mmdebstrap-autopkgtest-1141078/runs/style-gate-control"}
output=$(realpath -m -- "$output_input")
runs_root=$(realpath -m -- "$repo_root/investigations/mmdebstrap-autopkgtest-1141078/runs")

case "$output" in
  "$runs_root"/*|/tmp/*|/var/tmp/*)
    ;;
  *)
    printf 'output must be a child of %s, /tmp, or /var/tmp: %s\n' "$runs_root" "$output" >&2
    exit 2
    ;;
esac
case "$output" in
  /|/tmp|/var/tmp|"$runs_root")
    printf 'refusing unsafe output directory: %s\n' "$output" >&2
    exit 2
    ;;
esac

if [[ $(id -u) -ne 0 ]]; then
  printf 'this reproduction requires root in a disposable environment\n' >&2
  exit 77
fi
for command in autopkgtest patch dpkg-query sha256sum timeout; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'required command is unavailable: %s\n' "$command" >&2
    exit 77
  }
done
for path in "$source_tree/debian/tests/testsuite" "$source_tree/coverage.sh" "$patch_file"; do
  [[ -f "$path" ]] || {
    printf 'required input is missing: %s\n' "$path" >&2
    exit 2
  }
done

rm -rf -- "$output"
mkdir -p "$output"
work_root=$(mktemp -d /tmp/lf-mmdebstrap-style-gate.XXXXXXXX)
case "$work_root" in
  /|/tmp|/var/tmp)
    printf 'refusing unsafe temporary source root: %s\n' "$work_root" >&2
    exit 2
    ;;
esac
cleanup() {
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM
candidate="$work_root/mmdebstrap"
cp -a "$source_tree" "$candidate"
patch -p1 -d "$candidate" -i "$patch_file" \
  >"$output/patch.stdout" 2>"$output/patch.stderr"

{
  printf 'run_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'kernel=%s\n' "$(uname -srmo)"
  sed -n 's/^PRETTY_NAME=/os=/p' /etc/os-release
  printf 'uid=%s\n' "$(id -u)"
  printf 'source_path=upstream/mmdebstrap\n'
  printf 'execution_source=temporary patched copy\n'
  printf 'behavior_command=/usr/bin/mmdebstrap\n'
  printf 'style_checked_command=temporary fake source-tree mmdebstrap\n'
  dpkg-query -W -f='package=${binary:Package}\tversion=${Version}\tarchitecture=${Architecture}\n' \
    autopkgtest mmdebstrap perltidy apt dpkg patch 2>&1 || true
} >"$output/environment.txt"

sha256sum \
  "$source_tree/debian/tests/testsuite" \
  "$source_tree/coverage.sh" \
  "$patch_file" \
  "$candidate/debian/tests/testsuite" \
  >"$output/input-sha256.txt"

printf '%q ' autopkgtest --output-dir "$output/autopkgtest-output" '<temporary-patched-source>' -- null \
  >"$output/command.txt"
printf '\n' >>"$output/command.txt"

set +e
autopkgtest --output-dir "$output/autopkgtest-output" "$candidate" -- null \
  >"$output/console.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" >"$output/exit-status"

{
  printf 'exit_status=%s\n' "$status"
  case "$status" in
    0) printf 'classification=pass\n' ;;
    77) printf 'classification=neutral-or-skipped\n' ;;
    *) printf 'classification=failure\n' ;;
  esac
  if grep -Fq 'perltidy failed' "$output/console.log"; then
    printf 'perltidy_gate_failed=yes\n'
  else
    printf 'perltidy_gate_failed=no\n'
  fi
  if grep -Fq '/usr/bin/mmdebstrap' "$candidate/debian/tests/testsuite"; then
    printf 'installed_command_wrapper_present=yes\n'
  else
    printf 'installed_command_wrapper_present=no\n'
  fi
} >"$output/summary.txt"

exit "$status"
