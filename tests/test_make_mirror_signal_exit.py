from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest


class MakeMirrorSignalExitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/make_mirror.sh"
        cls.patch = cls.repo / (
            "investigations/make-mirror-signal-exit/"
            "0001-preserve-signal-exit-status.patch"
        )

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate"
        destination = tree / "upstream/mmdebstrap/make_mirror.sh"
        destination.parent.mkdir(parents=True)
        destination.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        checked = subprocess.run(
            ["sh", "-n", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination.read_text(encoding="utf-8")

    @staticmethod
    def candidate_block(source: str) -> str:
        start = source.index("PROXYPID=\nCLEANUP_PROXY_CACHE=no\n")
        end = source.index('./caching_proxy.py "$oldcachedir" "$newcachedir" &', start)
        functions = source[start:end]
        trap_start = source.index("trap 'stop_proxy' EXIT", end)
        trap_end = source.index("\n\nfor i in", trap_start)
        return functions + source[trap_start:trap_end] + "\n"

    @staticmethod
    def baseline_block(source: str) -> str:
        trap = "trap 'kill \"$PROXYPID\" || :' EXIT INT TERM"
        if source.count(trap) != 1:
            raise AssertionError("baseline cleanup-only trap changed")
        return trap + "\n"

    def write_harness(
        self,
        root: pathlib.Path,
        label: str,
        trap_block: str,
    ) -> pathlib.Path:
        runtime = root / label
        runtime.mkdir()
        script = runtime / "harness.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.shell_quote(str(runtime))}\n"
            "cleanup_newcachedir() {\n"
            "  printf 'cleanup\\n' >>\"$runtime/cleanup.log\"\n"
            "  rm -f \"$runtime/cache-state\"\n"
            "}\n"
            "touch \"$runtime/cache-state\"\n"
            "sleep 60 &\n"
            "PROXYPID=$!\n"
            "printf '%s\\n' \"$PROXYPID\" >\"$runtime/proxy.pid\"\n"
            + trap_block
            + "printf 'ready\\n' >\"$runtime/ready\"\n"
            "sleep 0.5\n"
            "printf 'after\\n' >\"$runtime/after\"\n",
            encoding="utf-8",
        )
        return script

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def run_signaled(self, script: pathlib.Path) -> tuple[subprocess.Popen, pathlib.Path, int]:
        runtime = script.parent
        process = subprocess.Popen(
            ["sh", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (runtime / "ready").exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(f"harness exited before ready: {process.returncode}: {stdout}{stderr}")
            time.sleep(0.01)
        self.assertTrue((runtime / "ready").exists(), "harness did not become ready")
        proxy_pid = int((runtime / "proxy.pid").read_text().strip())
        os.kill(process.pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        return process, runtime, proxy_pid

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def test_parent_only_term_preserves_status_and_stops_later_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="make-mirror-signal-") as tmp:
            root = pathlib.Path(tmp)
            baseline_source = self.source.read_text(encoding="utf-8")
            candidate_source = self.prepare_candidate(root)

            baseline_script = self.write_harness(
                root, "baseline", self.baseline_block(baseline_source)
            )
            candidate_script = self.write_harness(
                root, "candidate", self.candidate_block(candidate_source)
            )

            baseline_process, baseline_runtime, _baseline_proxy = self.run_signaled(
                baseline_script
            )
            self.assertEqual(baseline_process.returncode, 0)
            self.assertTrue((baseline_runtime / "after").exists())

            candidate_process, candidate_runtime, candidate_proxy = self.run_signaled(
                candidate_script
            )
            self.assertEqual(candidate_process.returncode, 143)
            self.assertFalse((candidate_runtime / "after").exists())
            self.assertFalse((candidate_runtime / "cache-state").exists())
            self.assertEqual(
                (candidate_runtime / "cleanup.log").read_text().splitlines(),
                ["cleanup"],
            )

            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and self.process_exists(candidate_proxy):
                time.sleep(0.02)
            self.assertFalse(self.process_exists(candidate_proxy))

    def test_unsignaled_candidate_rerun_succeeds_and_cleans_once(self) -> None:
        with tempfile.TemporaryDirectory(prefix="make-mirror-rerun-") as tmp:
            root = pathlib.Path(tmp)
            candidate_source = self.prepare_candidate(root)
            script = self.write_harness(
                root, "rerun", self.candidate_block(candidate_source)
            )
            completed = subprocess.run(
                ["sh", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            runtime = script.parent
            self.assertTrue((runtime / "after").exists())
            self.assertFalse((runtime / "cache-state").exists())
            self.assertEqual(
                (runtime / "cleanup.log").read_text().splitlines(),
                ["cleanup"],
            )
            proxy_pid = int((runtime / "proxy.pid").read_text().strip())
            self.assertFalse(self.process_exists(proxy_pid))

    def test_candidate_replaces_every_cleanup_only_signal_trap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="make-mirror-source-") as tmp:
            candidate = self.prepare_candidate(pathlib.Path(tmp))
            self.assertNotIn("EXIT INT TERM", candidate)
            self.assertIn("trap 'signal_exit 130' INT", candidate)
            self.assertIn("trap 'signal_exit 131' QUIT", candidate)
            self.assertIn("trap 'signal_exit 143' TERM", candidate)
            self.assertEqual(candidate.count("stop_proxy"), 5)
            self.assertIn('wait "$PROXYPID" 2>/dev/null || :', candidate)


if __name__ == "__main__":
    unittest.main()
