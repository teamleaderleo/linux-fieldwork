#!/usr/bin/env python3
import argparse
import ctypes
import os
import subprocess
import sys
import time
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"This process .*fork.*")

PR_SET_CHILD_SUBREAPER = 36
libc = ctypes.CDLL(None, use_errno=True)


def set_subreaper():
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))


def proc_state(pid):
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as f:
            return f.read().split()[2]
    except FileNotFoundError:
        return None


def reap_children():
    reaped = []
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
        reaped.append((pid, status))
    return reaped


def adopted_children():
    me = os.getpid()
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            with open(f"/proc/{pid}/status", "r", encoding="utf-8") as f:
                fields = {}
                for line in f:
                    key, _, value = line.partition(":")
                    if key in {"Name", "State", "PPid"}:
                        fields[key] = value.strip()
            if int(fields.get("PPid", "-1")) == me:
                found.append((pid, fields.get("State", "?"), fields.get("Name", "?")))
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            pass
    return found


def wait_for_zombie(timeout):
    deadline = time.monotonic() + timeout
    children = []
    zombies = []
    while time.monotonic() < deadline:
        children = adopted_children()
        zombies = [row for row in children if row[1].startswith("Z")]
        if zombies:
            break
        time.sleep(0.01)
    return children, zombies


def run_model():
    set_subreaper()
    pid_r, pid_w = os.pipe()
    event_r, event_w = os.pipe()

    outer = os.fork()
    if outer == 0:
        os.close(pid_r)
        init_pid = os.fork()
        if init_pid == 0:
            os.close(pid_w)
            os.close(event_r)
            command = os.fork()
            if command == 0:
                os._exit(0)
            os.waitpid(command, 0)
            os.write(event_w, b"x")
            time.sleep(0.15)
            os._exit(0)

        os.write(pid_w, f"{init_pid}\n".encode())
        os.close(pid_w)
        os.close(event_w)
        os.read(event_r, 1)
        os._exit(0)

    os.close(pid_w)
    os.close(event_w)
    init_pid = int(os.read(pid_r, 64).strip())
    os.close(pid_r)
    os.close(event_r)
    os.waitpid(outer, 0)

    state = None
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        state = proc_state(init_pid)
        if state == "Z":
            break
        time.sleep(0.01)

    print(f"model: init_pid={init_pid} state_after_outer_exit={state}")
    try:
        os.waitpid(init_pid, 0)
    except ChildProcessError:
        pass

    return 0 if state == "Z" else 1


def run_short_cases(path, expect_short_clean=False):
    cases = [
        ("pid-helper", ["--unshare-pid"]),
        ("as-pid-1-control", ["--unshare-pid", "--as-pid-1"]),
        ("no-pidns-control", []),
    ]
    rc = 0

    for name, extra in cases:
        reap_children()
        cmd = [path, *extra, "--dev-bind", "/", "/", "--", "/bin/true"]
        completed = subprocess.run(cmd, check=False)
        children, zombies = wait_for_zombie(2.0 if name == "pid-helper" else 0.2)
        print(f"{name}: bwrap_rc={completed.returncode} adopted_children={children}")
        reap_children()

        if completed.returncode != 0:
            rc = 2
        elif name == "pid-helper" and expect_short_clean and zombies:
            rc = max(rc, 1)
        elif name == "pid-helper" and not expect_short_clean and not zombies:
            rc = max(rc, 1)
        elif name != "pid-helper" and zombies:
            rc = max(rc, 1)

    return rc


def run_background_case(path):
    reap_children()
    cmd = [
        path,
        "--unshare-pid",
        "--dev-bind", "/", "/",
        "--", "/bin/sh", "-c", "sleep 3 & exit 0",
    ]
    started = time.monotonic()
    completed = subprocess.run(cmd, check=False)
    elapsed = time.monotonic() - started
    immediate = adopted_children()
    live_helpers = [row for row in immediate if not row[1].startswith("Z") and row[2] == "bwrap"]
    final_children, final_zombies = wait_for_zombie(4.0)
    print(
        "background-child: "
        f"bwrap_rc={completed.returncode} elapsed={elapsed:.3f}s "
        f"immediate_adopted={immediate} final_adopted={final_children}"
    )
    reap_children()

    if completed.returncode != 0:
        return 2
    if elapsed >= 1.5:
        return 1
    if not live_helpers:
        return 1
    if not final_zombies:
        return 1
    return 0


def run_bwrap(path, expect_short_clean=False):
    set_subreaper()
    rc = run_short_cases(path, expect_short_clean=expect_short_clean)
    rc = max(rc, run_background_case(path))
    return rc


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model", action="store_true")
    group.add_argument("--bwrap", metavar="PATH")
    parser.add_argument("--expect-short-clean", action="store_true")
    args = parser.parse_args()

    if args.model:
        return run_model()
    return run_bwrap(args.bwrap, expect_short_clean=args.expect_short_clean)


if __name__ == "__main__":
    sys.exit(main())
