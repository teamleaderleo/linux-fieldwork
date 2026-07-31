from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


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
parser.add_argument("--root", type=pathlib.Path, required=True)
parser.add_argument("--restore-before-final", action="store_true")
args = parser.parse_args()

proc = subprocess.Popen(
    [sys.executable, str(args.root / "wrapper.py"), str(args.root)],
    start_new_session=True,
)
(args.root / "backend.pgid").write_text(str(proc.pid), encoding="ascii")
(args.root / "driver.ready").write_text("ready\n", encoding="ascii")

try:
    proc.wait()
except KeyboardInterrupt:
    previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

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

        (args.root / "finalizing").write_text("yes\n", encoding="ascii")
        if args.restore_before_final:
            signal.signal(signal.SIGINT, previous_sigint)
        while not (args.root / "final-release").exists():
            time.sleep(0.01)
        (args.root / "driver.done").write_text("130\n", encoding="ascii")
        raise SystemExit(130)
    finally:
        if not args.restore_before_final:
            # The process exits immediately after publication. Keeping SIGINT ignored
            # through that exit is the policy under test.
            pass
'''

WRAPPER = r'''
import os
import pathlib
import signal
import subprocess
import sys
import time


root = pathlib.Path(sys.argv[1])


def on_term(_signal, _frame):
    (root / "wrapper.term").write_text("term\n", encoding="ascii")


signal.signal(signal.SIGTERM, on_term)
subprocess.Popen([sys.executable, str(root / "descendant.py"), str(root)])
(root / "wrapper.ready").write_text("ready\n", encoding="ascii")
while True:
    time.sleep(0.05)
'''

DESCENDANT = r'''
import pathlib
import signal
import sys
import time


root = pathlib.Path(sys.argv[1])


def on_term(_signal, _frame):
    (root / "descendant.term").write_text("term\n", encoding="ascii")


signal.signal(signal.SIGTERM, on_term)
(root / "descendant.ready").write_text("ready\n", encoding="ascii")
while True:
    time.sleep(0.05)
'''


@unittest.skipUnless(
    pathlib.Path("/proc").is_dir() and hasattr(os, "killpg"),
    "requires Linux /proc and POSIX process groups",
)
class CoverageFinalSigintContainmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="coverage-final-sigint-containment-"
        )
        self.root = pathlib.Path(self.temporary.name)
        for name, content in (
            ("driver.py", DRIVER),
            ("wrapper.py", WRAPPER),
            ("descendant.py", DESCENDANT),
        ):
            (self.root / name).write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

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
    def live_group_members(pgid: int) -> list[int]:
        members: list[int] = []
        for entry in pathlib.Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                text = (entry / "stat").read_text(encoding="utf-8")
                right = text.rfind(")")
                fields = text[right + 2 :].split()
                if int(fields[2]) == pgid and fields[0] != "Z":
                    members.append(int(entry.name))
            except (
                FileNotFoundError,
                ProcessLookupError,
                PermissionError,
                ValueError,
            ):
                continue
        return sorted(members)

    @classmethod
    def stop_group(cls, pgid: int) -> None:
        if not cls.live_group_members(pgid):
            return
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if not cls.live_group_members(pgid):
                return
            time.sleep(0.01)

    @staticmethod
    def stop_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait(timeout=2)

    def start_case(
        self,
        label: str,
        *,
        restore_before_final: bool,
    ) -> tuple[pathlib.Path, subprocess.Popen[bytes], subprocess.Popen[bytes]]:
        case = self.root / label
        case.mkdir()
        for name in ("driver.py", "wrapper.py", "descendant.py"):
            (case / name).write_text(
                (self.root / name).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(300)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, unrelated)

        stdout = open(case / "driver.stdout", "wb")
        stderr = open(case / "driver.stderr", "wb")
        self.addCleanup(stdout.close)
        self.addCleanup(stderr.close)
        command = [
            sys.executable,
            str(case / "driver.py"),
            "--root",
            str(case),
        ]
        if restore_before_final:
            command.append("--restore-before-final")
        driver = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, driver)

        self.wait_for_file(case / "driver.ready", driver)
        self.wait_for_file(case / "wrapper.ready", driver)
        self.wait_for_file(case / "descendant.ready", driver)
        backend_pgid = int((case / "backend.pgid").read_text(encoding="ascii"))
        self.addCleanup(self.stop_group, backend_pgid)
        return case, driver, unrelated

    def drive_to_finalization(
        self,
        case: pathlib.Path,
        driver: subprocess.Popen[bytes],
    ) -> int:
        backend_pgid = int((case / "backend.pgid").read_text(encoding="ascii"))
        os.kill(driver.pid, signal.SIGINT)
        self.wait_for_file(case / "wrapper.term", driver)
        self.wait_for_file(case / "descendant.term", driver)

        # A later signal during bounded cleanup must not replace the first.
        os.kill(driver.pid, signal.SIGINT)
        self.wait_for_file(case / "finalizing", driver)
        self.assertTrue((case / "escalated").exists())
        self.assertFalse(self.live_group_members(backend_pgid))
        return backend_pgid

    def test_restored_handler_loses_final_result_to_third_sigint(self) -> None:
        case, driver, unrelated = self.start_case(
            "restore-before-final",
            restore_before_final=True,
        )
        self.drive_to_finalization(case, driver)
        self.assertIsNone(unrelated.poll())

        os.kill(driver.pid, signal.SIGINT)
        status = driver.wait(timeout=5)

        self.assertNotEqual(status, 0)
        self.assertFalse((case / "driver.done").exists())
        self.assertIn(
            "KeyboardInterrupt",
            (case / "driver.stderr").read_text(errors="replace"),
        )
        self.assertIsNone(unrelated.poll())

    def test_ignored_handler_survives_third_sigint_and_publishes_130(self) -> None:
        case, driver, unrelated = self.start_case(
            "ignore-through-final",
            restore_before_final=False,
        )
        self.drive_to_finalization(case, driver)
        self.assertIsNone(unrelated.poll())

        os.kill(driver.pid, signal.SIGINT)
        time.sleep(0.10)
        self.assertIsNone(driver.poll())
        self.assertIsNone(unrelated.poll())

        (case / "final-release").write_text("go\n", encoding="ascii")
        status = driver.wait(timeout=5)

        self.assertEqual(status, 130)
        self.assertEqual(
            (case / "driver.done").read_text(encoding="ascii"),
            "130\n",
        )
        self.assertIsNone(unrelated.poll())


if __name__ == "__main__":
    unittest.main()
