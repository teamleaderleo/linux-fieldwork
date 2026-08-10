#!/bin/sh
# Disposable reproduction for systemd-tmpfiles Unix-socket liveness across
# network namespaces. Evidence helper only; this is not an upstream candidate.
set -eu

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "missing command: $1" >&2
        exit 77
    }
}

need python3
need systemd-tmpfiles
need unshare

base="/tmp/lf-tmpfiles-cross-netns.$$"
config="/tmp/lf-tmpfiles-cross-netns.$$.conf"
listener="/tmp/lf-tmpfiles-cross-netns.$$.py"
pids=""

cleanup() {
    for p in $pids; do
        kill "$p" 2>/dev/null || true
    done
    for p in $pids; do
        wait "$p" 2>/dev/null || true
    done
    rm -rf "$base" "$config" "$listener"
}
trap cleanup EXIT HUP INT TERM

cat >"$listener" <<'PY'
import os
import socket
import sys
import time

path = sys.argv[1]
try:
    os.unlink(path)
except FileNotFoundError:
    pass

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(path)
s.listen(1)
print(os.getpid(), flush=True)
while True:
    time.sleep(60)
PY

mkdir -m 0777 "$base"
printf 'D %s 0777 root root 1s\n' "$base" >"$config"

python3 "$listener" "$base/same" >"$base/same.pid" 2>"$base/same.err" &
same_pid=$!
pids="$pids $same_pid"

unshare -Urn python3 "$listener" "$base/foreign" >"$base/foreign.pid" 2>"$base/foreign.err" &
foreign_pid=$!
pids="$pids $foreign_pid"

python3 "$listener" "$base/dead" >"$base/dead.pid" 2>"$base/dead.err" &
dead_pid=$!

n=0
while [ "$n" -lt 100 ]; do
    [ -S "$base/same" ] && [ -S "$base/foreign" ] && [ -S "$base/dead" ] && break
    n=$((n + 1))
    sleep 0.02
done

[ -S "$base/same" ] && [ -S "$base/foreign" ] && [ -S "$base/dead" ] || {
    echo "listener setup failed" >&2
    exit 1
}

kill "$dead_pid"
wait "$dead_pid" 2>/dev/null || true

# Let all relevant timestamps cross the one-second cleanup cutoff.
sleep 2

for name in same foreign dead; do
    if grep -F "$base/$name" /proc/net/unix >/dev/null 2>&1; then
        visible=yes
    else
        visible=no
    fi
    echo "$name outer-proc-net-unix=$visible"
done

SYSTEMD_LOG_LEVEL=debug \
    systemd-tmpfiles --clean --prefix="$base" "$config" \
    >"$base/clean.out" 2>"$base/clean.err"

for name in same foreign dead; do
    if [ -S "$base/$name" ]; then
        state=present
    else
        state=absent
    fi
    echo "$name after-clean=$state"
done

printf '%s\n' '--- relevant tmpfiles log ---'
grep -E '(live socket|Removing|cross-netns)' "$base/clean.err" || true

# Current affected classifier:
#   same=present, foreign=absent, dead=absent
# A candidate that recognizes the foreign live socket should produce:
#   same=present, foreign=present, dead=absent
