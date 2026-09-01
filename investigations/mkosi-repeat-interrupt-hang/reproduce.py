#!/usr/bin/env python3
"""Reduced reproducer for mkosi repeated-interrupt wait behavior.

Models the current control-flow interaction at upstream commit
f7401bdc8d23486bb346790dc92508381a062f3b:

* mkosi/__main__.py: onsignal() records a process-global one-shot
  INTERRUPTED latch and returns for later SIGINT/SIGTERM/SIGHUP delivery.
* mkosi/run.py: spawn() and fork_and_wait() forward the first SIGINT and
  then enter another blocking wait.

The fixture uses only Python's standard library and never touches mounts,
packages, namespaces, or external systems.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time

INTERRUPTED = False


def onsignal(signum: int, frame: object) -> None:
    global INTERRUPTED
    if INTERRUPTED:
        return
    INTERRUPTED = True
    raise KeyboardInterrupt()


def install_handlers() -> None:
    signal.signal(signal.SIGINT, onsignal)
    signal.signal(signal.SIGTERM, onsignal)
    signal.signal(signal.SIGHUP, onsignal)


def wait_child_spawn(mode: str) -> int:
    install_handlers()
    child_code = [
        "import os,signal,time",
        "print(f'child={os.getpid()}', flush=True)",
    ]
    if mode == "ignore":
        child_code.insert(
            1,
            "signal.signal(signal.SIGINT, signal.SIG_IGN); signal.signal(signal.SIGTERM, signal.SIG_IGN)",
        )

    child = subprocess.Popen(
        [sys.executable, "-c", "; ".join(child_code) + "; time.sleep(120)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert child.stdout is not None
    print(f"parent={os.getpid()} {child.stdout.readline().strip()}", flush=True)

    try:
        child.wait()
    except KeyboardInterrupt:
        child.send_signal(signal.SIGINT)
        raise
    finally:
        child.send_signal(signal.SIGCONT)
        child.wait()

    return 0


def wait_child_fork(mode: str) -> int:
    install_handlers()
    pid = os.fork()
    if pid == 0:
        if mode == "ignore":
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(120)
        os._exit(0)

    print(f"parent={os.getpid()} child={pid}", flush=True)
    try:
        _, status = os.waitpid(pid, 0)
    except KeyboardInterrupt:
        os.kill(pid, signal.SIGINT)
        _, status = os.waitpid(pid, 0)
    except BaseException:
        os.kill(pid, signal.SIGTERM)
        _, status = os.waitpid(pid, 0)

    return os.waitstatus_to_exitcode(status)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def drive(kind: str, mode: str) -> list[tuple[str, bool, bool]]:
    proc = subprocess.Popen(
        [sys.executable, __file__, "--parent-kind", kind, "--child-mode", mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert proc.stdout is not None
    first = proc.stdout.readline().strip()
    match = re.fullmatch(r"parent=(\d+) child=(\d+)", first)
    if match is None:
        raise RuntimeError(f"unexpected parent banner: {first!r}")
    parent_pid, child_pid = map(int, match.groups())

    sequence = [(signal.SIGINT, "SIGINT#1")]
    if mode == "ignore":
        sequence += [(signal.SIGINT, "SIGINT#2"), (signal.SIGTERM, "SIGTERM#3")]

    observations: list[tuple[str, bool, bool]] = []
    try:
        for sig, label in sequence:
            os.kill(parent_pid, sig)
            if mode == "default":
                deadline = time.monotonic() + 1.0
                while proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.05)
            else:
                time.sleep(0.25)
            observations.append((label, proc.poll() is None, alive(child_pid)))
    finally:
        if proc.poll() is None:
            os.kill(parent_pid, signal.SIGKILL)
        if alive(child_pid):
            os.kill(child_pid, signal.SIGKILL)
        proc.wait(timeout=2)

    return observations


def print_case(kind: str, mode: str) -> None:
    print(f"{kind} / {mode}")
    for label, parent_alive, child_alive in drive(kind, mode):
        print(f"{label}: parent_alive={parent_alive} child_alive={child_alive}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-kind", choices=("spawn", "fork"))
    parser.add_argument("--child-mode", choices=("default", "ignore"))
    args = parser.parse_args()

    if args.parent_kind:
        assert args.child_mode is not None
        try:
            if args.parent_kind == "spawn":
                return wait_child_spawn(args.child_mode)
            return wait_child_fork(args.child_mode)
        except KeyboardInterrupt:
            return 1

    for kind in ("spawn", "fork"):
        print_case(kind, "default")
        print_case(kind, "ignore")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
