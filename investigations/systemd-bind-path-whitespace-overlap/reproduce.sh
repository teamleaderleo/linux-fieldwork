#!/usr/bin/env bash
set -euo pipefail

out=${1:-artifacts/systemd-bind-path-whitespace}
analyze=${SYSTEMD_ANALYZE:-systemd-analyze}
mkdir -p "$out/cases"
out=$(cd "$out" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/systemd-bind-whitespace.XXXXXX")
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

write_unit() {
    local name=$1
    local directive_text=$2
    cat >"$work/$name.service" <<UNIT
[Unit]
Description=Bind-path parser probe: $name

[Service]
Type=oneshot
ExecStart=/usr/bin/true
$directive_text
UNIT
}

# Reported failures and whitespace variants.
write_unit repeated-space \
    'BindReadOnlyPaths=/usr/bin  /usr/lib  /usr/share'
write_unit mixed-whitespace \
    $'BindPaths=/usr/bin\t \t/usr/lib   /usr/share'
write_unit continued-space \
    $'BindPaths=/usr/bin \\\n          /usr/lib \\\n          /usr/share'

# Stable valid controls from systemd.exec's documented grammar.
write_unit one-space \
    'BindReadOnlyPaths=/usr/bin /usr/lib /usr/share'
write_unit source-only \
    'BindPaths=/usr/bin'
write_unit full-triple \
    'BindPaths=/usr/bin:/usr/bin:norbind /usr/lib:/usr/lib:rbind'
write_unit quoted-spaces \
    'BindReadOnlyPaths="/tmp/source with space":"/tmp/destination with space":norbind'
write_unit escaped-colons \
    'BindPaths=/tmp/source\:colon:/tmp/destination\:colon:norbind'
write_unit ignore-missing \
    'BindReadOnlyPaths=-/definitely/not/present:/tmp/fieldwork-bind-destination:norbind'
write_unit reset \
    $'BindPaths=/usr/bin /usr/lib\nBindPaths=\nBindPaths=/usr/share'

# Documented invalid controls. systemd.exec says that when destination is
# omitted, the option string must be omitted too.
write_unit omitted-destination-options \
    'BindPaths=/usr/bin::norbind'
write_unit too-many-fields \
    'BindPaths=/usr/bin:/usr/bin:norbind:extra'
write_unit invalid-option \
    'BindPaths=/usr/bin:/usr/bin:nosuid'

{
    "$analyze" --version
    uname -srvmo
    printf 'analyzer=%s\n' "$analyze"
} >"$out/identity.txt"

: >"$out/results.tsv"
for unit in "$work"/*.service; do
    name=$(basename "$unit" .service)
    stdout="$out/cases/$name.stdout"
    stderr="$out/cases/$name.stderr"
    status=0
    "$analyze" verify "$unit" >"$stdout" 2>"$stderr" || status=$?
    printf '%s\t%d\t%s\t%s\n' \
        "$name" \
        "$status" \
        "$(sha256sum "$stdout" | cut -d' ' -f1)" \
        "$(sha256sum "$stderr" | cut -d' ' -f1)" \
        >>"$out/results.tsv"
done

cp "$work"/*.service "$out/cases/"
cat "$out/identity.txt"
cat "$out/results.tsv"

# Fixture controls: the analyzer must run and ordinary syntax must not produce
# the empty-path warning that identifies issue #43214.
grep -q '^one-space' "$out/results.tsv"
if grep -Fq 'Empty path in bind mount' "$out/cases/one-space.stderr"; then
    echo 'ordinary one-space control produced empty-path warning' >&2
    exit 1
fi
