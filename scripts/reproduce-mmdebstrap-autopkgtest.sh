#!/usr/bin/env bash
# Run the imported mmdebstrap Debian autopkgtest and retain a compact evidence set.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
imported_source="$repo_root/upstream/mmdebstrap"
override_patch="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/installed-command-wrapper.patch"
run_id=${RUN_ID:-"local-$(date -u +%Y%m%dT%H%M%SZ)"}
run_dir=${RUN_DIR:-"$repo_root/investigations/mmdebstrap-autopkgtest-1141078/runs/$run_id"}
timeout_duration=${AUTOPKGTEST_TIMEOUT:-165m}
mkdir -p "$run_dir"

status_file="$run_dir/exit-status"
console_log="$run_dir/autopkgtest-console.log"
output_dir="$run_dir/autopkgtest-output"

if [[ $(id -u) -ne 0 ]]; then
  printf 'reproduction requires root inside a disposable test environment\n' >&2
  printf '77\n' >"$status_file"
  exit 77
fi
for command in autopkgtest patch; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf '%s is unavailable\n' "$command" >&2
    printf '77\n' >"$status_file"
    exit 77
  fi
done
if [[ ! -f $imported_source/debian/tests/control ]]; then
  printf 'imported mmdebstrap source tree is missing\n' >&2
  printf '2\n' >"$status_file"
  exit 2
fi
if [[ ! -f $override_patch ]]; then
  printf 'installed-command wrapper patch is missing\n' >&2
  printf '2\n' >"$status_file"
  exit 2
fi

work_root=$(mktemp -d "${TMPDIR:-/tmp}/lf-mmdebstrap-autopkgtest.XXXXXXXX")
case "$work_root" in
  /|/tmp|/var/tmp)
    printf 'refusing unsafe temporary source root: %s\n' "$work_root" >&2
    exit 2
    ;;
esac
trap 'rm -rf -- "$work_root"' EXIT INT TERM
source_tree="$work_root/mmdebstrap"
cp -a "$imported_source" "$source_tree"
patch -p1 -d "$source_tree" -i "$override_patch" \
  >"$run_dir/override-patch.stdout" 2>"$run_dir/override-patch.stderr"

"$repo_root/scripts/capture-linux-context.sh" "$run_dir/context.md"

{
  printf '# Reproduction provenance\n\n'
  printf -- '- Started: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Run ID: `%s`\n' "$run_id"
  printf -- '- Timeout: `%s`\n' "$timeout_duration"
  printf -- '- Imported source path: `%s`\n' "upstream/mmdebstrap"
  printf -- '- Execution source: temporary copy with the recorded installed-command wrapper patch\n'
  printf -- '- Wrapper purpose: execute `/usr/bin/mmdebstrap` while bypassing only the source-style check that current perltidy applies to the older packaged script\n'
  if [[ -f $imported_source/.linux-fieldwork-source.json ]]; then
    printf '\n## Imported source\n\n```json\n'
    cat "$imported_source/.linux-fieldwork-source.json"
    printf '\n```\n'
  fi
  printf '\n## Test and override hashes\n\n```text\n'
  sha256sum \
    "$imported_source/debian/tests/control" \
    "$imported_source/debian/tests/testsuite" \
    "$imported_source/coverage.py" \
    "$imported_source/coverage.txt" \
    "$imported_source/make_mirror.sh" \
    "$override_patch" \
    "$source_tree/debian/tests/testsuite"
  printf '```\n'
  printf '\n## Tool versions\n\n```text\n'
  dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
    autopkgtest mmdebstrap perltidy apt dpkg patch 2>&1 || true
  printf 'autopkgtest executable\t%s\n' "$(command -v autopkgtest)"
  printf '``\n'
  printf '\n## APT policy\n\n```text\n'
  apt-cache policy base-files mmdebstrap perltidy apt dpkg 2>&1 || true
  printf '```\n'
} >"$run_dir/provenance.md"

# Fix the accidental two-backtick fence above without hiding the exact generated text.
sed -i 's/^``$/```/' "$run_dir/provenance.md"

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
  printf -- '- Style-gate override: `installed-command-wrapper.patch`\n'
  if [[ -f $console_log ]]; then
    printf -- '- Console SHA-256: `%s`\n' "$(sha256sum "$console_log" | cut -d' ' -f1)"
  fi
} >"$run_dir/result.md"

exit "$status"
