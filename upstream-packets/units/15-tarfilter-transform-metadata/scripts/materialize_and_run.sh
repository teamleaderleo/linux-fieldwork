#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
UNIT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO=$(CDPATH= cd -- "$UNIT_DIR/../../.." && pwd)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/unit15-matrix.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

SOURCE="$REPO/upstream/mmdebstrap/tarfilter"
PREDECESSOR_PATCH="$REPO/investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch"
COMPOSED_PATCH="$UNIT_DIR/patches/0001-tarfilter-transform-metadata.patch"

for path in "$SOURCE" "$PREDECESSOR_PATCH" "$COMPOSED_PATCH"; do
    if [ ! -f "$path" ]; then
        echo "missing required file: $path" >&2
        exit 2
    fi
done

mkdir -p "$TMP/scripts" "$TMP/upstream/mmdebstrap" "$TMP/predecessor/upstream/mmdebstrap" "$TMP/candidate/upstream/mmdebstrap"
cp "$SCRIPT_DIR/run_matrix.py" "$TMP/scripts/run_unit15_matrix.py"
cp "$SOURCE" "$TMP/upstream/mmdebstrap/tarfilter"
cp "$SOURCE" "$TMP/predecessor/upstream/mmdebstrap/tarfilter"
cp "$SOURCE" "$TMP/candidate/upstream/mmdebstrap/tarfilter"

# The historical PR #68 carrier is retained as a Git patch and applies with
# line offsets. It is used only as the negative predecessor for numeric flags.
git -C "$TMP/predecessor" init -q
git -C "$TMP/predecessor" add upstream/mmdebstrap/tarfilter
git -C "$TMP/predecessor" -c user.name=unit15 -c user.email=unit15@example.invalid commit -qm baseline
git -C "$TMP/predecessor" apply "$PREDECESSOR_PATCH"

# The regenerated unit patch is the release candidate carrier. GNU patch must
# apply it with zero fuzz; clean output means no offsets or fuzz were used.
patch --fuzz=0 -p1 -d "$TMP/candidate" -i "$COMPOSED_PATCH" >/dev/null

python3 "$TMP/scripts/run_unit15_matrix.py"
