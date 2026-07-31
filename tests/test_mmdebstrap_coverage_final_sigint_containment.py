from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from tests import test_mmdebstrap_coverage_term_resistant_cleanup as matrix


FINALIZER = r'''
import argparse
import pathlib
import signal
import time


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=pathlib.Path, required=True)
parser.add_argument("--restore-before-final", action="store_true")
args = parser.parse_args()

previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
(args.root / "finalizing").write_text("yes\n", encoding="ascii")
if args.restore_before_final:
    signal.signal(signal.SIGINT, previous_sigint)
(args.root / "handler-ready").write_text("yes\n", encoding="ascii")

while not (args.root / "final-release").exists():
    time.sleep(0.01)

(args.root / "driver.done").write_text("130\n", encoding="ascii")
raise SystemExit(130)
'''


@unittest.skipUnless(
    pathlib.Path("/proc").is_dir() and hasattr(os, "killpg"),
    "requires Linux /proc and POSIX process groups",
)
class CoverageFinalSigintContainmentTest(unittest.TestCase):
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
    def stop_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait(timeout=2)

    def start_finalizer(
        self,
        root: pathlib.Path,
        *,
        restore_before_final: bool,
    ) -> subprocess.Popen[bytes]:
        script = root / "finalizer.py"
        script.write_text(FINALIZER, encoding="utf-8")
        command = [
            sys.executable,
            str(script),
            "--root",
            str(root),
        ]
        if restore_before_final:
            command.append("--restore-before-final")
        stdout = open(root / "finalizer.stdout", "wb")
        stderr = open(root / "finalizer.stderr", "wb")
        self.addCleanup(stdout.close)
        self.addCleanup(stderr.close)
        process = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, process)
        self.wait_for_file(root / "handler-ready", process)
        return process

    def test_predecessor_source_restores_sigint_before_result_publication(self) -> None:
        restore = matrix.DRIVER.index(
            "signal.signal(signal.SIGINT, previous_sigint)"
        )
        publication = matrix.DRIVER.index(
            '(args.root / "driver.done").write_text("130\\n", encoding="ascii")'
        )
        final_exit = matrix.DRIVER.index("raise SystemExit(130)", publication)
        self.assertLess(restore, publication)
        self.assertLess(publication, final_exit)

    def test_restored_handler_loses_final_publication_to_third_sigint(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="coverage-final-sigint-restored-"
        ) as temporary:
            root = pathlib.Path(temporary)
            process = self.start_finalizer(
                root,
                restore_before_final=True,
            )
            os.kill(process.pid, signal.SIGINT)
            status = process.wait(timeout=5)

            self.assertNotEqual(status, 0)
            self.assertFalse((root / "driver.done").exists())
            self.assertIn(
                "KeyboardInterrupt",
                (root / "finalizer.stderr").read_text(errors="replace"),
            )

    def test_ignored_handler_survives_third_sigint_and_publishes_130(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="coverage-final-sigint-ignored-"
        ) as temporary:
            root = pathlib.Path(temporary)
            process = self.start_finalizer(
                root,
                restore_before_final=False,
            )
            os.kill(process.pid, signal.SIGINT)
            time.sleep(0.10)
            self.assertIsNone(process.poll())

            (root / "final-release").write_text("go\n", encoding="ascii")
            status = process.wait(timeout=5)

            self.assertEqual(status, 130)
            self.assertEqual(
                (root / "driver.done").read_text(encoding="ascii"),
                "130\n",
            )

    def test_escalation_drains_backend_without_touching_unrelated_process(
        self,
    ) -> None:
        helper = matrix.CoverageTermResistantCleanupTest(methodName="runTest")
        helper.setUp()
        self.addCleanup(helper.tearDown)
        self.addCleanup(helper.doCleanups)

        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(300)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.addCleanup(helper.stop_driver, unrelated)

        case, process, stdout, stderr = helper.start_driver(
            "escalation-unrelated",
            "escalate",
            "hold",
        )
        backend_pgid, _descendant_pid, descendant_pgid = helper.identities(case)
        self.assertEqual(descendant_pgid, backend_pgid)

        helper.signal_once(case, process)
        os.kill(process.pid, signal.SIGINT)
        status = process.wait(timeout=5)
        stdout.close()
        stderr.close()

        self.assertEqual(status, 130)
        self.assertTrue((case / "escalated").exists())
        self.assertFalse(helper.live_group_members(backend_pgid))
        self.assertFalse((case / "descendant.later").exists())
        self.assertFalse((case / "wrapper.later").exists())
        self.assertIsNone(unrelated.poll())


if __name__ == "__main__":
    unittest.main()
