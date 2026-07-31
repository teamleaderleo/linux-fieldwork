#!/usr/bin/env bash
# Run the imported mmdebstrap Debian autopkgtest and retain a compact evidence set.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
imported_source="$repo_root/upstream/mmdebstrap"
override_patch="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/installed-command-wrapper.patch"
sourcesfilter_patch="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/sourcesfilter-deb822.patch"
capability_patch="$repo_root/investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure/0001-run-hook-free-capability-case-as-hard-failure.patch"
signal_patch="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/sigint-process-group-kill-sid.patch"
phase_order_tool="$repo_root/tools/reorder_mmdebstrap_hook_free_phase.py"
run_id=${RUN_ID:-"local-$(date -u +%Y%m%dT%H%M%SZ)"}
run_dir=${RUN_DIR:-"$repo_root/investigations/mmdebstrap-autopkgtest-1141078/runs/$run_id"}
timeout_duration=${AUTOPKGTEST_TIMEOUT:-165m}
mkdir -p "$run_dir"

status_file="$run_dir/exit-status"
console_log="$run_dir/autopkgtest-console.log"
output_dir="$run_dir/autopkgtest-output"

finish_early() {
  local status=$1
  shift
  local reason=$*
  printf '%s\n' "$reason" >&2
  printf '%s\n' "$status" >"$status_file"
  printf '%s\n' "$reason" >"$run_dir/preflight-error.txt"
  {
    printf '# Reproduction result\n\n'
    printf -- '- Finished: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf -- '- Exit status: `%s`\n' "$status"
    if [[ $status -eq 77 ]]; then
      printf -- '- Classification: `neutral-or-skipped`\n'
    else
      printf -- '- Classification: `carrier-preflight-failure`\n'
    fi
    printf -- '- Preflight reason: `%s`\n' "$reason"
  } >"$run_dir/result.md"
  exit "$status"
}

apply_exact_patch() {
  local label=$1
  local patch_path=$2
  local stdout_path="$run_dir/$label-patch.stdout"
  local stderr_path="$run_dir/$label-patch.stderr"

  if ! patch --batch --forward --fuzz=0 -p1 -d "$source_tree" -i "$patch_path" \
      >"$stdout_path" 2>"$stderr_path"; then
    return 1
  fi
  if grep -Eiq '(^|[^[:alpha:]])(fuzz|offset)([^[:alpha:]]|$)' \
      "$stdout_path" "$stderr_path"; then
    printf 'patch %s applied with fuzzy or offset placement\n' "$label" \
      >>"$stderr_path"
    return 2
  fi
}

if [[ $(id -u) -ne 0 ]]; then
  finish_early 77 "reproduction requires root inside a disposable test environment"
fi
for command in autopkgtest patch python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    finish_early 77 "$command is unavailable"
  fi
done
if [[ ! -f $imported_source/debian/tests/control ]]; then
  finish_early 2 "imported mmdebstrap source tree is missing"
fi
if [[ ! -f $override_patch ]]; then
  finish_early 2 "installed-command wrapper patch is missing"
fi
if [[ ! -f $sourcesfilter_patch ]]; then
  finish_early 2 "Deb822 sourcesfilter patch is missing"
fi
if [[ ! -f $capability_patch ]]; then
  finish_early 2 "hook-free hard-failure scheduling patch is missing"
fi
if [[ ! -f $signal_patch ]]; then
  finish_early 2 "sid process-group signal compatibility patch is missing"
fi
if [[ ! -f $phase_order_tool ]]; then
  finish_early 2 "integration-only hook-free phase ordering tool is missing"
fi

work_root=$(mktemp -d "${TMPDIR:-/tmp}/lf-mmdebstrap-autopkgtest.XXXXXXXX")
case "$work_root" in
  /|/tmp|/var/tmp)
    finish_early 2 "refusing unsafe temporary source root: $work_root"
    ;;
esac
trap 'rm -rf -- "$work_root"' EXIT INT TERM
source_tree="$work_root/mmdebstrap"
cp -a "$imported_source" "$source_tree"

# Apply independent and later-file patches before the wrapper changes testsuite
# line positions. Every patch must land with zero fuzz and zero offset.
if ! apply_exact_patch sourcesfilter "$sourcesfilter_patch"; then
  finish_early 2 "Deb822 sourcesfilter patch failed exact application"
fi
if ! apply_exact_patch capability "$capability_patch"; then
  finish_early 2 "hook-free hard-failure patch failed exact application"
fi
if ! apply_exact_patch override "$override_patch"; then
  finish_early 2 "installed-command wrapper patch failed exact application"
fi
if ! apply_exact_patch signal "$signal_patch"; then
  finish_early 2 "sid process-group signal patch failed exact application"
fi
python3 "$phase_order_tool" "$source_tree/debian/tests/testsuite" \
  >"$run_dir/phase-order.stdout" 2>"$run_dir/phase-order.stderr"

bash "$repo_root/scripts/capture-linux-context.sh" "$run_dir/context.md"

{
  printf '# Reproduction provenance\n\n'
  printf -- '- Started: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Run ID: `%s`\n' "$run_id"
  printf -- '- Timeout: `%s`\n' "$timeout_duration"
  printf -- '- Imported source path: `%s`\n' "upstream/mmdebstrap"
  printf -- '- Execution source: temporary copy with installed-command, Deb822 sourcesfilter, hook-free hard-failure scheduling, sid process-group signal compatibility, and integration-only phase-order transformations\n'
  printf -- '- Patch application contract: `zero fuzz and zero offset`\n'
  printf -- '- Wrapper purpose: execute `/usr/bin/mmdebstrap` while bypassing source-preflight checks that current tooling applies to the older packaged script\n'
  printf -- '- Sourcesfilter purpose: process current Deb822 apt source entries through python-apt exploded entries instead of asserting\n'
  printf -- '- Scheduling purpose: retain the landing candidate that runs the mount-capability case in a dedicated hook-free phase with hard ordinary failures\n'
  printf -- '- Signal compatibility purpose: replace the rejected procps long form with the exact dash builtin spelling proven by current sid process-group topology evidence\n'
  printf -- '- Integration-order purpose: run that exact hook-free block before the broad matrix, then continue the broad matrix unchanged so an unrelated earlier failure cannot hide Packet B execution\n'
  if [[ -f $imported_source/.linux-fieldwork-source.json ]]; then
    printf '\n## Imported source\n\n```json\n'
    cat "$imported_source/.linux-fieldwork-source.json"
    printf '\n```\n'
  fi
  printf '\n## Test and override hashes\n\n```text\n'
  sha256sum \
    "$imported_source/debian/tests/control" \
    "$imported_source/debian/tests/testsuite" \
    "$imported_source/debian/tests/sourcesfilter" \
    "$imported_source/tests/sigint-during-customize-hook" \
    "$imported_source/coverage.py" \
    "$imported_source/coverage.txt" \
    "$imported_source/make_mirror.sh" \
    "$override_patch" \
    "$sourcesfilter_patch" \
    "$capability_patch" \
    "$signal_patch" \
    "$phase_order_tool" \
    "$source_tree/debian/tests/testsuite" \
    "$source_tree/debian/tests/sourcesfilter" \
    "$source_tree/tests/sigint-during-customize-hook" \
    "$source_tree/coverage.py" \
    "$source_tree/coverage.txt"
  printf '```\n'
  printf '\n## Integration phase ordering\n\n```text\n'
  cat "$run_dir/phase-order.stdout"
  printf '```\n'
  printf '\n## Tool versions\n\n```text\n'
  dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
    autopkgtest mmdebstrap perltidy apt dpkg patch procps dash 2>&1 || true
  printf 'autopkgtest executable\t%s\n' "$(command -v autopkgtest)"
  printf '```\n'
  printf '\n## APT policy\n\n```text\n'
  apt-cache policy base-files mmdebstrap perltidy apt dpkg procps dash 2>&1 || true
  printf '```\n'
} >"$run_dir/provenance.md"

dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  >"$run_dir/package-versions-before.tsv" 2>"$run_dir/package-query-before.err" || true

printf '%q ' timeout --signal=INT --kill-after=5m "$timeout_duration" \
  autopkgtest --output-dir "$output_dir" '<temporary-source-copy>' -- null \
  >"$run_dir/command.txt"
printf '\n' >>"$run_dir/command.txt"

set +e
timeout --signal=INT --kill-after=5m "$timeout_duration" \
  autopkgtest --output-dir "$output_dir" "$source_tree" -- null \
  >"$console_log" 2>&1
status=$?
set -e
printf '%s\n' "$status" >"$status_file"

dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  >"$run_dir/package-versions-after.tsv" 2>"$run_dir/package-query-after.err" || true

{
  printf '# Reproduction result\n\n'
  printf -- '- Finished: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Exit status: `%s`\n' "$status"
  case $status in
    0) printf -- '- Classification: `pass`\n' ;;
    77) printf -- '- Classification: `neutral-or-skipped`\n' ;;
    124|137) printf -- '- Classification: `timeout`\n' ;;
    *) printf -- '- Classification: `failure`\n' ;;
  esac
  printf -- '- Patch application contract: `zero fuzz and zero offset`\n'
  printf -- '- Source-preflight override: `installed-command-wrapper.patch`\n'
  printf -- '- Source compatibility override: `sourcesfilter-deb822.patch`\n'
  printf -- '- Test scheduling override: `0001-run-hook-free-capability-case-as-hard-failure.patch`\n'
  printf -- '- Integration signal override: `sigint-process-group-kill-sid.patch`\n'
  printf -- '- Integration-only order: `hook-free hard phase, broad matrix, soft transition phase`\n'
  if [[ -f $console_log ]]; then
    printf -- '- Console SHA-256: `%s`\n' "$(sha256sum "$console_log" | cut -d' ' -f1)"
  fi
} >"$run_dir/result.md"

exit "$status"
