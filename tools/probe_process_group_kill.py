#!/usr/bin/env python3
"""Characterize process-group SIGINT delivery across kill spellings."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from typing import Callable, Sequence


READY_TIMEOUT_SECONDS = 5.0
SIGNAL_TIMEOUT_SECONDS = 3.0
CLEANUP_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class CaseResult:
    name: str
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    parent_signal: int | None
    child_signal: int | None
    unrelated_signal: int | None
    parent_running: bool
    child_running: bool
    unrelated_running: bool
    classification: str


class ProbeError(RuntimeError):
    """Raised when the topology fixture cannot be established or cleaned."""


def process_running(pid: int) -> bool:
    """Return true only for a live, non-zombie Linux process."""

    stat_path = pathlib.Path(f"/proc/{pid}/stat")
    try:
        fields = stat_path.read_text(encoding="utf-8").split()
    except FileNotFoundError:
        return False
    except OSError:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    return len(fields) >= 3 and fields[2] != "Z"


def wait_for_path(path: pathlib.Path, timeout: float = READY_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.02)
    raise ProbeError(f"timed out waiting for fixture path: {path}")


def wait_for_process_exit(pid: int, timeout: float = CLEANUP_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_running(pid):
            return
        time.sleep(0.02)
    raise ProbeError(f"process survived cleanup: pid={pid}")


def read_signal(
    path: pathlib.Path,
    timeout: float = SIGNAL_TIMEOUT_SECONDS,
) -> int | None:
    """Read a marker after its create-before-write publication race settles."""

    deadline = time.monotonic() + timeout
    while True:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        if value:
            try:
                return int(value)
            except ValueError as error:
                if time.monotonic() >= deadline:
                    raise ProbeError(f"invalid signal marker {path}: {value!r}") from error
        if time.monotonic() >= deadline:
            raise ProbeError(f"empty signal marker did not settle: {path}")
        time.sleep(0.01)


def wait_for_signal_settle(
    parent_pid: int,
    child_pid: int,
    parent_signal_path: pathlib.Path,
    child_signal_path: pathlib.Path,
) -> None:
    """Wait until each group member has either recorded SIGINT or exited."""

    deadline = time.monotonic() + SIGNAL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        parent_done = parent_signal_path.exists() or not process_running(parent_pid)
        child_done = child_signal_path.exists() or not process_running(child_pid)
        if parent_done and child_done:
            return
        time.sleep(0.02)


def settle_observed_exit(
    *,
    pid: int,
    signal_path: pathlib.Path,
    owner: subprocess.Popen[str] | None = None,
) -> None:
    """Wait past marker publication and reap a directly owned process.

    Signal handlers publish their marker before the short exit path completes.
    A marker therefore proves delivery, while liveness must be sampled only
    after the observed process exits. Direct children are explicitly reaped so
    a zombie never becomes fixture evidence.
    """

    if not signal_path.exists():
        return
    wait_for_process_exit(pid)
    if owner is not None:
        try:
            owner.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            raise ProbeError(f"signaled owner was not reaped: pid={pid}") from error


def worker_program() -> str:
    return r'''
import os
import pathlib
import signal
import subprocess
import sys
import time

root = pathlib.Path(sys.argv[1])
child_code = r"""
import pathlib
import signal
import sys
import time

root = pathlib.Path(sys.argv[1])
def handle(signum, frame):
    root.joinpath('child.signal').write_text(str(signum), encoding='utf-8')
    raise SystemExit(128 + signum)
signal.signal(signal.SIGINT, handle)
root.joinpath('child.ready').write_text(str(__import__('os').getpid()), encoding='utf-8')
while True:
    time.sleep(1)
"""
child = subprocess.Popen([sys.executable, '-c', child_code, str(root)])

def handle(signum, frame):
    root.joinpath('parent.signal').write_text(str(signum), encoding='utf-8')
    time.sleep(0.05)
    raise SystemExit(128 + signum)

signal.signal(signal.SIGINT, handle)
root.joinpath('parent.ready').write_text(
    f"{os.getpid()} {os.getpgrp()} {child.pid}",
    encoding='utf-8',
)
while True:
    time.sleep(1)
'''


def unrelated_program() -> str:
    return r'''
import pathlib
import signal
import sys
import time

root = pathlib.Path(sys.argv[1])
def handle(signum, frame):
    root.joinpath('unrelated.signal').write_text(str(signum), encoding='utf-8')
signal.signal(signal.SIGINT, handle)
root.joinpath('unrelated.ready').write_text(str(__import__('os').getpid()), encoding='utf-8')
while True:
    time.sleep(1)
'''


def classify(
    *,
    parent_signal: int | None,
    child_signal: int | None,
    unrelated_signal: int | None,
    returncode: int,
    stderr: str,
) -> str:
    if parent_signal == signal.SIGINT and child_signal == signal.SIGINT:
        if unrelated_signal is None:
            return "whole-group-delivery"
        return "overbroad-delivery"
    if parent_signal == signal.SIGINT and child_signal is None:
        return "owner-only-delivery"
    if parent_signal is None and child_signal is None:
        if "usage:" in stderr.lower() or returncode != 0:
            return "parser-or-target-rejection"
        return "no-delivery"
    return "partial-or-unexpected-delivery"


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        process.wait(timeout=0)
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def cleanup_group(parent: subprocess.Popen[str], child_pid: int | None) -> None:
    try:
        os.killpg(parent.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    try:
        parent.wait(timeout=2)
    except subprocess.TimeoutExpired:
        parent.kill()
        parent.wait(timeout=2)

    if child_pid is not None:
        wait_for_process_exit(child_pid)


def run_case(
    name: str,
    command_builder: Callable[[int, int], Sequence[str]] | None,
    *,
    python_group_control: bool = False,
) -> CaseResult:
    with tempfile.TemporaryDirectory(prefix=f"lf-kill-{name}-") as temporary:
        root = pathlib.Path(temporary)
        parent = subprocess.Popen(
            [sys.executable, "-c", worker_program(), str(root)],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        unrelated = subprocess.Popen(
            [sys.executable, "-c", unrelated_program(), str(root)],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        child_pid_for_cleanup: int | None = None
        try:
            wait_for_path(root / "parent.ready")
            wait_for_path(root / "child.ready")
            wait_for_path(root / "unrelated.ready")
            ready = (root / "parent.ready").read_text(encoding="utf-8").split()
            if len(ready) != 3:
                raise ProbeError(f"invalid parent readiness record: {ready}")
            parent_pid, pgid, child_pid = map(int, ready)
            child_pid_for_cleanup = child_pid
            unrelated_pid = int(
                (root / "unrelated.ready").read_text(encoding="utf-8").strip()
            )
            if parent_pid != parent.pid or pgid != parent.pid:
                raise ProbeError(
                    f"fixture is not an isolated process group: "
                    f"parent={parent.pid}, record={ready}"
                )
            if unrelated_pid != unrelated.pid:
                raise ProbeError("unrelated fixture PID mismatch")

            if python_group_control:
                command = ("python:os.killpg", str(pgid), "SIGINT")
                os.killpg(pgid, signal.SIGINT)
                returncode = 0
                stdout = ""
                stderr = ""
            else:
                if command_builder is None:
                    raise ProbeError("missing command builder")
                command = tuple(command_builder(parent_pid, pgid))
                completed = subprocess.run(
                    command,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
                returncode = completed.returncode
                stdout = completed.stdout
                stderr = completed.stderr

            parent_signal_path = root / "parent.signal"
            child_signal_path = root / "child.signal"
            wait_for_signal_settle(
                parent_pid,
                child_pid,
                parent_signal_path,
                child_signal_path,
            )
            parent_signal_value = read_signal(parent_signal_path)
            child_signal_value = read_signal(child_signal_path)
            unrelated_signal_value = read_signal(root / "unrelated.signal")

            settle_observed_exit(
                pid=parent_pid,
                signal_path=parent_signal_path,
                owner=parent,
            )
            settle_observed_exit(
                pid=child_pid,
                signal_path=child_signal_path,
            )

            return CaseResult(
                name=name,
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                parent_signal=parent_signal_value,
                child_signal=child_signal_value,
                unrelated_signal=unrelated_signal_value,
                parent_running=process_running(parent_pid),
                child_running=process_running(child_pid),
                unrelated_running=process_running(unrelated_pid),
                classification=classify(
                    parent_signal=parent_signal_value,
                    child_signal=child_signal_value,
                    unrelated_signal=unrelated_signal_value,
                    returncode=returncode,
                    stderr=stderr,
                ),
            )
        finally:
            cleanup_error: Exception | None = None
            try:
                cleanup_group(parent, child_pid_for_cleanup)
            except Exception as error:  # preserve cleanup authority after all cases
                cleanup_error = error
            terminate_process(unrelated)
            if cleanup_error is not None:
                raise cleanup_error


def command_cases() -> tuple[
    tuple[str, Callable[[int, int], Sequence[str]]], ...
]:
    return (
        (
            "owner-only-external",
            lambda parent, pgid: (
                "/bin/kill",
                "--signal",
                "INT",
                str(parent),
            ),
        ),
        (
            "external-long",
            lambda parent, pgid: (
                "/bin/kill",
                "--signal",
                "INT",
                "--",
                f"-{pgid}",
            ),
        ),
        (
            "external-short",
            lambda parent, pgid: (
                "/bin/kill",
                "-s",
                "INT",
                "--",
                f"-{pgid}",
            ),
        ),
        (
            "external-compact",
            lambda parent, pgid: (
                "/bin/kill",
                "-INT",
                "--",
                f"-{pgid}",
            ),
        ),
        (
            "dash-builtin-short",
            lambda parent, pgid: (
                "/bin/dash",
                "-c",
                'kill -s INT -- "$1"',
                "dash",
                f"-{pgid}",
            ),
        ),
    )


def version_output(command: Sequence[str]) -> str:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    return (completed.stdout + completed.stderr).strip()


def run_probe() -> dict[str, object]:
    results = [run_case(name, builder) for name, builder in command_cases()]
    results.append(
        run_case(
            "python-killpg-control",
            None,
            python_group_control=True,
        )
    )
    by_name = {result.name: result for result in results}

    owner = by_name["owner-only-external"]
    if owner.classification != "owner-only-delivery":
        raise ProbeError(f"owner-only negative control failed: {owner}")
    if not owner.child_running or not owner.unrelated_running:
        raise ProbeError(f"owner-only topology control was not preserved: {owner}")

    positive = by_name["python-killpg-control"]
    if positive.classification != "whole-group-delivery":
        raise ProbeError(f"Python killpg positive control failed: {positive}")
    if positive.parent_running or positive.child_running:
        raise ProbeError(f"Python killpg left group members running: {positive}")
    if not positive.unrelated_running:
        raise ProbeError(f"Python killpg terminated unrelated process: {positive}")

    candidate_priority = (
        "dash-builtin-short",
        "external-short",
        "external-compact",
        "external-long",
    )
    selected = next(
        (
            name
            for name in candidate_priority
            if by_name[name].classification == "whole-group-delivery"
            and not by_name[name].parent_running
            and not by_name[name].child_running
            and by_name[name].unrelated_running
        ),
        None,
    )
    if selected is None:
        raise ProbeError("no tested kill spelling delivered SIGINT to the whole group")

    return {
        "schema_version": 1,
        "kill_version": version_output(("/bin/kill", "--version")),
        "dash_version": version_output(("/bin/dash", "-c", "echo dash=$0")),
        "selected_candidate": selected,
        "results": [asdict(result) for result in results],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run disposable process-group SIGINT controls against external kill "
            "and dash builtin spellings."
        )
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="optional JSON output path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        record = run_probe()
        encoded = json.dumps(record, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            args.output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
    except (
        OSError,
        ProbeError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"process-group kill probe failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
