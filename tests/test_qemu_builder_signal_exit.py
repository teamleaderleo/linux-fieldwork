from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest


class QemuBuilderSignalExitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
        cls.patch = cls.repo / (
            "investigations/qemu-builder-signal-exit/"
            "0001-preserve-signal-exit-status.patch"
        )

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate"
        destination = tree / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
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
    def lifecycle_block(source: str) -> str:
        start = source.index("cleanup() {\n")
        end = source.index("WORKDIR=$(mktemp -d)", start)
        return source[start:end]

    def write_harness(
        self, root: pathlib.Path, label: str, lifecycle: str
    ) -> pathlib.Path:
        runtime = root / label
        runtime.mkdir()
        workdir = runtime / "work"
        workdir.mkdir()
        (workdir / "owned").write_text("owned\n", encoding="utf-8")
        script = runtime / "harness.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"WORKDIR={self.shell_quote(str(workdir))}\n"
            + lifecycle
            + f"printf 'ready\\n' >{self.shell_quote(str(runtime / 'ready'))}\n"
            "sleep 0.5\n"
            + f"printf 'after\\n' >{self.shell_quote(str(runtime / 'after'))}\n",
            encoding="utf-8",
        )
        return script

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def run_signaled(
        self, script: pathlib.Path
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
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
        os.kill(process.pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        return subprocess.CompletedProcess(
            process.args, process.returncode, stdout, stderr
        ), runtime

    def test_parent_only_term_baseline_resumes_but_candidate_exits_143(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-builder-signal-") as tmp:
            root = pathlib.Path(tmp)
            baseline_source = self.source.read_text(encoding="utf-8")
            candidate_source = self.prepare_candidate(root)

            baseline = self.write_harness(
                root, "baseline", self.lifecycle_block(baseline_source)
            )
            candidate = self.write_harness(
                root, "candidate-run", self.lifecycle_block(candidate_source)
            )

            baseline_result, baseline_runtime = self.run_signaled(baseline)
            self.assertEqual(
                baseline_result.returncode,
                0,
                baseline_result.stdout + baseline_result.stderr,
            )
            self.assertTrue((baseline_runtime / "after").exists())
            self.assertFalse((baseline_runtime / "work").exists())

            candidate_result, candidate_runtime = self.run_signaled(candidate)
            self.assertEqual(
                candidate_result.returncode,
                143,
                candidate_result.stdout + candidate_result.stderr,
            )
            self.assertFalse((candidate_runtime / "after").exists())
            self.assertFalse((candidate_runtime / "work").exists())

    def test_unsignaled_candidate_rerun_succeeds_and_cleans(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-builder-rerun-") as tmp:
            root = pathlib.Path(tmp)
            candidate_source = self.prepare_candidate(root)
            script = self.write_harness(
                root, "rerun", self.lifecycle_block(candidate_source)
            )
            completed = subprocess.run(
                ["sh", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            runtime = script.parent
            self.assertTrue((runtime / "after").exists())
            self.assertFalse((runtime / "work").exists())

    def test_candidate_source_separates_exit_and_signal_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-builder-source-") as tmp:
            baseline = self.source.read_text(encoding="utf-8")
            candidate = self.prepare_candidate(pathlib.Path(tmp))
            self.assertIn("trap cleanup EXIT INT TERM QUIT", baseline)
            self.assertNotIn("trap cleanup EXIT INT TERM QUIT", candidate)
            self.assertIn("trap cleanup EXIT", candidate)
            self.assertIn("trap 'signal_exit 130' INT", candidate)
            self.assertIn("trap 'signal_exit 131' QUIT", candidate)
            self.assertIn("trap 'signal_exit 143' TERM", candidate)
            self.assertIn("trap - EXIT INT TERM QUIT", candidate)
            self.assertIn("cleanup || :", candidate)
            self.assertIn('exit "$status"', candidate)


if __name__ == "__main__":
    unittest.main()
