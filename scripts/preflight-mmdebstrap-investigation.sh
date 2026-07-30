#!/usr/bin/env bash
# Run offline checks for the mmdebstrap autopkgtest investigation.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python3 -m compileall -q tools tests
python3 -m unittest discover -s tests -v

bash -n scripts/capture-linux-context.sh
bash -n scripts/reproduce-mmdebstrap-autopkgtest.sh
bash -n scripts/preflight-mmdebstrap-investigation.sh

python3 tools/tar_manifest.py --help >/dev/null
python3 tools/manifest_diff.py --help >/dev/null
python3 tools/debian_bug_report.py --help >/dev/null
bash scripts/capture-linux-context.sh --help >/dev/null

context=$(mktemp)
trap 'rm -f "$context"' EXIT
bash scripts/capture-linux-context.sh "$context" >/dev/null
grep -Fq -- '- Host: `redacted`' "$context"
grep -Fq -- '- Sensitive fields included: `no`' "$context"

python3 - <<'PY'
import json
from pathlib import Path

metadata = json.loads(
    Path("upstream/mmdebstrap/.linux-fieldwork-source.json").read_text()
)
expected = "6fde999741f4fe1e7bf38079acf29432ef87a35e"
if metadata.get("resolved_commit") != expected:
    raise SystemExit(
        "unexpected imported mmdebstrap commit: "
        f"{metadata.get('resolved_commit')!r}"
    )
print(f"imported mmdebstrap commit: {expected}")
PY

sha256sum \
  upstream/mmdebstrap/debian/tests/control \
  upstream/mmdebstrap/debian/tests/testsuite \
  upstream/mmdebstrap/coverage.py \
  upstream/mmdebstrap/coverage.txt \
  upstream/mmdebstrap/make_mirror.sh

registered=$(awk '/^Test: / {count++} END {print count+0}' upstream/mmdebstrap/coverage.txt)
files=$(find upstream/mmdebstrap/tests -maxdepth 1 -type f | wc -l)
printf 'registered tests: %s\n' "$registered"
printf 'test files: %s\n' "$files"
