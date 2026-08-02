#!/usr/bin/env bash
set -euo pipefail

out=${1:-artifacts/systemd-bind-path-whitespace}
mkdir -p "$out"
out=$(cd "$out" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/systemd-bind-whitespace.XXXXXX")
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

cat >"$work/repeated-space.service" <<'UNIT'
[Unit]
Description=Repeated bind-path whitespace probe

[Service]
Type=oneshot
ExecStart=/usr/bin/true
BindReadOnlyPaths=/usr/bin  /usr/lib  /usr/share
UNIT

cat >"$work/continued-space.service" <<'UNIT'
[Unit]
Description=Continued bind-path whitespace probe

[Service]
Type=oneshot
ExecStart=/usr/bin/true
BindPaths=/usr/bin \
          /usr/lib \
          /usr/share
UNIT

cat >"$work/colon-control.service" <<'UNIT'
[Unit]
Description=Empty colon field compatibility control

[Service]
Type=oneshot
ExecStart=/usr/bin/true
BindReadOnlyPaths=/usr/bin::nosuid
UNIT

{
    systemd-analyze --version
    uname -srvmo
} >"$out/identity.txt"

status=0
systemd-analyze verify \
    "$work/repeated-space.service" \
    "$work/continued-space.service" \
    "$work/colon-control.service" \
    >"$out/stdout.txt" 2>"$out/stderr.txt" || status=$?

{
    printf 'status=%d\n' "$status"
    sha256sum "$out/stdout.txt" "$out/stderr.txt"
} >"$out/result.txt"

cp "$work"/*.service "$out/"
cat "$out/identity.txt"
cat "$out/result.txt"
cat "$out/stderr.txt"
