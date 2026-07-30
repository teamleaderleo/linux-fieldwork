#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
source_root="$repo_root/upstream/mmdebstrap"
result_dir="$repo_root/investigations/mmdebstrap-unwritable-tmpdir/results"
runtime_root="${RUNNER_TEMP:-/tmp}/linux-fieldwork-mmdebstrap-tmpdir"
unwritable_tmp="$runtime_root/unwritable"
writable_tmp="$runtime_root/writable"
unwritable_log="$result_dir/unwritable.log"
writable_log="$result_dir/writable.log"
summary_file="$result_dir/summary.json"
source_spec="deb [trusted=yes] https://deb.debian.org/debian sid main"

cleanup() {
  chmod 0700 "$unwritable_tmp" 2>/dev/null || true
  rm -rf "$runtime_root"
}
trap cleanup EXIT INT TERM

rm -rf "$runtime_root" "$result_dir"
mkdir -p "$unwritable_tmp" "$writable_tmp" "$result_dir"
chmod 0555 "$unwritable_tmp"

if touch "$unwritable_tmp/should-fail" 2>/dev/null; then
  echo "probe setup failed: unwritable TMPDIR accepts files" >&2
  exit 1
fi

chmod +x "$source_root/mmdebstrap"

set +e
TMPDIR="$unwritable_tmp" timeout 240 \
  "$source_root/mmdebstrap" \
  --dry-run \
  --mode=chrootless \
  --variant=apt \
  sid \
  /dev/null \
  "$source_spec" \
  >"$unwritable_log" 2>&1
unwritable_status=$?
set -e

unwritable_selected="$(sed -n 's/^I: using \(.*\) as tempdir$/\1/p' "$unwritable_log" | head -n 1)"

if [[ "$unwritable_status" -eq 0 ]]; then
  echo "expected explicit unwritable TMPDIR to fail" >&2
  cat "$unwritable_log" >&2
  exit 1
fi

if [[ -n "$unwritable_selected" ]]; then
  echo "mmdebstrap selected a fallback directory after explicit TMPDIR failed: $unwritable_selected" >&2
  exit 1
fi

grep -F 'Error in tempdir()' "$unwritable_log"
grep -F "$unwritable_tmp" "$unwritable_log"
grep -F 'Permission denied' "$unwritable_log"

TMPDIR="$writable_tmp" timeout 240 \
  "$source_root/mmdebstrap" \
  --dry-run \
  --mode=chrootless \
  --variant=apt \
  sid \
  /dev/null \
  "$source_spec" \
  >"$writable_log" 2>&1
writable_status=$?
writable_selected="$(sed -n 's/^I: using \(.*\) as tempdir$/\1/p' "$writable_log" | head -n 1)"

if [[ "$writable_status" -ne 0 ]]; then
  echo "writable explicit TMPDIR unexpectedly failed" >&2
  cat "$writable_log" >&2
  exit 1
fi

if [[ "$writable_selected" != "$writable_tmp"/mmdebstrap.* ]]; then
  echo "writable explicit TMPDIR was not honored: $writable_selected" >&2
  exit 1
fi

if find "$writable_tmp" -mindepth 1 -print -quit | grep -q .; then
  echo "temporary files remained under writable TMPDIR" >&2
  find "$writable_tmp" -mindepth 1 -maxdepth 2 -print >&2
  exit 1
fi

candidate_commit="$(git rev-parse HEAD)"
python3 - "$summary_file" "$candidate_commit" "$unwritable_tmp" "$unwritable_status" "$writable_tmp" "$writable_status" "$writable_selected" <<'PY'
import json
import pathlib
import sys

(
    path,
    candidate_commit,
    unwritable_tmp,
    unwritable_status,
    writable_tmp,
    writable_status,
    writable_selected,
) = sys.argv[1:]

data = {
    "upstream_revision": "6fde999741f4fe1e7bf38079acf29432ef87a35e",
    "candidate_commit": candidate_commit,
    "mode": "chrootless",
    "unwritable_case": {
        "requested_tmpdir": unwritable_tmp,
        "command_status": int(unwritable_status),
        "selected_tmpdir": None,
        "diagnostic_names_requested_tmpdir": True,
        "diagnostic_source": "File::Temp tempdir",
        "result": "rejected",
    },
    "writable_case": {
        "requested_tmpdir": writable_tmp,
        "command_status": int(writable_status),
        "selected_tmpdir": writable_selected,
        "cleanup_complete": True,
        "result": "honored",
    },
}
pathlib.Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2))
PY

echo "Verified: unusable explicit TMPDIR fails at File::Temp; writable explicit TMPDIR remains honored"
