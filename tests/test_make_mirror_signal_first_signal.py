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


class MakeMirrorSignalFirstSignalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/make_mirror.sh"
        cls.patch = cls.repo / (
            "investigations/make-mirror-signal-exit/"
            "0001-preserve-signal-exit-status.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="make-mirror-first-signal-")
        root = pathlib.Path(cls.work.name)
        tree = root / "candidate-tree"
        cls.candidate = tree / "upstream/mmdebstrap/make_mirror.sh"
        cls.candidate.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.candidate)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(cls.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)
        checked = subprocess.run(
            ["sh", "-n", str(cls.candidate)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if checked.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(checked.stdout + checked.stderr)

        source = cls.candidate.read_text(encoding="utf-8")
        start = source.index("handle_launch_signal() {\n")
        end = source.index("trap 'cleanup_owner' EXIT", start)
        cls.functions = source[start:end]
        cls.baseline_functions = cls.make_overtake_baseline(cls.functions)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    @staticmethod
    def make_overtake_baseline(functions: str) -> str:
        repaired_handler = '''handle_launch_signal() {
  if [ -n "${PROXYPID:-}" ]; then
    signal_exit "${PENDING_SIGNAL:-$1}"
  fi
  if [ -z "${PENDING_SIGNAL:-}" ]; then
    PENDING_SIGNAL=$1
  fi
}
'''
        old_handler = '''record_signal() {
  if [ -z "${PENDING_SIGNAL:-}" ]; then
    PENDING_SIGNAL=$1
  fi
}
'''
        if functions.count(repaired_handler) != 1:
            raise AssertionError("launch signal handler shape changed")
        baseline = functions.replace(repaired_handler, old_handler)
        baseline = baseline.replace("handle_launch_signal", "record_signal")
        repaired_order = '''  PROXYPID=$!
  if [ -n "$PENDING_SIGNAL" ]; then
    signal_exit "$PENDING_SIGNAL"
  fi
  install_signal_traps
'''
        old_order = '''  PROXYPID=$!
  install_signal_traps
  if [ -n "$PENDING_SIGNAL" ]; then
    signal_exit "$PENDING_SIGNAL"
  fi
'''
        if baseline.count(repaired_order) != 1:
            raise AssertionError("launch dispatch order changed")
        return baseline.replace(repaired_order, old_order)

    @staticmethod
    def instrument_candidate(functions: str) -> str:
        seam = '''  "$@" &
  PROXYPID=$!
  if [ -n "$PENDING_SIGNAL" ]; then
'''
        instrumented = '''  "$@" &
  printf '%s\\n' "$!" >"$runtime/proxy.pid"
  printf 'phase1\\n' >"$runtime/phase1"
  kill -STOP "$$"
  PROXYPID=$!
  printf 'phase2\\n' >"$runtime/phase2"
  kill -STOP "$$"
  if [ -n "$PENDING_SIGNAL" ]; then
'''
        if functions.count(seam) != 1:
            raise AssertionError("candidate registration seam changed")
        return functions.replace(seam, instrumented)

    @staticmethod
    def instrument_baseline(functions: str) -> str:
        seam = '''  "$@" &
  PROXYPID=$!
  install_signal_traps
  if [ -n "$PENDING_SIGNAL" ]; then
'''
        instrumented = '''  "$@" &
  printf '%s\\n' "$!" >"$runtime/proxy.pid"
  printf 'phase1\\n' >"$runtime/phase1"
  kill -STOP "$$"
  PROXYPID=$!
  install_signal_traps
  printf 'phase2\\n' >"$runtime/phase2"
  kill -STOP "$$"
  if [ -n "$PENDING_SIGNAL" ]; then
'''
        if functions.count(seam) != 1:
            raise AssertionError("baseline registration seam changed")
        return functions.replace(seam, instrumented)

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def write_harness(
        self, label: str, functions: str, *, candidate: bool
    ) -> pathlib.Path:
        runtime = pathlib.Path(self.work.name) / label
        runtime.mkdir()
        block = (
            self.instrument_candidate(functions)
            if candidate
            else self.instrument_baseline(functions)
        )
        script = runtime / "harness.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.shell_quote(str(runtime))}\n"
            "cleanup_newcachedir() {\n"
            "  printf 'cleanup\\n' >>\"$runtime/cleanup.log\"\n"
            "}\n"
            "cleanuptmpdir() { :; }\n"
            "newcache=cache.B\n"
            "PROXYPID=\n"
            "PENDING_SIGNAL=\n"
            "CLEANUP_PROXY_CACHE=yes\n"
            "CLEANUP_TMPDIR=no\n"
            + block
            + "trap 'cleanup_owner' EXIT\n"
            "install_signal_traps\n"
            "launch_proxy sh -c 'printf ready >\"$1\"; exec sleep 60' "
            "proxy \"$runtime/proxy.ready\"\n"
            "printf 'after\\n' >\"$runtime/after\"\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        checked = subprocess.run(
            ["sh", "-n", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return script

    @staticmethod
    def wait_for_file(path: pathlib.Path, process: subprocess.Popen[str]) -> None:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"owner exited before {path.name}: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        raise AssertionError(f"timed out waiting for {path}")

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def wait_for_pid_exit(self, pid: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not self.process_exists(pid):
                return
            time.sleep(0.01)
        raise AssertionError(f"proxy pid {pid} survived")

    def run_competing_signals(
        self, label: str, functions: str, *, candidate: bool
    ) -> tuple[int, pathlib.Path, int]:
        script = self.write_harness(label, functions, candidate=candidate)
        runtime = script.parent
        process = subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=runtime,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        child_pid = -1
        try:
            self.wait_for_file(runtime / "phase1", process)
            self.wait_for_file(runtime / "proxy.ready", process)
            child_pid = int((runtime / "proxy.pid").read_text().strip())

            os.kill(process.pid, signal.SIGTERM)
            os.kill(process.pid, signal.SIGCONT)

            self.wait_for_file(runtime / "phase2", process)
            os.kill(process.pid, signal.SIGINT)
            os.kill(process.pid, signal.SIGCONT)

            stdout, stderr = process.communicate(timeout=8)
        except BaseException:
            if process.poll() is None:
                process.kill()
                process.wait()
            if child_pid > 0 and self.process_exists(child_pid):
                os.kill(child_pid, signal.SIGKILL)
            raise

        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.wait_for_pid_exit(child_pid)
        return process.returncode, runtime, child_pid

    def assert_cleanup_contract(self, runtime: pathlib.Path) -> None:
        self.assertEqual(
            (runtime / "cleanup.log").read_text(encoding="utf-8").splitlines(),
            ["cleanup"],
        )
        self.assertFalse((runtime / "after").exists())

    def test_first_recorded_term_survives_competing_int(self) -> None:
        baseline_status, baseline_runtime, _ = self.run_competing_signals(
            "baseline-overtake", self.baseline_functions, candidate=False
        )
        candidate_status, candidate_runtime, _ = self.run_competing_signals(
            "candidate-first-signal", self.functions, candidate=True
        )

        self.assertEqual(baseline_status, 128 + signal.SIGINT)
        self.assertEqual(candidate_status, 128 + signal.SIGTERM)
        self.assert_cleanup_contract(baseline_runtime)
        self.assert_cleanup_contract(candidate_runtime)

    def test_candidate_dispatches_pending_signal_before_restoring_traps(self) -> None:
        pid_assignment = self.functions.index("  PROXYPID=$!\n")
        pending_dispatch = self.functions.index(
            '  if [ -n "$PENDING_SIGNAL" ]; then\n', pid_assignment
        )
        ordinary_traps = self.functions.index(
            "  install_signal_traps\n", pending_dispatch
        )
        self.assertLess(pid_assignment, pending_dispatch)
        self.assertLess(pending_dispatch, ordinary_traps)
        self.assertIn(
            'signal_exit "${PENDING_SIGNAL:-$1}"',
            self.functions,
        )


if __name__ == "__main__":
    unittest.main()
