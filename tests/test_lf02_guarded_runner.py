from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "investigations/lf-02-upgrade-failure-recovery/run-guarded.sh"


class LF02GuardedRunnerTest(unittest.TestCase):
    def base_env(self, temporary_root: pathlib.Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "TMPDIR": str(temporary_root),
                "LF02_GUARDED_TEST_MODE": "1",
            }
        )
        return env

    def test_rejects_repository_as_recursive_cleanup_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf02-guard-reject-") as tmp:
            marker = pathlib.Path(tmp) / "command-ran"
            env = self.base_env(ROOT)
            completed = subprocess.run(
                ["bash", str(RUNNER), "bash", "-c", f"touch {marker!s}"],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=15,
            )
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertIn("temporary-root validation failed", completed.stderr)
            self.assertFalse(marker.exists())

    def test_preserves_child_status_and_removes_exact_sandbox(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf02-guard-status-") as tmp:
            root = pathlib.Path(tmp)
            sandbox_record = root / "sandbox"
            command = (
                'printf "%s\\n" "$RUNNER_TEMP" > "$1"; '
                "exit 7"
            )
            completed = subprocess.run(
                [
                    "bash",
                    str(RUNNER),
                    "bash",
                    "-c",
                    command,
                    "guard-child",
                    str(sandbox_record),
                ],
                cwd=ROOT,
                env=self.base_env(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=15,
            )
            self.assertEqual(completed.returncode, 7, completed.stderr)
            sandbox = pathlib.Path(sandbox_record.read_text().strip())
            self.assertEqual(sandbox.parent, root)
            self.assertTrue(sandbox.name.startswith("lf-02-upgrade-failure-recovery."))
            self.assertFalse(sandbox.exists())

    def run_signal_case(self, signal_value: signal.Signals, expected_status: int) -> None:
        with tempfile.TemporaryDirectory(prefix="lf02-guard-signal-") as tmp:
            root = pathlib.Path(tmp)
            child_script = root / "child.sh"
            log = root / "events"
            sandbox_record = root / "sandbox"
            pid_record = root / "child-pid"
            child_script.write_text(
                "#!/usr/bin/env bash\n"
                "set -eu\n"
                'printf "%s\\n" "$RUNNER_TEMP" > "$SANDBOX_RECORD"\n'
                'printf "%s\\n" "$$" > "$PID_RECORD"\n'
                'printf "started\\n" >> "$EVENT_LOG"\n'
                "trap 'printf \"signal\\n\" >> \"$EVENT_LOG\"; while :; do sleep 1; done' INT TERM\n"
                "while :; do sleep 1; done\n"
                'printf "later\\n" >> "$EVENT_LOG"\n',
                encoding="utf-8",
            )
            child_script.chmod(0o755)
            env = self.base_env(root)
            env.update(
                {
                    "EVENT_LOG": str(log),
                    "SANDBOX_RECORD": str(sandbox_record),
                    "PID_RECORD": str(pid_record),
                }
            )
            process = subprocess.Popen(
                ["bash", str(RUNNER), str(child_script)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if log.exists() and "started" in log.read_text(encoding="utf-8"):
                        break
                    time.sleep(0.05)
                else:
                    self.fail("guarded child did not start")

                process.send_signal(signal_value)
                stdout, stderr = process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)

            self.assertEqual(process.returncode, expected_status, stdout + stderr)
            events = log.read_text(encoding="utf-8").splitlines()
            self.assertIn("started", events)
            self.assertNotIn("later", events)
            sandbox = pathlib.Path(sandbox_record.read_text().strip())
            self.assertFalse(sandbox.exists())
            child_pid = int(pid_record.read_text().strip())
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)

    def test_term_stops_process_group_and_preserves_143(self) -> None:
        self.run_signal_case(signal.SIGTERM, 143)

    def test_int_stops_process_group_and_preserves_130(self) -> None:
        self.run_signal_case(signal.SIGINT, 130)


if __name__ == "__main__":
    unittest.main()
