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


OUTPUT = "Install: 1\n"


class MmdebstrapProxysolverSignalStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/proxysolver"
        cls.status_patch = cls.repo / (
            "investigations/mmdebstrap-proxysolver-exit-status/"
            "0001-propagate-solver-status.patch"
        )
        cls.signal_patch = cls.repo / (
            "investigations/mmdebstrap-proxysolver-signal-status/"
            "0001-reraise-solver-signals.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="proxysolver-signal-")
        root = pathlib.Path(cls.work.name)

        cls.fake_solver = root / "fake-solver"
        cls.fake_solver.write_text(
            """#!/usr/bin/env python3
import os
import signal
import sys
import time

sys.stdin.read()
with open(os.environ["FAKE_SOLVER_PIDFILE"], "w", encoding="utf-8") as stream:
    stream.write(str(os.getpid()) + "\\n")
sys.stdout.write(os.environ["FAKE_SOLVER_OUTPUT"])
sys.stdout.flush()
mode = os.environ["FAKE_SOLVER_MODE"]
if mode == "exit":
    raise SystemExit(int(os.environ["FAKE_SOLVER_STATUS"]))
if mode == "term":
    # The wrapper-mask regression deliberately starts with SIGTERM blocked.
    # Unblock it in the solver so the child still terminates by signal while
    # the parent retains the inherited blocked mask.
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM})
    os.kill(os.getpid(), signal.SIGTERM)
    time.sleep(5)
    raise SystemExit(99)
raise SystemExit(98)
""",
            encoding="utf-8",
        )
        cls.fake_solver.chmod(0o755)

        cls.canonical_root = root / "canonical"
        cls.repaired_root = root / "repaired"
        cls.canonical = cls.canonical_root / "upstream/mmdebstrap/proxysolver"
        cls.repaired = cls.repaired_root / "upstream/mmdebstrap/proxysolver"
        for destination in (cls.canonical, cls.repaired):
            destination.parent.mkdir(parents=True)
            shutil.copy2(cls.source, destination)

        cls.apply_patch(cls.canonical_root, cls.status_patch)
        cls.apply_patch(cls.repaired_root, cls.status_patch)
        cls.apply_patch(cls.repaired_root, cls.signal_patch)

        solver_literal = '"/usr/lib/apt/solvers/apt"'
        replacement = repr(str(cls.fake_solver))
        for path in (cls.canonical, cls.repaired):
            text = path.read_text(encoding="utf-8")
            if text.count(solver_literal) != 2:
                cls.work.cleanup()
                raise AssertionError("unexpected solver path occurrence count")
            path.write_text(
                text.replace(solver_literal, replacement), encoding="utf-8"
            )
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if compiled.returncode != 0:
                cls.work.cleanup()
                raise AssertionError(compiled.stdout + compiled.stderr)

    @classmethod
    def apply_patch(cls, root: pathlib.Path, patch: pathlib.Path) -> None:
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def run_wrapper(
        self,
        script: pathlib.Path,
        label: str,
        mode: str,
        status: int = 0,
        *,
        block_term_in_wrapper: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], str, int]:
        root = pathlib.Path(self.work.name)
        dump = root / f"{label}.dump"
        pidfile = root / f"{label}.pid"
        env = os.environ.copy()
        env.update(
            {
                "APT_EDSP_DUMP_FILENAME": str(dump),
                "FAKE_SOLVER_MODE": mode,
                "FAKE_SOLVER_STATUS": str(status),
                "FAKE_SOLVER_OUTPUT": OUTPUT,
                "FAKE_SOLVER_PIDFILE": str(pidfile),
            }
        )
        command = [sys.executable, str(script)]
        if block_term_in_wrapper:
            launcher = (
                "import os, signal, sys; "
                "signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM}); "
                "os.execv(sys.executable, [sys.executable, sys.argv[1]])"
            )
            command = [sys.executable, "-c", launcher, str(script)]
        result = subprocess.run(
            command,
            input="Request: EDSP\n\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=10,
        )
        child_pid = int(pidfile.read_text().strip())
        return result, dump.read_text(encoding="utf-8"), child_pid

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def assert_child_reaped(self, pid: int) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and self.process_exists(pid):
            time.sleep(0.01)
        self.assertFalse(self.process_exists(pid))

    def test_canonical_negative_systemexit_wraps_but_repair_reraises_term(self) -> None:
        canonical, canonical_dump, canonical_pid = self.run_wrapper(
            self.canonical, "canonical-term", "term"
        )
        repaired, repaired_dump, repaired_pid = self.run_wrapper(
            self.repaired, "repaired-term", "term"
        )

        self.assertEqual(canonical.returncode, 256 - signal.SIGTERM)
        self.assertEqual(repaired.returncode, -signal.SIGTERM)
        for result, dump in (
            (canonical, canonical_dump),
            (repaired, repaired_dump),
        ):
            self.assertEqual(result.stdout, OUTPUT)
            self.assertEqual(dump, OUTPUT)
        self.assert_child_reaped(canonical_pid)
        self.assert_child_reaped(repaired_pid)

    def test_repair_unblocks_inherited_term_before_reraising(self) -> None:
        repaired, dump, child_pid = self.run_wrapper(
            self.repaired,
            "repaired-blocked-term",
            "term",
            block_term_in_wrapper=True,
        )

        self.assertEqual(repaired.returncode, -signal.SIGTERM, repaired.stderr)
        self.assertEqual(repaired.stdout, OUTPUT)
        self.assertEqual(dump, OUTPUT)
        self.assert_child_reaped(child_pid)

    def test_ordinary_success_and_failure_statuses_remain_unchanged(self) -> None:
        for status in (0, 7):
            for label, script in (
                ("canonical", self.canonical),
                ("repaired", self.repaired),
            ):
                result, dump, child_pid = self.run_wrapper(
                    script, f"{label}-exit-{status}", "exit", status
                )
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, OUTPUT)
                self.assertEqual(dump, OUTPUT)
                self.assert_child_reaped(child_pid)

    def test_repaired_source_restores_unblocks_and_signals_itself(self) -> None:
        canonical = self.canonical.read_text(encoding="utf-8")
        repaired = self.repaired.read_text(encoding="utf-8")
        self.assertNotIn("if returncode < 0", canonical)
        self.assertIn("if returncode < 0", repaired)
        self.assertIn("signal.signal(signum, signal.SIG_DFL)", repaired)
        self.assertIn(
            "signal.pthread_sigmask(signal.SIG_UNBLOCK, {signum})", repaired
        )
        self.assertIn("os.kill(os.getpid(), signum)", repaired)
        self.assertIn("raise SystemExit(returncode)", repaired)


if __name__ == "__main__":
    unittest.main()
