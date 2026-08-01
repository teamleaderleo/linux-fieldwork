#!/usr/bin/env bash
# Read-only audit of canonical mmdebstrap and Debian carriers for unit 09.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
run_id=${RUN_ID:-"local-$(date -u +%Y%m%dT%H%M%SZ)"}
run_dir=${RUN_DIR:-"$repo_root/investigations/mmdebstrap-dev-ptmx-bsdutils/canonical-audit/$run_id"}
expected_head=${EXPECTED_CANONICAL_HEAD:-77ec9be5417ee44c96343d2347145585da1b1f94}
canonical_url=https://gitlab.mister-muffin.de/josch/mmdebstrap.git
salsa_url=https://salsa.debian.org/debian/mmdebstrap.git
mkdir -p "$run_dir"

work_root=$(mktemp -d "${TMPDIR:-/tmp}/lf-mmdebstrap-canonical.XXXXXXXX")
cleanup() {
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

exec > >(tee "$run_dir/audit.stdout") 2> >(tee "$run_dir/audit.stderr" >&2)

printf 'run_id=%s\n' "$run_id" >"$run_dir/context.env"
printf 'started=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$run_dir/context.env"
printf 'expected_canonical_head=%s\n' "$expected_head" >>"$run_dir/context.env"
printf 'canonical_url=%s\n' "$canonical_url" >>"$run_dir/context.env"
printf 'salsa_url=%s\n' "$salsa_url" >>"$run_dir/context.env"
git --version >"$run_dir/git-version.txt"
curl --version >"$run_dir/curl-version.txt"

clone_mirror() {
  local name=$1
  local url=$2
  local mirror="$work_root/$name.git"
  printf 'Cloning %s read-only from %s\n' "$name" "$url"
  git clone --mirror "$url" "$mirror" \
    >"$run_dir/$name-clone.stdout" 2>"$run_dir/$name-clone.stderr"
  git --git-dir="$mirror" remote -v >"$run_dir/$name-remotes.txt"
  git --git-dir="$mirror" show-ref >"$run_dir/$name-refs.txt"
  git --git-dir="$mirror" for-each-ref \
    --sort=refname \
    --format='%(refname)%09%(objectname)%09%(objecttype)%09%(subject)' \
    >"$run_dir/$name-ref-inventory.tsv"
  printf '%s\n' "$mirror"
}

canonical_mirror=$(clone_mirror canonical "$canonical_url" | tail -n1)
canonical_head=$(git --git-dir="$canonical_mirror" rev-parse refs/heads/main)
printf '%s\n' "$canonical_head" >"$run_dir/canonical-main-head.txt"

if ! git --git-dir="$canonical_mirror" cat-file -e "$canonical_head:tests/dev-ptmx"; then
  printf 'tests/dev-ptmx is absent at canonical head %s\n' "$canonical_head" >&2
  exit 2
fi

git --git-dir="$canonical_mirror" show "$canonical_head:tests/dev-ptmx" \
  >"$run_dir/canonical-tests-dev-ptmx"
git --git-dir="$canonical_mirror" rev-parse "$canonical_head:tests/dev-ptmx" \
  >"$run_dir/canonical-tests-dev-ptmx-blob.txt"
sha256sum "$run_dir/canonical-tests-dev-ptmx" \
  >"$run_dir/canonical-tests-dev-ptmx.sha256"
grep -n -- '--include=' "$run_dir/canonical-tests-dev-ptmx" \
  >"$run_dir/canonical-include-lines.txt" || true
grep -n -F 'script -c' "$run_dir/canonical-tests-dev-ptmx" \
  >"$run_dir/canonical-script-hooks.txt" || true

# Full path history, including patches, and exact pickaxe searches.
git --git-dir="$canonical_mirror" log --all --follow --date=iso-strict \
  --format='commit %H%nparents %P%nauthor %an <%ae>%nauthor-date %aI%ncommitter-date %cI%nsubject %s%nbody%n%b%n---' \
  -- tests/dev-ptmx >"$run_dir/canonical-dev-ptmx-history.txt"
git --git-dir="$canonical_mirror" log --all --follow --date=iso-strict -p \
  -- tests/dev-ptmx >"$run_dir/canonical-dev-ptmx-history.patch"
git --git-dir="$canonical_mirror" log --all --date=iso-strict -p \
  -S'--include=bsdutils,gcc,libc6-dev,python3,passwd' -- tests/dev-ptmx \
  >"$run_dir/canonical-pickaxe-corrected-include.patch"
git --git-dir="$canonical_mirror" log --all --date=iso-strict -p \
  -S'--include=gcc,libc6-dev,python3,passwd' -- tests/dev-ptmx \
  >"$run_dir/canonical-pickaxe-baseline-include.patch"
git --git-dir="$canonical_mirror" log --all --date=iso-strict -p \
  -G'bsdutils|dev-ptmx|script -c' -- tests/dev-ptmx \
  >"$run_dir/canonical-regex-overlap-history.patch"
git --git-dir="$canonical_mirror" log --all --date=iso-strict \
  --regexp-ignore-case --extended-regexp \
  --grep='bsdutils|dev-ptmx|script\(1\)|pseudo.?terminal|pty' \
  --format='%H%x09%aI%x09%s' >"$run_dir/canonical-message-overlap.tsv"

: >"$run_dir/canonical-ref-content-overlap.txt"
while IFS= read -r ref; do
  git --git-dir="$canonical_mirror" grep -n -I -E \
    'bsdutils|--include=.*gcc,libc6-dev,python3,passwd|script -c' \
    "$ref" -- tests/dev-ptmx \
    >>"$run_dir/canonical-ref-content-overlap.txt" 2>/dev/null || true
done < <(git --git-dir="$canonical_mirror" for-each-ref \
  --format='%(refname)' refs/heads refs/remotes refs/tags)

# Query canonical public issue and pull-request metadata without making writes.
forgejo_api=https://gitlab.mister-muffin.de/api/v1/repos/josch/mmdebstrap
curl --fail --location --silent --show-error \
  "$forgejo_api/issues?state=all&type=issues&limit=50&page=1" \
  >"$run_dir/forgejo-issues-page1.json"
curl --fail --location --silent --show-error \
  "$forgejo_api/pulls?state=all&limit=50&page=1" \
  >"$run_dir/forgejo-pulls-page1.json"\n
# Debian packaging history can carry changes absent from a downstream GitHub fork.
salsa_mirror=$(clone_mirror salsa "$salsa_url" | tail -n1)
git --git-dir="$salsa_mirror" log --all --date=iso-strict \
  --format='%H%x09%aI%x09%D%x09%s' >"$run_dir/salsa-all-history.tsv"
git --git-dir="$salsa_mirror" log --all --date=iso-strict -p \
  -G'bsdutils|dev-ptmx|script -c' -- tests/dev-ptmx \
  >"$run_dir/salsa-dev-ptmx-overlap.patch"
: >"$run_dir/salsa-ref-content-overlap.txt"
while IFS= read -r ref; do
  git --git-dir="$salsa_mirror" grep -n -I -E \
    'bsdutils|--include=.*gcc,libc6-dev,python3,passwd|script -c' \
    "$ref" -- tests/dev-ptmx \
    >>"$run_dir/salsa-ref-content-overlap.txt" 2>/dev/null || true
done < <(git --git-dir="$salsa_mirror" for-each-ref \
  --format='%(refname)' refs/heads refs/remotes refs/tags)

# Official Debian BTS and mailing-list searches. These are read-only requests.
curl --fail --location --silent --show-error \
  'https://bugs.debian.org/cgi-bin/pkgreport.cgi?archive=both;src=mmdebstrap' \
  >"$run_dir/debian-bts-mmdebstrap.html"
for query in \
  'mmdebstrap dev-ptmx' \
  'mmdebstrap bsdutils' \
  'dev-ptmx bsdutils' \
  'mmdebstrap script pseudo terminal'; do
  slug=$(printf '%s' "$query" | tr ' /' '__' | tr -cd '[:alnum:]_-')
  encoded=$(python3 - "$query" <<'PY'
import sys
import urllib.parse
print(urllib.parse.quote_plus(sys.argv[1]))
PY
)
  curl --fail --location --silent --show-error \
    "https://lists.debian.org/cgi-bin/search?P=$encoded&DEFAULTOP=and&SORT=0&HITSPERPAGE=100" \
    >"$run_dir/debian-lists-$slug.html"
done

python3 - "$run_dir" "$canonical_head" "$expected_head" <<'PY'
from __future__ import annotations

import json
import pathlib
import re
import sys

run_dir = pathlib.Path(sys.argv[1])
canonical_head = sys.argv[2]
expected_head = sys.argv[3]
source = (run_dir / "canonical-tests-dev-ptmx").read_text(encoding="utf-8")
blob = (run_dir / "canonical-tests-dev-ptmx-blob.txt").read_text().strip()
sha256 = (run_dir / "canonical-tests-dev-ptmx.sha256").read_text().split()[0]

corrected = "--include=bsdutils,gcc,libc6-dev,python3,passwd"
baseline = "--include=gcc,libc6-dev,python3,passwd"
if corrected in source:
    disposition = "equivalent-present"
elif baseline in source:
    disposition = "correction-absent-exact-baseline"
else:
    disposition = "source-drift-requires-review"

terms = re.compile(r"bsdutils|dev-ptmx|script\s*-c|pseudo.?terminal|pty", re.I)

def json_hits(path: pathlib.Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    hits: list[dict[str, object]] = []
    for item in data:
        haystack = "\n".join(
            str(item.get(key, "")) for key in ("title", "body", "html_url", "url")
        )
        if terms.search(haystack):
            hits.append(
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "url": item.get("html_url") or item.get("url"),
                }
            )
    return hits

forgejo_issue_hits = json_hits(run_dir / "forgejo-issues-page1.json")
forgejo_pull_hits = json_hits(run_dir / "forgejo-pulls-page1.json")

mail_hits: dict[str, int] = {}
for path in sorted(run_dir.glob("debian-lists-*.html")):
    text = path.read_text(encoding="utf-8", errors="replace")
    # Debian's search page reports a result table or explicit no-hit text.
    mail_hits[path.name] = len(re.findall(r"(?i)(mmdebstrap|dev-ptmx|bsdutils)", text))

bts_text = (run_dir / "debian-bts-mmdebstrap.html").read_text(
    encoding="utf-8", errors="replace"
)
bts_overlap_lines = [
    line.strip()
    for line in bts_text.splitlines()
    if terms.search(line)
][:50]

canonical_overlap = (run_dir / "canonical-pickaxe-corrected-include.patch").read_text(
    encoding="utf-8", errors="replace"
)
salsa_overlap = (run_dir / "salsa-dev-ptmx-overlap.patch").read_text(
    encoding="utf-8", errors="replace"
)

summary = {
    "canonical_head": canonical_head,
    "expected_head": expected_head,
    "head_matches_expected": canonical_head == expected_head,
    "canonical_dev_ptmx_blob": blob,
    "canonical_dev_ptmx_sha256": sha256,
    "disposition": disposition,
    "include_lines": [line for line in source.splitlines() if "--include=" in line],
    "inner_script_hook_count": source.count("script -c"),
    "corrected_include_history_present": bool(canonical_overlap.strip()),
    "forgejo_issue_hits": forgejo_issue_hits,
    "forgejo_pull_hits": forgejo_pull_hits,
    "salsa_overlap_history_present": bool(salsa_overlap.strip()),
    "debian_bts_overlap_lines": bts_overlap_lines,
    "debian_list_search_term_counts": mail_hits,
}
(run_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)

with (run_dir / "SUMMARY.md").open("w", encoding="utf-8") as handle:
    handle.write("# mmdebstrap unit-09 canonical audit\n\n")
    handle.write(f"- Canonical head: `{canonical_head}`\n")
    handle.write(f"- Expected head: `{expected_head}`\n")
    handle.write(f"- Head matches expected: `{canonical_head == expected_head}`\n")
    handle.write(f"- `tests/dev-ptmx` blob: `{blob}`\n")
    handle.write(f"- SHA-256: `{sha256}`\n")
    handle.write(f"- Disposition: `{disposition}`\n")
    handle.write(f"- Inner `script -c` hooks: `{source.count('script -c')}`\n")
    handle.write(
        f"- Corrected include found in canonical history: `{bool(canonical_overlap.strip())}`\n"
    )
    handle.write(f"- Forgejo issue overlap hits: `{len(forgejo_issue_hits)}`\n")
    handle.write(f"- Forgejo pull overlap hits: `{len(forgejo_pull_hits)}`\n")
    handle.write(
        f"- Salsa path-history overlap present: `{bool(salsa_overlap.strip())}`\n"
    )
    handle.write("\n## Canonical include lines\n\n```text\n")
    handle.write("\n".join(summary["include_lines"]) + "\n")
    handle.write("```\n")

print(json.dumps(summary, indent=2, sort_keys=True))

if disposition == "source-drift-requires-review":
    raise SystemExit(3)
PY

printf 'finished=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$run_dir/context.env"
printf '0\n' >"$run_dir/exit-status"
