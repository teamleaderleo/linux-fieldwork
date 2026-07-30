#!/usr/bin/env bash
# Execute the LF-02 matrix from a validated disposable directory and preserve signals.
set -euo pipefail

fail() {
    printf 'LF-02 guarded runner: %s\n' "$*" >&2
    exit 2
}

need() {
    command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

for command in git mktemp python3 setsid; do
    need "$command"
done

repo_root="$(git rev-parse --show-toplevel)"
investigation_dir="$repo_root/investigations/lf-02-upgrade-failure-recovery"
implementation="$investigation_dir/run.sh"
test_mode="${LF02_GUARDED_TEST_MODE:-0}"
result_dir="$investigation_dir/results"
if [[ "$test_mode" == 1 && -n "${LF02_GUARDED_RESULT_DIR:-}" ]]; then
    result_dir="$LF02_GUARDED_RESULT_DIR"
fi

python3 - "$repo_root" "$investigation_dir" "$result_dir" "$implementation" <<'PY'
import os
import pathlib
import stat
import sys

repo, investigation, result, implementation = map(pathlib.Path, sys.argv[1:])


def reject_symlink_components(path: pathlib.Path, *, allow_missing_leaf: bool) -> None:
    absolute = path.absolute()
    current = pathlib.Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for index, part in enumerate(parts):
        current /= part
        is_leaf = index == len(parts) - 1
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            if allow_missing_leaf and is_leaf:
                return
            raise SystemExit(f"missing path component: {current}")
        if stat.S_ISLNK(mode):
            raise SystemExit(f"symlinked path component: {current}")


reject_symlink_components(repo, allow_missing_leaf=False)
reject_symlink_components(investigation, allow_missing_leaf=False)
reject_symlink_components(implementation, allow_missing_leaf=False)
reject_symlink_components(result, allow_missing_leaf=True)
repo_resolved = repo.resolve(strict=True)
investigation_resolved = investigation.resolve(strict=True)
expected_investigation = repo_resolved / "investigations/lf-02-upgrade-failure-recovery"
if investigation_resolved != expected_investigation:
    raise SystemExit(
        f"investigation directory escaped repository: {investigation_resolved}"
    )
if result.parent.resolve(strict=True) != investigation_resolved:
    raise SystemExit(f"result directory escaped investigation: {result}")
if result.name != "results":
    raise SystemExit(f"unexpected result directory name: {result.name}")
if not implementation.is_file():
    raise SystemExit(f"missing implementation: {implementation}")
PY

approved_tmp="$(python3 - "${TMPDIR:-/tmp}" <<'PY'
import pathlib
import stat
import sys

path = pathlib.Path(sys.argv[1])
if not path.is_absolute():
    raise SystemExit("temporary root must be absolute")
current = pathlib.Path(path.anchor)
for part in path.parts[1:]:
    current /= part
    mode = current.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise SystemExit(f"symlinked temporary-root component: {current}")
resolved = path.resolve(strict=True)
allowed = (pathlib.Path("/tmp"), pathlib.Path("/var/tmp"))
if not any(resolved == root or resolved.is_relative_to(root) for root in allowed):
    raise SystemExit(f"temporary root is outside approved roots: {resolved}")
print(resolved)
PY
)" || fail "temporary-root validation failed"

sandbox="$(mktemp -d -- "$approved_tmp/lf-02-upgrade-failure-recovery.XXXXXXXX")"
active_pgid=""
cleanup_started=0

cleanup() {
    local status=$?
    if [[ $cleanup_started -eq 1 ]]; then
        return "$status"
    fi
    cleanup_started=1
    if [[ -n "$sandbox" && -d "$sandbox" && ! -L "$sandbox" ]]; then
        python3 - "$sandbox" "$approved_tmp" <<'PY'
import pathlib
import sys

sandbox = pathlib.Path(sys.argv[1]).resolve(strict=True)
approved = pathlib.Path(sys.argv[2]).resolve(strict=True)
if sandbox.parent != approved:
    raise SystemExit(f"sandbox parent changed: {sandbox.parent}")
if not sandbox.name.startswith("lf-02-upgrade-failure-recovery."):
    raise SystemExit(f"unexpected sandbox name: {sandbox.name}")
PY
        rm -rf -- "$sandbox"
    fi
    return "$status"
}

forward_and_exit() {
    local signal_name=$1
    local exit_status=$2
    trap - INT TERM
    if [[ -n "$active_pgid" ]]; then
        kill -s "$signal_name" -- "-$active_pgid" 2>/dev/null || true
        for _ in $(seq 1 20); do
            if ! kill -0 -- "-$active_pgid" 2>/dev/null; then
                break
            fi
            sleep 0.05
        done
        if kill -0 -- "-$active_pgid" 2>/dev/null; then
            kill -KILL -- "-$active_pgid" 2>/dev/null || true
        fi
        wait "$active_pgid" 2>/dev/null || true
        active_pgid=""
    fi
    exit "$exit_status"
}

trap cleanup EXIT
trap 'forward_and_exit INT 130' INT
trap 'forward_and_exit TERM 143' TERM

export RUNNER_TEMP="$sandbox"
if [[ "$test_mode" == 1 ]]; then
    [[ $# -gt 0 ]] || fail "test mode requires a command"
    command=("$@")
else
    [[ $# -eq 0 ]] || fail "production mode accepts no command arguments"
    command=(bash "$implementation")
fi

setsid "${command[@]}" &
active_pgid=$!
set +e
wait "$active_pgid"
status=$?
set -e
active_pgid=""
exit "$status"
