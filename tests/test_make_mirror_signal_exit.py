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
        tree = root / "candidate-tree"
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
    def candidate_blocks(source: str) -> tuple[str, str]:
        function_start = source.index("stop_proxy() {\n")
        function_end = source.index(
            './caching_proxy.py "$oldcachedir" "$newcachedir" &', function_start
        )
        functions = source[function_start:function_end]
        trap_start = source.index("trap 'cleanup_owner' EXIT", function_end)
        trap_end = source.index("\n\nfor i in", trap_start)
        traps = source[trap_start:trap_end] + "\n"
        return functions, traps

    @staticmethod
    def baseline_blocks(source: str) -> tuple[str, str]:
        trap = "trap 'kill \"$PROXYPID\" || :;cleanup_newcachedir' EXIT INT TERM"
        if source.count(trap) != 1:
            raise AssertionError("baseline post-readiness trap changed")
        return "", trap + "\n"

    def write_harness(
        self,
        root: pathlib.Path,
        label: str,
        blocks: tuple[str, str],
    ) -> pathlib.Path:
        functions, traps = blocks
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
            "CLEANUP_PROXY_CACHE=yes\n"
            "CLEANUP_TMPDIR=no\n"
            + functions
            + "touch \"$runtime/cache-state\"\n"
            "sleep 60 &\n"
            "PROXYPID=$!\n"
            "printf '%s\\n' \"$PROXYPID\" >\"$runtime/proxy.pid\"\n"
            + traps
            + "printf 'ready\\n' >\"$runtime/ready\"\n"
            "sleep 0.5\n"
            "printf 'after\\n' >\"$runtime/after\"\n",
            encoding="utf-8",
        )
        return script

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def run_signaled(
        self, script: pathlib.Path
    ) -> tuple[subprocess.Popen, pathlib.Path, int, str, str]:
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
                self.fail(
                    f"harness exited before ready: {process.returncode}: {stdout}{stderr}"
                )
            time.sleep(0.01)
        self.assertTrue((runtime / "ready").exists(), "harness did not become ready")
        proxy_pid = int((runtime / "proxy.pid").read_text().strip())
        os.kill(process.pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        return process, runtime, proxy_pid, stdout, stderr

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
                root, "baseline", self.baseline_blocks(baseline_source)
            )
            candidate_script = self.write_harness(
                root, "candidate", self.candidate_blocks(candidate_source)
            )

            (
                baseline_process,
                baseline_runtime,
                _baseline_proxy,
                baseline_stdout,
                _baseline_stderr,
            ) = self.run_signaled(baseline_script)
            self.assertEqual(baseline_process.returncode, 0)
            self.assertEqual(baseline_stdout, "")
            self.assertTrue((baseline_runtime / "after").exists())
            self.assertFalse((baseline_runtime / "cache-state").exists())
            self.assertEqual(
                (baseline_runtime / "cleanup.log").read_text().splitlines(),
                ["cleanup", "cleanup"],
            )

            (
                candidate_process,
                candidate_runtime,
                candidate_proxy,
                candidate_stdout,
                candidate_stderr,
            ) = self.run_signaled(candidate_script)
            self.assertEqual(candidate_process.returncode, 143)
            self.assertEqual(candidate_stdout, "")
            self.assertEqual(candidate_stderr, "")
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
                root, "rerun", self.candidate_blocks(candidate_source)
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

    def test_candidate_replaces_top_level_cleanup_only_signal_traps(self) -> None:
        with tempfile.TemporaryDirectory(prefix="make-mirror-source-") as tmp:
            candidate = self.prepare_candidate(pathlib.Path(tmp))
            self.assertNotIn(
                "trap 'kill \"$PROXYPID\" || :' EXIT INT TERM", candidate
            )
            self.assertNotIn(
                "trap 'kill \"$PROXYPID\" || :;cleanup_newcachedir' EXIT INT TERM",
                candidate,
            )
            self.assertNotIn(
                "trap 'kill \"$PROXYPID\" || :;cleanuptmpdir; "
                "cleanup_newcachedir' EXIT INT TERM",
                candidate,
            )
            self.assertNotIn(
                'trap "cleanup_newcachedir" EXIT INT TERM', candidate
            )
            self.assertNotIn("\nkill $PROXYPID\n", candidate)
            self.assertNotIn("\n  kill $PROXYPID\n", candidate)
            self.assertIn("trap 'cleanup_owner' EXIT", candidate)
            self.assertIn("trap 'signal_exit 130' INT", candidate)
            self.assertIn("trap 'signal_exit 131' QUIT", candidate)
            self.assertIn("trap 'signal_exit 143' TERM", candidate)
            self.assertEqual(candidate.count("stop_proxy"), 4)
            self.assertIn('wait "$PROXYPID" 2>/dev/null || :', candidate)
            self.assertIn("cleanup_owner() {", candidate)
            self.assertIn("CLEANUP_TMPDIR=yes", candidate)
            self.assertIn("CLEANUP_TMPDIR=no", candidate)


if __name__ == "__main__":
    unittest.main()
