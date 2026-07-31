from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from typing import BinaryIO


ROOT = pathlib.Path(__file__).resolve().parents[1]
PREDECESSOR_PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-coverage-process-group"
    / "0001-own-backend-process-group.patch"
)

DRIVER = r'''
import argparse
import os
import pathlib
import signal
import subprocess
import sys
import time


def live_group_members(pgid):
    members = []
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            text = (entry / "stat").read_text(encoding="utf-8")
            right = text.rfind(")")
            fields = text[right + 2 :].split()
            if int(fields[2]) == pgid and fields[0] != "Z":
                members.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
    return members


def wait_group(pgid, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not live_group_members(pgid):
            return True
        time.sleep(0.01)
    return not live_group_members(pgid)


parser = argparse.ArgumentParser()
parser.add_argument("--policy", choices=("current", "ignore", "bounded", "escalate"))
parser.add_argument("--wrapper-mode", choices=("exit", "hold"))
parser.add_argument("--root", type=pathlib.Path)
args = parser.parse_args()

proc = subprocess.Popen(
    [sys.executable, str(args.root / "wrapper.py"), args.wrapper_mode, str(args.root)],
    start_new_session=True,
)
(args.root / "driver.pid").write_text(str(os.getpid()), encoding="ascii")
(args.root / "backend.pgid").write_text(str(proc.pid), encoding="ascii")

try:
    proc.wait()
except KeyboardInterrupt:
    previous_sigint = None
    if args.policy in ("ignore", "bounded", "escalate"):
        previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

        if args.policy in ("current", "ignore"):
            proc.wait()
        elif args.policy == "bounded":
            try:
                proc.wait(timeout=0.20)
            except subprocess.TimeoutExpired:
                (args.root / "wrapper-timeout").write_text("yes\n", encoding="ascii")
            wait_group(proc.pid, 0.20)
            survivors = live_group_members(proc.pid)
            if survivors:
                (args.root / "survivors").write_text(
                    ",".join(str(pid) for pid in survivors) + "\n",
                    encoding="ascii",
                )
        elif args.policy == "escalate":
            try:
                proc.wait(timeout=0.20)
            except subprocess.TimeoutExpired:
                pass
            if not wait_group(proc.pid, 0.20):
                (args.root / "escalated").write_text("yes\n", encoding="ascii")
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                wait_group(proc.pid, 1)
    finally:
        if previous_sigint is not None:
            signal.signal(signal.SIGINT, previous_sigint)

    (args.root / "driver.done").write_text("130\n", encoding="ascii")
    raise SystemExit(130)
'''

WRAPPER = r'''
import os
import pathlib
import signal
import subprocess
import sys
import time


mode = sys.argv[1]
root = pathlib.Path(sys.argv[2])


def on_term(_signal, _frame):
    (root / "wrapper.term").write_text("term\n", encoding="ascii")
    if mode == "exit":
        raise SystemExit(0)


signal.signal(signal.SIGTERM, on_term)
child = subprocess.Popen(
    [
        sys.executable,
        str(root / "descendant.py"),
        str(root),
        os.environ.get("ESCAPE_DESCENDANT", "no"),
    ],
    start_new_session=os.environ.get("ESCAPE_DESCENDANT") == "yes",
)
(root / "wrapper.pid").write_text(str(os.getpid()), encoding="ascii")
(root / "wrapper.pgid").write_text(str(os.getpgrp()), encoding="ascii")
(root / "wrapper.ready").write_text("ready\n", encoding="ascii")

while not (root / "release").exists():
    if child.poll() is not None:
        break
    time.sleep(0.01)

if (root / "release").exists():
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
(root / "wrapper.later").write_text("later\n", encoding="ascii")
'''

DESCENDANT = r'''
import os
import pathlib
import signal
import sys
import time


root = pathlib.Path(sys.argv[1])


def on_term(_signal, _frame):
    (root / "descendant.term").write_text("term\n", encoding="ascii")


signal.signal(signal.SIGTERM, on_term)
(root / "descendant.pid").write_text(str(os.getpid()), encoding="ascii")
(root / "descendant.pgid").write_text(str(os.getpgrp()), encoding="ascii")
(root / "descendant.sid").write_text(str(os.getsid(0)), encoding="ascii")
(root / "descendant.ready").write_text("ready\n", encoding="ascii")

while not (root / "release").exists():
    time.sleep(0.01)
(root / "descendant.later").write_text("later\n", encoding="ascii")
'''


@unittest.skipUnless(
    pathlib.Path("/proc").is_dir() and hasattr(os, "killpg"),
    "requires Linux /proc and POSIX process groups",
)
class CoverageTermResistantCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work = tempfile.TemporaryDirectory(
            prefix="coverage-term-resistant-cleanup-"
        )
        self.root = pathlib.Path(self.work.name)
        for name, content in (
            ("driver.py", DRIVER),
            ("wrapper.py", WRAPPER),
            ("descendant.py", DESCENDANT),
        ):
            (self.root / name).write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.work.cleanup()

    @staticmethod
    def wait_for_file(
        path: pathlib.Path,
        process: subprocess.Popen[bytes] | None = None,
        timeout: float = 5.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process is not None and process.poll() is not None:
                raise AssertionError(
                    f"process exited before {path.name}: {process.returncode}"
                )
            time.sleep(0.01)
        raise AssertionError(f"timed out waiting for {path}")

    @staticmethod
    def group_members(pgid: int) -> list[dict[str, int | str]]:
        members: list[dict[str, int | str]] = []
        for entry in pathlib.Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                text = (entry / "stat").read_text(encoding="utf-8")
                right = text.rfind(")")
                fields = text[right + 2 :].split()
                if int(fields[2]) != pgid:
                    continue
                members.append(
                    {
                        "pid": int(entry.name),
                        "state": fields[0],
                        "ppid": int(fields[1]),
                        "pgid": int(fields[2]),
                        "sid": int(fields[3]),
                    }
                )
            except (
                FileNotFoundError,
                ProcessLookupError,
                PermissionError,
                ValueError,
            ):
                continue
        return sorted(members, key=lambda item: int(item["pid"]))

    @classmethod
    def live_group_members(cls, pgid: int) -> list[dict[str, int | str]]:
        return [member for member in cls.group_members(pgid) if member["state"] != "Z"]

    @classmethod
    def terminate_group(cls, pgid: int) -> None:
        for group_signal in (signal.SIGTERM, signal.SIGKILL):
            if not cls.live_group_members(pgid):
                return
            try:
                os.killpg(pgid, group_signal)
            except ProcessLookupError:
                return
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if not cls.live_group_members(pgid):
                    return
                time.sleep(0.01)

    @staticmethod
    def stop_driver(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait(timeout=2)

    def start_driver(
        self,
        label: str,
        policy: str,
        wrapper_mode: str,
        *,
        escape_descendant: bool = False,
    ) -> tuple[pathlib.Path, subprocess.Popen[bytes], BinaryIO, BinaryIO]:
        case = self.root / label
        case.mkdir()
        for name in ("driver.py", "wrapper.py", "descendant.py"):
            shutil.copy2(self.root / name, case / name)

        stdout = open(case / "driver.stdout", "wb")
        stderr = open(case / "driver.stderr", "wb")
        environment = os.environ.copy()
        environment["ESCAPE_DESCENDANT"] = "yes" if escape_descendant else "no"
        process = subprocess.Popen(
            [
                sys.executable,
                str(case / "driver.py"),
                "--policy",
                policy,
                "--wrapper-mode",
                wrapper_mode,
                "--root",
                str(case),
            ],
            env=environment,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        self.addCleanup(stdout.close)
        self.addCleanup(stderr.close)
        self.addCleanup(self.stop_driver, process)
        self.wait_for_file(case / "descendant.ready", process)
        return case, process, stdout, stderr

    def identities(self, case: pathlib.Path) -> tuple[int, int, int]:
        backend_pgid = int((case / "backend.pgid").read_text(encoding="ascii"))
        descendant_pid = int(
            (case / "descendant.pid").read_text(encoding="ascii")
        )
        descendant_pgid = int(
            (case / "descendant.pgid").read_text(encoding="ascii")
        )
        self.addCleanup(self.terminate_group, backend_pgid)
        if descendant_pgid != backend_pgid:
            self.addCleanup(self.terminate_group, descendant_pgid)
        return backend_pgid, descendant_pid, descendant_pgid

    def signal_once(
        self,
        case: pathlib.Path,
        process: subprocess.Popen[bytes],
    ) -> None:
        os.kill(process.pid, signal.SIGINT)
        self.wait_for_file(case / "wrapper.term", process)
        self.wait_for_file(case / "descendant.term", process)

    @staticmethod
    def release(case: pathlib.Path) -> None:
        (case / "release").write_text("go\n", encoding="ascii")

    def test_current_policy_returns_130_while_term_resistant_descendant_survives(
        self,
    ) -> None:
        case, process, stdout, stderr = self.start_driver(
            "current-wrapper-exits", "current", "exit"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.signal_once(case, process)
        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()

        self.assertEqual(status, 130)
        live = self.live_group_members(backend_pgid)
        self.assertEqual(len(live), 1, live)
        self.assertEqual(live[0]["ppid"], 1)
        self.assertFalse((case / "descendant.later").exists())

        self.release(case)
        self.wait_for_file(case / "descendant.later")
        self.assertFalse(self.live_group_members(backend_pgid))

    def test_second_sigint_interrupts_current_cleanup_wait(self) -> None:
        case, process, stdout, stderr = self.start_driver(
            "current-second-sigint", "current", "hold"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.signal_once(case, process)
        self.assertIsNone(process.poll())

        os.kill(process.pid, signal.SIGINT)
        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()

        self.assertEqual(status, -int(signal.SIGINT))
        self.assertIn(
            "KeyboardInterrupt",
            (case / "driver.stderr").read_text(errors="replace"),
        )
        self.assertFalse((case / "driver.done").exists())
        self.assertGreaterEqual(len(self.live_group_members(backend_pgid)), 2)

    def test_ignoring_later_sigint_preserves_130_but_waits_for_release(
        self,
    ) -> None:
        case, process, stdout, stderr = self.start_driver(
            "ignore-second-sigint", "ignore", "hold"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.signal_once(case, process)
        os.kill(process.pid, signal.SIGINT)
        time.sleep(0.25)

        self.assertIsNone(process.poll())
        self.assertGreaterEqual(len(self.live_group_members(backend_pgid)), 2)

        self.release(case)
        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()

        self.assertEqual(status, 130)
        self.assertTrue((case / "descendant.later").exists())
        self.assertTrue((case / "wrapper.later").exists())
        self.assertFalse(self.live_group_members(backend_pgid))

    def test_bounded_diagnostic_returns_130_and_names_survivors(self) -> None:
        case, process, stdout, stderr = self.start_driver(
            "bounded-diagnostic", "bounded", "hold"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.signal_once(case, process)
        os.kill(process.pid, signal.SIGINT)

        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()
        self.assertEqual(status, 130)
        self.assertTrue((case / "wrapper-timeout").exists())
        survivors = (case / "survivors").read_text(encoding="ascii").strip()
        self.assertTrue(survivors)
        self.assertGreaterEqual(len(self.live_group_members(backend_pgid)), 2)

        self.release(case)
        self.wait_for_file(case / "descendant.later")
        self.wait_for_file(case / "wrapper.later")

    def test_bounded_escalation_stops_held_wrapper_and_descendant(self) -> None:
        case, process, stdout, stderr = self.start_driver(
            "escalate-held-wrapper", "escalate", "hold"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.signal_once(case, process)
        os.kill(process.pid, signal.SIGINT)

        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()
        self.assertEqual(status, 130)
        self.assertTrue((case / "escalated").exists())
        self.assertFalse(self.live_group_members(backend_pgid))
        self.assertFalse((case / "descendant.later").exists())
        self.assertFalse((case / "wrapper.later").exists())

    def test_bounded_escalation_drains_descendant_after_wrapper_exit(self) -> None:
        case, process, stdout, stderr = self.start_driver(
            "escalate-wrapper-exits", "escalate", "exit"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.signal_once(case, process)

        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()
        self.assertEqual(status, 130)
        self.assertTrue((case / "escalated").exists())
        self.assertFalse(self.live_group_members(backend_pgid))
        self.assertFalse((case / "descendant.later").exists())

    def test_unsignaled_current_model_completes_cleanly(self) -> None:
        case, process, stdout, stderr = self.start_driver(
            "ordinary-success", "current", "hold"
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)
        self.release(case)

        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()
        self.assertEqual(status, 0)
        self.assertTrue((case / "descendant.later").exists())
        self.assertTrue((case / "wrapper.later").exists())
        self.assertFalse(self.live_group_members(backend_pgid))

    def test_session_escape_remains_outside_group_delivery(self) -> None:
        case, process, stdout, stderr = self.start_driver(
            "escaped-descendant",
            "current",
            "exit",
            escape_descendant=True,
        )
        backend_pgid, _descendant_pid, descendant_pgid = self.identities(case)
        self.assertNotEqual(descendant_pgid, backend_pgid)

        os.kill(process.pid, signal.SIGINT)
        self.wait_for_file(case / "wrapper.term", process)
        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()

        self.assertEqual(status, 130)
        self.assertFalse((case / "descendant.term").exists())
        self.assertTrue(self.live_group_members(descendant_pgid))
        self.release(case)
        self.wait_for_file(case / "descendant.later")

    def test_predecessor_source_has_unbounded_second_wait(self) -> None:
        patch = PREDECESSOR_PATCH.read_text(encoding="utf-8")
        self.assertIn(
            "subprocess.Popen(argv, start_new_session=True)",
            patch,
        )
        kill_index = patch.index(
            "+                os.killpg(proc.pid, signal.SIGTERM)"
        )
        wait_index = patch.index("\n             proc.wait()\n", kill_index)
        exit_index = patch.index(
            '+            raise SystemExit(130)', wait_index
        )
        self.assertLess(kill_index, wait_index)
        self.assertLess(wait_index, exit_index)
        self.assertNotIn("signal.SIG_IGN", patch)
        self.assertNotIn("timeout=", patch)
        self.assertNotIn("signal.SIGKILL", patch)


if __name__ == "__main__":
    unittest.main()
