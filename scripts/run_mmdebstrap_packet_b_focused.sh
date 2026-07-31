#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
imported_source="$repo_root/upstream/mmdebstrap"
investigation_root="$repo_root/investigations/mmdebstrap-packet-b-focused"
run_root="$investigation_root/runs"
capability_patch="$repo_root/investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure/0001-run-hook-free-capability-case-as-hard-failure.patch"
proxy_patch="$investigation_root/0001-use-installed-mmdebstrap-proxy.patch"
prepare_tool="$repo_root/tools/prepare_mmdebstrap_packet_b_focused.py"
verify_tool="$repo_root/tools/verify_mmdebstrap_packet_b_focused.py"
runtime_guard="$repo_root/investigations/mmdebstrap-unwritable-tmpdir/runtime_guard.sh"
run_id=${RUN_ID:-"local-$(date -u +%Y%m%dT%H%M%SZ)"}
timeout_duration=${FOCUSED_TIMEOUT:-80m}

classify_status() {
  local raw_status=$1 verifier_status=$2
  case "$raw_status" in
    0)
      if [[ $verifier_status -eq 0 ]]; then
        printf '0 focused-pass\n'
      else
        printf '2 evidence-verification-failure\n'
      fi
      ;;
    124)
      printf '77 outer-timeout-neutral\n'
      ;;
    *)
      printf '%s focused-hard-failure\n' "$raw_status"
      ;;
  esac
}

if [[ ${1-} == --classify-status ]]; then
  [[ $# -eq 3 && $2 =~ ^[0-9]+$ && $3 =~ ^[0-9]+$ ]] || {
    echo 'usage: run_mmdebstrap_packet_b_focused.sh --classify-status RAW VERIFIER' >&2
    exit 2
  }
  classify_status "$2" "$3"
  exit
fi

case "$run_id" in
  ''|.|..|*/*|*[!A-Za-z0-9._-]*)
    echo "refusing unsafe run id: $run_id" >&2
    exit 2
    ;;
esac

source "$runtime_guard"
runtime_leaf="lf-mmdebstrap-packet-b-$run_id"

if [[ ${1-} == --check-runtime-parent ]]; then
  [[ $# -eq 2 ]] || {
    echo 'usage: run_mmdebstrap_packet_b_focused.sh --check-runtime-parent PATH' >&2
    exit 2
  }
  validate_disposable_runtime \
    "$repo_root" "${HOME:-/nonexistent-home}" "$2" "$runtime_leaf" \
    >/dev/null
  exit
fi

runtime="$(validate_disposable_runtime \
  "$repo_root" \
  "${HOME:-/nonexistent-home}" \
  "${TMPDIR:-/tmp}" \
  "$runtime_leaf")"
run_root="$(realpath -m "$run_root")"
run_dir="$(realpath -m "$run_root/$run_id")"
case "$run_dir" in
  "$run_root"/*) ;;
  *)
    echo "refusing result directory outside run root: $run_dir" >&2
    exit 2
    ;;
esac
mkdir -p "$run_dir"
if find "$run_dir" -mindepth 1 -maxdepth 1 \
    ! -name 'repository-*' -print -quit | grep -q .; then
  echo "refusing nonempty run directory: $run_dir" >&2
  exit 2
fi

cleanup() {
  chmod -R u+w "$runtime" 2>/dev/null || true
  rm -rf -- "$runtime"
}

finish() {
  local primary_status=$1 cleanup_status=0
  trap '' INT TERM
  trap - EXIT
  cleanup || cleanup_status=$?
  if [[ $primary_status -ne 0 ]]; then
    exit "$primary_status"
  fi
  exit "$cleanup_status"
}

exit_cleanup() {
  finish "$?"
}

trap exit_cleanup EXIT
trap 'finish 130' INT
trap 'finish 143' TERM

finish_early() {
  local status=$1
  shift
  local reason=$*
  printf '%s\n' "$reason" >&2
  printf '%s\n' "$status" >"$run_dir/carrier-exit-status"
  printf '%s\n' "$reason" >"$run_dir/preflight-error.txt"
  {
    printf '# Packet B focused result\n\n'
    printf -- '- Finished: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf -- '- Carrier status: `%s`\n' "$status"
    printf -- '- Classification: `carrier-preflight-failure`\n'
    printf -- '- Reason: `%s`\n' "$reason"
  } >"$run_dir/result.md"
  exit "$status"
}

apply_exact_patch() {
  local label=$1 patch_path=$2
  local stdout_path="$run_dir/$label-patch.stdout"
  local stderr_path="$run_dir/$label-patch.stderr"
  if ! patch --batch --forward --fuzz=0 -p1 -d "$source_tree" \
      -i "$patch_path" >"$stdout_path" 2>"$stderr_path"; then
    return 1
  fi
  if grep -Eiq '(^|[^[:alpha:]])(fuzz|offset)([^[:alpha:]]|$)' \
      "$stdout_path" "$stderr_path"; then
    printf 'patch %s applied with fuzz or offset\n' "$label" \
      >>"$stderr_path"
    return 2
  fi
}

if [[ $(id -u) -ne 0 ]]; then
  finish_early 77 "focused sid run requires root in a disposable test container"
fi
for command_name in autopkgtest patch python3 realpath sha256sum sh timeout; do
  command -v "$command_name" >/dev/null 2>&1 || \
    finish_early 77 "$command_name is unavailable"
done
for required in \
  "$imported_source/debian/tests/control" \
  "$imported_source/debian/tests/testsuite" \
  "$capability_patch" \
  "$proxy_patch" \
  "$prepare_tool" \
  "$verify_tool"; do
  [[ -f "$required" ]] || finish_early 2 "missing required input: $required"
done

rm -rf -- "$runtime"
mkdir -p "$runtime"
source_tree="$runtime/mmdebstrap"
output_dir="$run_dir/autopkgtest-output"
console_log="$run_dir/autopkgtest-console.log"
raw_status_file="$run_dir/autopkgtest-exit-status"
verifier_receipt="$run_dir/focused-verification.json"
cp -a "$imported_source" "$source_tree"

apply_exact_patch capability "$capability_patch" || \
  finish_early 2 "hook-free hard-failure patch failed exact application"
apply_exact_patch installed-proxy "$proxy_patch" || \
  finish_early 2 "installed-package proxy patch failed exact application"
python3 "$prepare_tool" \
  "$source_tree/debian/tests/testsuite" \
  --receipt "$run_dir/preparation-receipt.json" \
  >"$run_dir/preparation.stdout" \
  2>"$run_dir/preparation.stderr" || \
  finish_early 2 "focused testsuite preparation failed"
sh -n "$source_tree/debian/tests/testsuite" || \
  finish_early 2 "prepared package testsuite failed shell syntax"

{
  printf '# Packet B focused provenance\n\n'
  printf -- '- Started: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Run ID: `%s`\n' "$run_id"
  printf -- '- Outer timeout: `%s`\n' "$timeout_duration"
  printf -- '- Imported source: `upstream/mmdebstrap`\n'
  printf -- '- Product command: installed `/usr/bin/mmdebstrap` through a formatted proxy\n'
  printf -- '- Focused order: `create-directory`, `root-without-cap-sys-admin`, explicit stop\n'
  printf -- '- Broad phase: `not executed by construction`\n'
  printf -- '- Patch placement: `zero fuzz and zero offset`\n'
  printf '\n## Input hashes\n\n```text\n'
  sha256sum \
    "$imported_source/debian/tests/control" \
    "$imported_source/debian/tests/testsuite" \
    "$imported_source/coverage.py" \
    "$imported_source/coverage.txt" \
    "$capability_patch" \
    "$proxy_patch" \
    "$prepare_tool" \
    "$verify_tool"
  printf '```\n'
  if [[ -f "$imported_source/.linux-fieldwork-source.json" ]]; then
    printf '\n## Imported source identity\n\n```json\n'
    cat "$imported_source/.linux-fieldwork-source.json"
    printf '\n```\n'
  fi
} >"$run_dir/provenance.md"

printf '%q ' timeout --signal=INT --kill-after=5m "$timeout_duration" \
  autopkgtest --output-dir "$output_dir" '<temporary-source-copy>' -- null \
  >"$run_dir/command.txt"
printf '\n' >>"$run_dir/command.txt"

set +e
timeout --signal=INT --kill-after=5m "$timeout_duration" \
  autopkgtest --output-dir "$output_dir" "$source_tree" -- null \
  >"$console_log" 2>&1
raw_status=$?
set -e
printf '%s\n' "$raw_status" >"$raw_status_file"

set +e
python3 "$verify_tool" "$console_log" \
  --status-file "$raw_status_file" \
  --output "$verifier_receipt" \
  >"$run_dir/focused-verification.stdout" \
  2>"$run_dir/focused-verification.stderr"
verifier_status=$?
set -e
printf '%s\n' "$verifier_status" >"$run_dir/verifier-exit-status"

read -r carrier_status classification \
  < <(classify_status "$raw_status" "$verifier_status")
printf '%s\n' "$carrier_status" >"$run_dir/carrier-exit-status"

{
  printf '# Packet B focused result\n\n'
  printf -- '- Finished: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Raw autopkgtest status: `%s`\n' "$raw_status"
  printf -- '- Verifier status: `%s`\n' "$verifier_status"
  printf -- '- Carrier status: `%s`\n' "$carrier_status"
  printf -- '- Classification: `%s`\n' "$classification"
  printf -- '- Console SHA-256: `%s`\n' \
    "$(sha256sum "$console_log" | cut -d' ' -f1)"
  printf -- '- Imported source modified in place: `no`\n'
  printf -- '- Broad named cases permitted after consumer: `no`\n'
} >"$run_dir/result.md"

exit "$carrier_status"
