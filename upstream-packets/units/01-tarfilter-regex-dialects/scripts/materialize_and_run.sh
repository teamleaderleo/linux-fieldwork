#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
packet="$repo_root/upstream-packets/units/01-tarfilter-regex-dialects"
base="$repo_root/upstream/mmdebstrap/tarfilter"
expected_base_blob=ad776167a8473d5d15dbe22e850f4f6db35cf278
expected_prerequisite_blob=adb330efcc941bf5e646f195c245a3184e42f8e2
expected_candidate_blob=ca8e656c036172230c796a8a12cb17f262108c39

actual_base_blob=$(git -C "$repo_root" hash-object "$base")
[ "$actual_base_blob" = "$expected_base_blob" ] || {
    echo "unexpected base blob: $actual_base_blob" >&2
    exit 1
}

work=$(mktemp -d)
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT HUP INT TERM
mkdir -p "$work/upstream/mmdebstrap"
cp "$base" "$work/upstream/mmdebstrap/tarfilter"
cp "$base" "$work/tarfilter.base"

patch --fuzz=0 -p1 -d "$work" \
  -i "$packet/patches/0001-transform-metadata-prerequisite.patch"
cp "$work/upstream/mmdebstrap/tarfilter" "$work/tarfilter.prerequisite"
actual_prerequisite_blob=$(git -C "$repo_root" hash-object "$work/tarfilter.prerequisite")
[ "$actual_prerequisite_blob" = "$expected_prerequisite_blob" ] || {
    echo "unexpected prerequisite blob: $actual_prerequisite_blob" >&2
    exit 1
}

patch --fuzz=0 -p1 -d "$work" \
  -i "$packet/patches/0002-tarfilter-regex-dialects.patch"
actual_candidate_blob=$(git -C "$repo_root" hash-object "$work/upstream/mmdebstrap/tarfilter")
[ "$actual_candidate_blob" = "$expected_candidate_blob" ] || {
    echo "unexpected candidate blob: $actual_candidate_blob" >&2
    exit 1
}

python3 -m py_compile "$work/upstream/mmdebstrap/tarfilter"
LC_ALL=C python3 "$packet/scripts/run_matrix.py" \
  --baseline "$work/tarfilter.base" \
  --prerequisite "$work/tarfilter.prerequisite" \
  --candidate "$work/upstream/mmdebstrap/tarfilter"
