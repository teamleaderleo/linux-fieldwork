#!/usr/bin/env bash
# Run the imported mmdebstrap Debian autopkgtest and retain a compact evidence set.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_tree="$repo_root/upstream/mmdebstrap"
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
if ! command -v autopkgtest >/dev/null 2>&1; then
  printf 'autopkgtest is unavailable\n' >&2
  printf '77\n' >"$status_file"
  exit 77
fi
if [[ ! -f $source_tree/debian/tests/control ]]; then
  printf 'imported mmdebstrap source tree is missing\n' >&2
  printf '2\n' >"$status_file"
  exit 2
fi

"$repo_root/scripts/capture-linux-context.sh" "$run_dir/context.md"

{
  printf '# Reproduction provenance\n\n'
  printf -- '- Started: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Run ID: `%s`\n' "$run_id"
  printf -- '- Timeout: `%s`\n' "$timeout_duration"
  printf -- '- Source path: `%s`\n' "upstream/mmdebstrap"
  if [[ -f $source_tree/.linux-fieldwork-source.json ]]; then
    printf '\n## Imported source\n\n```json\n'
    cat "$source_tree/.linux-fieldwork-source.json"
    printf '\n```\n'
  fi
  printf '\n## Test source hashes\n\n```text\n'
  sha256sum \
    "$source_tree/debian/tests/control" \
    "$source_tree/debian/tests/testsuite" \
    "$source_tree/coverage.py" \
    "$source_tree/coverage.txt" \
    "$source_tree/make_mirror.sh"
  printf '```\n'
  printf '\n## Tool versions\n\n```text\n'
  dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
    autopkgtest mmdebstrap apt dpkg 2>&1 || true
  printf 'autopkgtest executable\t%s\n' "$(command -v autopkgtest)"
  printf '```\n'
  printf '\n## APT policy\n\n```text\n'
  apt-cache policy base-files mmdebstrap apt dpkg 2>&1 || true
  printf '```\n'
} >"$run_dir/provenance.md"

dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  >"$run_dir/package-versions-before.tsv" 2>"$run_dir/package-query-before.err" || true

printf '%q ' timeout --signal=INT --kill-after=5m "$timeout_duration" \
  autopkgtest --output-dir "$output_dir" "$source_tree" -- null \
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
  if [[ -f $console_log ]]; then
    printf -- '- Console SHA-256: `%s`\n' "$(sha256sum "$console_log" | cut -d' ' -f1)"
  fi
} >"$run_dir/result.md"

exit "$status"
