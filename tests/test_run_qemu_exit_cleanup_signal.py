from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest

from tests import test_run_qemu_first_signal_cleanup as first_signal


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH3 = (
    ROOT
    / "investigations"
    / "run-qemu-result-precedence"
    / "0003-retain-signal-during-exit-cleanup.patch"
)


class RunQemuExitCleanupSignalTest(unittest.TestCase):
    def prepare_candidate(
        self, root: pathlib.Path, *, include_exit_repair: bool
    ) -> str:
        helper = first_signal.RunQemuFirstSignalCleanupTest(methodName="runTest")
        helper.prepare_candidate(root, include_repair=True)
        tree = root / "repaired-tree"
        destination = tree / "upstream/mmdebstrap/run_qemu.sh"

        if include_exit_repair:
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(PATCH3),
                ],
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
    def extract_exact_function(source: str, name: str) -> str:
        marker = f"{name}() {{\n"
        if source.startswith(marker):
            start = 0
        else:
            boundary = f"\n{marker}"
            boundary_start = source.find(boundary)
            if boundary_start == -1:
                raise ValueError(f"function not found at line boundary: {name}")
            start = boundary_start + 1
        end = source.index("\n}\n", start) + len("\n}\n")
        return source[start:end]

    def candidate_blocks(self, source: str) -> tuple[str, str]:
        functions = "\n".join(
            self.extract_exact_function(source, name)
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

    def run_signals_during_cleanup(
        self,
        script: pathlib.Path,
        signals: tuple[signal.Signals, ...],
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        ready = script.parent / "cleanup-ready"
        deadline = time.monotonic() + 5
        while not ready.exists():
            if process.poll() is not None:
                self.fail(
                    "process exited before reaching ordinary EXIT cleanup: "
                    f"{process.returncode}"
                )
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=5)
                self.fail("ordinary EXIT cleanup barrier was not reached")
            time.sleep(0.01)

        for sig in signals:
            os.kill(process.pid, sig)
            time.sleep(0.05)
            if process.poll() is not None:
                break

        if process.poll() is None:
            (script.parent / "cleanup-release").touch()
        stdout, stderr = process.communicate(timeout=5)
        return subprocess.CompletedProcess(
            process.args, process.returncode, stdout, stderr
        )

    def make_case(
        self,
        root: pathlib.Path,
        label: str,
        source: str,
        *,
        host_status: int = 0,
        guest_status: str | None = "0",
        cleanup_failure: bool = False,
        cleanup_hold: bool = True,
    ) -> pathlib.Path:
        helper = first_signal.RunQemuFirstSignalCleanupTest(methodName="runTest")
        functions, traps = self.candidate_blocks(source)
        if "record_cleanup_signal() {" in source:
            initialization = "cleanup_signal_status=0"
            self.assertEqual(source.count(initialization + "\n"), 1)
            functions = "\n".join(
                (
                    initialization,
                    self.extract_exact_function(source, "record_cleanup_signal"),
                    functions,
                )
            )
        return helper.write_case(
            root,
            label,
            (functions, traps),
            host_status=host_status,
            guest_status=guest_status,
            cleanup_failure=cleanup_failure,
            cleanup_hold=cleanup_hold,
            wait_for_signal=False,
        )

    @staticmethod
    def cleanup_log(runtime: pathlib.Path) -> list[str]:
        path = runtime / "cleanup.log"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def test_current_stack_ignores_term_during_ordinary_exit_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-exit-pre-repair-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, include_exit_repair=False)
            script = self.make_case(root, "pre-repair", source)
            result = self.run_signals_during_cleanup(script, (signal.SIGTERM,))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["rm", "rmdir"])
            self.assertFalse((script.parent / "tmp").exists())

    def test_repair_reports_first_signal_and_finishes_cleanup(self) -> None:
        cases = (
            ((signal.SIGINT,), 130),
            ((signal.SIGTERM,), 143),
            ((signal.SIGINT, signal.SIGTERM), 130),
            ((signal.SIGTERM, signal.SIGINT), 143),
        )
        for index, (signals, expected) in enumerate(cases):
            with self.subTest(signals=[sig.name for sig in signals]):
                with tempfile.TemporaryDirectory(
                    prefix=f"run-qemu-exit-signal-{index}-"
                ) as td:
                    root = pathlib.Path(td)
                    source = self.prepare_candidate(
                        root, include_exit_repair=True
                    )
                    script = self.make_case(root, "candidate", source)
                    result = self.run_signals_during_cleanup(script, signals)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(
                        self.cleanup_log(script.parent), ["rm", "rmdir"]
                    )
                    self.assertFalse((script.parent / "tmp").exists())

    def test_primary_and_signal_precedence_during_exit_cleanup(self) -> None:
        cases = (
            ("signal-over-guest", 0, "1", False, 143),
            ("host-over-signal", 42, "0", False, 42),
            ("signal-over-cleanup", 0, "0", True, 143),
        )
        for label, host, guest, cleanup_failure, expected in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(
                    prefix=f"run-qemu-exit-{label}-"
                ) as td:
                    root = pathlib.Path(td)
                    source = self.prepare_candidate(
                        root, include_exit_repair=True
                    )
                    script = self.make_case(
                        root,
                        "candidate",
                        source,
                        host_status=host,
                        guest_status=guest,
                        cleanup_failure=cleanup_failure,
                    )
                    result = self.run_signals_during_cleanup(
                        script, (signal.SIGTERM,)
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(
                        self.cleanup_log(script.parent), ["rm", "rmdir"]
                    )

    def test_signaled_cleanup_allows_immediate_clean_rerun(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-exit-rerun-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, include_exit_repair=True)
            first = self.make_case(root, "first", source)
            first_result = self.run_signals_during_cleanup(
                first, (signal.SIGTERM,)
            )
            self.assertEqual(first_result.returncode, 143, first_result.stderr)
            self.assertFalse((first.parent / "tmp").exists())

            second = self.make_case(
                root,
                "second",
                source,
                cleanup_hold=False,
            )
            helper = first_signal.RunQemuFirstSignalCleanupTest(methodName="runTest")
            second_result = helper.run_ordinary(second)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertEqual(self.cleanup_log(second.parent), ["rm", "rmdir"])
            self.assertFalse((second.parent / "tmp").exists())

    def test_composed_source_and_fixture_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-exit-contract-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, include_exit_repair=True)
            script = self.make_case(
                root,
                "fixture-contract",
                source,
                cleanup_hold=False,
            )
            fixture = script.read_text(encoding="utf-8")

        finish = self.extract_exact_function(source, "finish")
        exit_handler = self.extract_exact_function(source, "cleanup_exit")
        signal_handler = self.extract_exact_function(source, "cleanup_signal")
        recorder = self.extract_exact_function(source, "record_cleanup_signal")

        self.assertIn("cleanup_signal_status=0", source)
        self.assertIn("trap '' INT TERM", finish)
        self.assertIn('rv=$cleanup_signal_status', finish)
        self.assertIn("trap 'record_cleanup_signal 130' INT", exit_handler)
        self.assertIn("trap 'record_cleanup_signal 143' TERM", exit_handler)
        self.assertNotIn("trap '' INT TERM", exit_handler)
        self.assertIn("trap '' INT TERM", signal_handler)
        self.assertIn('cleanup_signal_status=$1', recorder)
        self.assertIn('if [ "$cleanup_signal_status" -eq 0 ]; then', recorder)

        self.assertEqual(fixture.count("cleanup_signal_status=0"), 1)
        self.assertEqual(fixture.count("record_cleanup_signal() {"), 1)
        self.assertEqual(fixture.count("\ncleanup_signal() {\n"), 1)
        self.assertIn("trap 'record_cleanup_signal 130' INT", fixture)
        self.assertIn("trap 'record_cleanup_signal 143' TERM", fixture)
        self.assertIn(
            "trap '' INT TERM",
            self.extract_exact_function(fixture, "cleanup_signal"),
        )


if __name__ == "__main__":
    unittest.main()
