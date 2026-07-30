#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-unwritable-tmpdir/results"
runtime_root="${RUNNER_TEMP:-/tmp}/linux-fieldwork-mmdebstrap-tmpdir"
unwritable_tmp="$runtime_root/unwritable"
log_file="$result_dir/mmdebstrap.log"
summary_file="$result_dir/summary.json"

rm -rf "$runtime_root" "$result_dir"
mkdir -p "$unwritable_tmp" "$result_dir"
chmod 0555 "$unwritable_tmp"

if touch "$unwritable_tmp/should-fail" 2>/dev/null; then
  echo "probe setup failed: TMPDIR is writable" >&2
  exit 1
fi

chmod +x "$source_root/mmdebstrap"

set +e
TMPDIR="$unwritable_tmp" timeout 240 \
  "$source_root/mmdebstrap" \
  --dry-run \
  --mode=unshare \
  --variant=apt \
  sid \
  /dev/null \
  https://deb.debian.org/debian \
  >"$log_file" 2>&1
command_status=$?
set -e

selected_tmp="$(sed -n 's/^I: using \(.*\) as tempdir$/\1/p' "$log_file" | head -n 1)"
warning_for_requested_tmp=false
if grep -Eiq "(warn|error|cannot|failed).*$unwritable_tmp|$unwritable_tmp.*(warn|error|cannot|failed)" "$log_file"; then
  warning_for_requested_tmp=true
fi

python3 - "$summary_file" "$command_status" "$unwritable_tmp" "$selected_tmp" "$warning_for_requested_tmp" <<'PY'
import json
import pathlib
import sys

path, status, requested, selected, warned = sys.argv[1:]
data = {
    "source_revision": "6fde999741f4fe1e7bf38079acf29432ef87a35e",
    "requested_tmpdir": requested,
    "requested_tmpdir_writable": False,
    "selected_tmpdir": selected or None,
    "command_status": int(status),
    "diagnostic_mentions_unwritable_tmpdir": warned == "true",
}
pathlib.Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2))
PY

if [[ -z "$selected_tmp" ]]; then
  echo "mmdebstrap did not log a selected temporary directory" >&2
  tail -n 80 "$log_file" >&2
  exit 1
fi

if [[ "$selected_tmp" == "$unwritable_tmp"/* ]]; then
  echo "mmdebstrap used the requested unwritable TMPDIR unexpectedly" >&2
  exit 1
fi

if [[ "$selected_tmp" != /tmp/mmdebstrap.* ]]; then
  echo "mmdebstrap selected an unexpected fallback directory: $selected_tmp" >&2
  exit 1
fi

if [[ "$warning_for_requested_tmp" == true ]]; then
  echo "mmdebstrap reported the unusable TMPDIR; silent fallback was not reproduced" >&2
  exit 1
fi

echo "Reproduced: explicit unwritable TMPDIR was silently replaced with $selected_tmp"
