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

OUTPUT = "Install: 1\nPackage: example\n"
STDERR = "solver diagnostic\n"
REQUEST = "Request: EDSP\n\n"


class ProxysolverResultPropagationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = pathlib.Path(__file__).resolve().parents[1]
        cls.repo = next(
            parent
            for parent in pathlib.Path(__file__).resolve().parents
            if (parent / "upstream/mmdebstrap/proxysolver").is_file()
        )
        cls.source = cls.repo / "upstream/mmdebstrap/proxysolver"
        cls.status_patch = cls.repo / (
            "investigations/mmdebstrap-proxysolver-exit-status/"
            "0001-propagate-solver-status.patch"
        )
        cls.combined_patch = (
            cls.packet
            / "patches/0001-proxysolver-propagate-solver-results.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="unit12-proxysolver-")
        root = pathlib.Path(cls.work.name)
        cls.fake_solver = root / "fake-solver.py"
        cls.fake_solver.write_text(
            """#!/usr/bin/env python3
import os
import signal
import sys
import time

sys.stdin.read()
with open(os.environ["FAKE_SOLVER_PIDFILE"], "w", encoding="utf-8") as stream:
    stream.write(f"{os.getpid()}\\n")
sys.stdout.write(os.environ["FAKE_SOLVER_OUTPUT"])
sys.stdout.flush()
sys.stderr.write(os.environ["FAKE_SOLVER_STDERR"])
sys.stderr.flush()
mode = os.environ["FAKE_SOLVER_MODE"]
if mode == "exit":
    raise SystemExit(int(os.environ["FAKE_SOLVER_STATUS"]))
if mode == "signal":
    signum = int(os.environ["FAKE_SOLVER_SIGNAL"])
    signal.signal(signum, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signum})
    os.kill(os.getpid(), signum)
    time.sleep(5)
raise SystemExit(98)
""",
            encoding="utf-8",
        )
        cls.fake_solver.chmod(0o755)

        cls.baseline = root / "baseline" / "proxysolver"
        cls.ordinary_root = root / "ordinary"
        cls.ordinary = cls.ordinary_root / "upstream/mmdebstrap/proxysolver"
        cls.candidate_root = root / "candidate"
        cls.candidate = cls.candidate_root / "proxysolver"
        for path in (cls.baseline, cls.ordinary, cls.candidate):
            path.parent.mkdir(parents=True)
            shutil.copy2(cls.source, path)

        cls.apply_patch(cls.ordinary_root, cls.status_patch)
        cls.apply_patch(cls.candidate_root, cls.combined_patch)

        solver_literal = '"/usr/lib/apt/solvers/apt"'
        replacement = repr(str(cls.fake_solver))
        for path in (cls.baseline, cls.ordinary, cls.candidate):
            text = path.read_text(encoding="utf-8")
            if text.count(solver_literal) != 2:
                raise AssertionError("unexpected solver path occurrence count")
            path.write_text(text.replace(solver_literal, replacement), encoding="utf-8")
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

    @classmethod
    def apply_patch(cls, root: pathlib.Path, patch: pathlib.Path) -> None:
        result = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def assert_child_gone(self, pid: int) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and self.process_exists(pid):
            time.sleep(0.01)
        self.assertFalse(self.process_exists(pid), f"solver PID {pid} survived")

    def run_wrapper(
        self,
        script: pathlib.Path,
        label: str,
        *,
        mode: str,
        status: int = 0,
        signum: int = signal.SIGTERM,
        block_signal_in_wrapper: bool = False,
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
                "FAKE_SOLVER_SIGNAL": str(signum),
                "FAKE_SOLVER_OUTPUT": OUTPUT,
                "FAKE_SOLVER_STDERR": STDERR,
                "FAKE_SOLVER_PIDFILE": str(pidfile),
            }
        )
        command = [sys.executable, str(script)]
        if block_signal_in_wrapper:
            launcher = (
                "import os, signal, sys; "
                "signum=int(sys.argv[1]); "
                "signal.pthread_sigmask(signal.SIG_BLOCK, {signum}); "
                "os.execv(sys.executable, [sys.executable, sys.argv[2]])"
            )
            command = [
                sys.executable,
                "-c",
                launcher,
                str(signum),
                str(script),
            ]
        result = subprocess.run(
            command,
            input=REQUEST,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=10,
        )
        child_pid = int(pidfile.read_text(encoding="utf-8").strip())
        return result, dump.read_text(encoding="utf-8"), child_pid

    def assert_streams(self, result: subprocess.CompletedProcess[str], dump: str) -> None:
        self.assertEqual(result.stdout, OUTPUT)
        self.assertEqual(result.stderr, STDERR)
        self.assertEqual(dump, OUTPUT)

    def test_baseline_false_success_and_candidate_exit_status(self) -> None:
        baseline, baseline_dump, baseline_pid = self.run_wrapper(
            self.baseline, "baseline-exit-7", mode="exit", status=7
        )
        candidate, candidate_dump, candidate_pid = self.run_wrapper(
            self.candidate, "candidate-exit-7", mode="exit", status=7
        )
        self.assertEqual(baseline.returncode, 0)
        self.assertEqual(candidate.returncode, 7)
        self.assert_streams(baseline, baseline_dump)
        self.assert_streams(candidate, candidate_dump)
        self.assert_child_gone(baseline_pid)
        self.assert_child_gone(candidate_pid)

    def test_success_remains_zero(self) -> None:
        for label, script in (
            ("baseline", self.baseline),
            ("ordinary", self.ordinary),
            ("candidate", self.candidate),
        ):
            result, dump, child_pid = self.run_wrapper(
                script, f"{label}-exit-0", mode="exit", status=0
            )
            self.assertEqual(result.returncode, 0)
            self.assert_streams(result, dump)
            self.assert_child_gone(child_pid)

    def test_sigterm_and_sigint_are_reraised_exactly(self) -> None:
        for signum in (signal.SIGTERM, signal.SIGINT):
            ordinary, ordinary_dump, ordinary_pid = self.run_wrapper(
                self.ordinary,
                f"ordinary-signal-{signum}",
                mode="signal",
                signum=signum,
            )
            candidate, candidate_dump, candidate_pid = self.run_wrapper(
                self.candidate,
                f"candidate-signal-{signum}",
                mode="signal",
                signum=signum,
            )
            self.assertEqual(ordinary.returncode, 256 - signum)
            self.assertEqual(candidate.returncode, -signum)
            self.assert_streams(ordinary, ordinary_dump)
            self.assert_streams(candidate, candidate_dump)
            self.assert_child_gone(ordinary_pid)
            self.assert_child_gone(candidate_pid)

    def test_inherited_blocked_sigterm_is_unblocked_before_reraise(self) -> None:
        result, dump, child_pid = self.run_wrapper(
            self.candidate,
            "candidate-blocked-sigterm",
            mode="signal",
            signum=signal.SIGTERM,
            block_signal_in_wrapper=True,
        )
        self.assertEqual(result.returncode, -signal.SIGTERM)
        self.assert_streams(result, dump)
        self.assert_child_gone(child_pid)

    def test_composed_source_contains_one_result_decision(self) -> None:
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertEqual(candidate.count("returncode = p.wait()"), 1)
        self.assertEqual(candidate.count("if returncode < 0:"), 1)
        self.assertEqual(candidate.count("if returncode != 0:"), 1)
        self.assertIn("sys.stdout.flush()", candidate)
        self.assertIn("signal.signal(signum, signal.SIG_DFL)", candidate)
        self.assertIn(
            "signal.pthread_sigmask(signal.SIG_UNBLOCK, {signum})", candidate
        )
        self.assertIn("os.kill(os.getpid(), signum)", candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
