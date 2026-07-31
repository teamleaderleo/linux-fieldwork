from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/run_qemu.sh"
PATCH = (
    ROOT
    / "investigations"
    / "run-qemu-result-precedence"
    / "0001-preserve-primary-result.patch"
)


class RunQemuResultPrecedenceTest(unittest.TestCase):
    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate-tree"
        destination = tree / "upstream/mmdebstrap/run_qemu.sh"
        destination.parent.mkdir(parents=True)
        destination.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=tree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return destination.read_text(encoding="utf-8")

    @staticmethod
    def extract_function(source: str, name: str) -> str:
        start = source.index(f"{name}() {{\n")
        end = source.index("\n}\n", start) + len("\n}\n")
        return source[start:end]

    def baseline_blocks(self, source: str) -> tuple[str, str]:
        function = self.extract_function(source, "cleanup")
        trap = "trap cleanup INT TERM EXIT\n"
        self.assertEqual(source.count(trap), 1)
        return function, trap

    def candidate_blocks(self, source: str) -> tuple[str, str]:
        functions = "\n".join(
            self.extract_function(source, name)
            for name in ("finish", "cleanup_exit", "cleanup_signal")
        )
        traps = (
            "trap cleanup_exit EXIT\n"
            "trap 'cleanup_signal 130' INT\n"
            "trap 'cleanup_signal 143' TERM\n"
        )
        for line in traps.splitlines(keepends=True):
            self.assertEqual(source.count(line), 1)
        return functions, traps

    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def write_case(
        self,
        root: pathlib.Path,
        label: str,
        blocks: tuple[str, str],
        *,
        host_status: int,
        guest_status: str | None,
        cleanup_failure: bool = False,
        wait_for_signal: bool = False,
    ) -> pathlib.Path:
        runtime = root / label
        runtime.mkdir(parents=True)
        shared = runtime / "shared"
        shared.mkdir()
        (shared / "output.txt").touch()
        if guest_status is not None:
            (shared / "exitstatus.txt").write_text(
                guest_status + "\n", encoding="utf-8"
            )
        tmpdir = runtime / "tmp"
        tmpdir.mkdir()
        (tmpdir / "log").touch()

        functions, traps = blocks
        script = runtime / "case.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"tmpdir={self.quote(str(tmpdir))}\n"
            f"cleanup_failure={'yes' if cleanup_failure else 'no'}\n"
            "rm() {\n"
            "  printf 'rm\\n' >>\"$runtime/cleanup.log\"\n"
            "  if [ \"$cleanup_failure\" = yes ]; then return 74; fi\n"
            "  command rm \"$@\"\n"
            "}\n"
            "rmdir() {\n"
            "  printf 'rmdir\\n' >>\"$runtime/cleanup.log\"\n"
            "  if [ \"$cleanup_failure\" = yes ]; then return 74; fi\n"
            "  command rmdir \"$@\"\n"
            "}\n"
            + functions
            + "\n"
            + traps
            + (
                "sleep 0.35\n"
                "printf 'later\\n' >\"$runtime/later\"\n"
                if wait_for_signal
                else f"exit {host_status}\n"
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    def run_ordinary(self, script: pathlib.Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )

    def run_signaled(
        self, script: pathlib.Path, sig: signal.Signals
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        time.sleep(0.08)
        os.kill(process.pid, sig)
        stdout, stderr = process.communicate(timeout=5)
        return subprocess.CompletedProcess(
            process.args, process.returncode, stdout, stderr
        )

    @staticmethod
    def cleanup_log(runtime: pathlib.Path) -> list[str]:
        path = runtime / "cleanup.log"
        return path.read_text().splitlines() if path.exists() else []

    def test_baseline_overwrites_host_failure_candidate_preserves_it(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="run-qemu-primary-") as td:
            root = pathlib.Path(td)
            baseline = self.write_case(
                root,
                "baseline",
                self.baseline_blocks(source),
                host_status=124,
                guest_status="1",
            )
            baseline_result = self.run_ordinary(baseline)
            self.assertEqual(baseline_result.returncode, 1)

            candidate_source = self.prepare_candidate(root)
            candidate = self.write_case(
                root,
                "candidate",
                self.candidate_blocks(candidate_source),
                host_status=124,
                guest_status="1",
            )
            candidate_result = self.run_ordinary(candidate)
            self.assertEqual(candidate_result.returncode, 124)
            self.assertEqual(
                self.cleanup_log(candidate.parent), ["rm", "rmdir"]
            )

    def test_candidate_result_precedence_matrix(self) -> None:
        cases = (
            ("all-success", 0, "0", False, 0),
            ("guest-failure", 0, "1", False, 1),
            ("guest-malformed", 0, "broken", False, 1),
            ("host-failure", 42, "0", False, 42),
            ("host-over-guest", 124, "1", False, 124),
            ("signal-like-over-guest", 143, "1", False, 143),
            ("missing-guest-on-success", 0, None, False, 1),
            ("missing-guest-after-host", 42, None, False, 42),
            ("cleanup-after-success", 0, "0", True, 74),
            ("host-over-cleanup", 42, "0", True, 42),
            ("guest-over-cleanup", 0, "1", True, 1),
        )
        with tempfile.TemporaryDirectory(prefix="run-qemu-matrix-") as td:
            root = pathlib.Path(td)
            candidate_source = self.prepare_candidate(root)
            blocks = self.candidate_blocks(candidate_source)
            for label, host, guest, cleanup_failure, expected in cases:
                with self.subTest(label=label):
                    script = self.write_case(
                        root,
                        label,
                        blocks,
                        host_status=host,
                        guest_status=guest,
                        cleanup_failure=cleanup_failure,
                    )
                    result = self.run_ordinary(script)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(
                        self.cleanup_log(script.parent), ["rm", "rmdir"]
                    )

    def test_signals_keep_identity_and_cleanup_once(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        cases = (
            (signal.SIGINT, 130),
            (signal.SIGTERM, 143),
        )
        with tempfile.TemporaryDirectory(prefix="run-qemu-signal-") as td:
            root = pathlib.Path(td)
            candidate_source = self.prepare_candidate(root)
            for sig, expected in cases:
                for guest in ("0", "1"):
                    with self.subTest(signal=sig.name, guest=guest):
                        baseline = self.write_case(
                            root,
                            f"baseline-{sig.name}-{guest}",
                            self.baseline_blocks(source),
                            host_status=0,
                            guest_status=guest,
                            wait_for_signal=True,
                        )
                        baseline_result = self.run_signaled(baseline, sig)
                        self.assertEqual(
                            baseline_result.returncode,
                            0 if guest == "0" else 1,
                        )
                        self.assertFalse((baseline.parent / "later").exists())
                        self.assertEqual(
                            self.cleanup_log(baseline.parent),
                            ["rm", "rmdir", "rm"],
                        )

                        candidate = self.write_case(
                            root,
                            f"candidate-{sig.name}-{guest}",
                            self.candidate_blocks(candidate_source),
                            host_status=0,
                            guest_status=guest,
                            wait_for_signal=True,
                        )
                        candidate_result = self.run_signaled(candidate, sig)
                        self.assertEqual(candidate_result.returncode, expected)
                        self.assertFalse((candidate.parent / "later").exists())
                        self.assertEqual(
                            self.cleanup_log(candidate.parent), ["rm", "rmdir"]
                        )

    def test_candidate_source_separates_exit_and_signal_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-source-") as td:
            candidate = self.prepare_candidate(pathlib.Path(td))
        self.assertNotIn("trap cleanup INT TERM EXIT", candidate)
        self.assertIn("finish() {", candidate)
        self.assertIn("cleanup_exit() {", candidate)
        self.assertIn("cleanup_signal() {", candidate)
        self.assertIn("trap - INT TERM EXIT", candidate)
        self.assertIn("trap cleanup_exit EXIT", candidate)
        self.assertIn("trap 'cleanup_signal 130' INT", candidate)
        self.assertIn("trap 'cleanup_signal 143' TERM", candidate)
        self.assertIn('if [ "$rv" -ne 0 ]; then', candidate)
        self.assertLess(
            candidate.index('if [ "$rv" -ne 0 ]; then'),
            candidate.index('if [ "$guest" -ne 0 ]; then'),
        )


if __name__ == "__main__":
    unittest.main()
