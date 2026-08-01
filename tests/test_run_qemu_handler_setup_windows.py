from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest

from tests import test_run_qemu_first_signal_cleanup as first_signal
from tests import test_run_qemu_guest_before_cleanup_signal as guest_before


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH5 = (
    ROOT
    / "upstream-packets"
    / "units"
    / "05-run-qemu-result-precedence"
    / "patches"
    / "0005-close-signal-handler-setup-windows.patch"
)


class RunQemuHandlerSetupWindowsTest(unittest.TestCase):
    def prepare_candidate(self, root: pathlib.Path, *, repaired: bool) -> str:
        helper = guest_before.RunQemuGuestBeforeCleanupSignalTest(
            methodName="runTest"
        )
        helper.prepare_candidate(root, preserve_completed_guest=True)
        tree = root / "repaired-tree"
        destination = tree / "upstream/mmdebstrap/run_qemu.sh"

        if repaired:
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(PATCH5),
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
    def extract_function(source: str, name: str) -> str:
        marker = f"{name}() {{\n"
        start = source.index(marker)
        end = source.index("\n}\n", start) + len("\n}\n")
        return source[start:end]

    def candidate_blocks(self, source: str) -> tuple[str, str]:
        parts: list[str] = []
        for assignment in ("cleanup_signal_status=0", "cleanup_phase=running"):
            if assignment in source:
                parts.append(assignment)
        parts.extend(
            self.extract_function(source, name)
            for name in (
                "finish",
                "record_cleanup_signal",
                "cleanup_exit",
                "cleanup_signal",
            )
        )
        traps = "\n".join(
            line
            for line in source.splitlines()
            if line.startswith("trap cleanup_exit EXIT")
            or (line.startswith("trap '") and line.endswith(" INT"))
            or (line.startswith("trap '") and line.endswith(" TERM"))
        ) + "\n"
        self.assertEqual(len(traps.splitlines()), 3)
        return "\n".join(parts), traps

    @staticmethod
    def wait_for_file(process: subprocess.Popen[str], path: pathlib.Path) -> None:
        deadline = time.monotonic() + 5
        while not path.exists():
            if process.poll() is not None:
                raise AssertionError(
                    f"process exited before reaching barrier: {process.returncode}"
                )
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=5)
                raise AssertionError(f"barrier was not reached: {path}")
            time.sleep(0.01)

    @staticmethod
    def launch(script: pathlib.Path) -> subprocess.Popen[str]:
        return subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

    @staticmethod
    def cleanup_log(runtime: pathlib.Path) -> list[str]:
        path = runtime / "cleanup.log"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def test_explicit_handler_setup_window_retains_first_signal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-setup-explicit-old-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, repaired=False)
            source = source.replace(
                "cleanup_signal() {\n  rv=$1\n  trap '' INT TERM",
                "cleanup_signal() {\n"
                "  rv=$1\n"
                "  : >\"$runtime/signal-handler-entered\"\n"
                "  while [ ! -e \"$runtime/signal-handler-release\" ]; do :; done\n"
                "  trap '' INT TERM",
                1,
            )
            helper = first_signal.RunQemuFirstSignalCleanupTest(
                methodName="runTest"
            )
            script = helper.write_case(
                root,
                "old",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="0",
                wait_for_signal=True,
            )
            process = self.launch(script)
            time.sleep(0.05)
            os.kill(process.pid, signal.SIGTERM)
            self.wait_for_file(process, script.parent / "signal-handler-entered")
            os.kill(process.pid, signal.SIGINT)
            time.sleep(0.05)
            (script.parent / "signal-handler-release").touch()
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 130, stderr)

        with tempfile.TemporaryDirectory(prefix="run-qemu-setup-explicit-new-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, repaired=True)
            source = source.replace(
                "trap 'trap \"\" INT TERM; cleanup_signal 143' TERM",
                "trap 'trap \"\" INT TERM; "
                ": >\"$runtime/term-trap-entered\"; "
                "while [ ! -e \"$runtime/term-trap-release\" ]; do :; done; "
                "cleanup_signal 143' TERM",
                1,
            )
            helper = first_signal.RunQemuFirstSignalCleanupTest(
                methodName="runTest"
            )
            script = helper.write_case(
                root,
                "new",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="0",
                wait_for_signal=True,
            )
            process = self.launch(script)
            time.sleep(0.05)
            os.kill(process.pid, signal.SIGTERM)
            self.wait_for_file(process, script.parent / "term-trap-entered")
            os.kill(process.pid, signal.SIGINT)
            time.sleep(0.05)
            (script.parent / "term-trap-release").touch()
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["rm", "rmdir"])
            self.assertFalse((script.parent / "tmp").exists())

    def test_exit_handler_setup_window_preserves_completed_guest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-setup-exit-old-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, repaired=False)
            source = source.replace(
                "cleanup_exit() {\n  rv=$?\n  trap 'record_cleanup_signal 130' INT",
                "cleanup_exit() {\n"
                "  rv=$?\n"
                "  : >\"$runtime/exit-handler-entered\"\n"
                "  while [ ! -e \"$runtime/exit-handler-release\" ]; do :; done\n"
                "  trap 'record_cleanup_signal 130' INT",
                1,
            )
            helper = first_signal.RunQemuFirstSignalCleanupTest(
                methodName="runTest"
            )
            script = helper.write_case(
                root,
                "old",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="1",
            )
            process = self.launch(script)
            self.wait_for_file(process, script.parent / "exit-handler-entered")
            os.kill(process.pid, signal.SIGTERM)
            time.sleep(0.05)
            (script.parent / "exit-handler-release").touch()
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, stderr)

        with tempfile.TemporaryDirectory(prefix="run-qemu-setup-exit-new-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, repaired=True)
            source = source.replace(
                "cleanup_exit() {\n"
                "  rv=$? cleanup_phase=exit\n"
                "  trap 'trap \"\" INT TERM; record_cleanup_signal 130' INT",
                "cleanup_exit() {\n"
                "  rv=$? cleanup_phase=exit\n"
                "  : >\"$runtime/exit-handler-entered\"\n"
                "  while [ ! -e \"$runtime/exit-handler-release\" ]; do :; done\n"
                "  trap 'trap \"\" INT TERM; record_cleanup_signal 130' INT",
                1,
            )
            helper = first_signal.RunQemuFirstSignalCleanupTest(
                methodName="runTest"
            )
            script = helper.write_case(
                root,
                "new",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="1",
            )
            process = self.launch(script)
            self.wait_for_file(process, script.parent / "exit-handler-entered")
            os.kill(process.pid, signal.SIGTERM)
            time.sleep(0.05)
            (script.parent / "exit-handler-release").touch()
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 1, stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["rm", "rmdir"])
            self.assertFalse((script.parent / "tmp").exists())

    def test_early_cleanup_signal_remains_first_after_traps_are_reinstalled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-setup-first-writer-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, repaired=True)
            source = source.replace(
                "cleanup_exit() {\n"
                "  rv=$? cleanup_phase=exit\n"
                "  trap 'trap \"\" INT TERM; record_cleanup_signal 130' INT",
                "cleanup_exit() {\n"
                "  rv=$? cleanup_phase=exit\n"
                "  : >\"$runtime/exit-handler-entered\"\n"
                "  while [ ! -e \"$runtime/exit-handler-release\" ]; do :; done\n"
                "  trap 'trap \"\" INT TERM; record_cleanup_signal 130' INT",
                1,
            )
            helper = first_signal.RunQemuFirstSignalCleanupTest(
                methodName="runTest"
            )
            script = helper.write_case(
                root,
                "candidate",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="0",
                cleanup_hold=True,
            )
            process = self.launch(script)
            self.wait_for_file(process, script.parent / "exit-handler-entered")
            os.kill(process.pid, signal.SIGTERM)
            time.sleep(0.05)
            (script.parent / "exit-handler-release").touch()
            self.wait_for_file(process, script.parent / "cleanup-ready")
            os.kill(process.pid, signal.SIGINT)
            time.sleep(0.05)
            (script.parent / "cleanup-release").touch()
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["rm", "rmdir"])
            self.assertFalse((script.parent / "tmp").exists())

    def test_repaired_source_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-setup-contract-") as td:
            source = self.prepare_candidate(pathlib.Path(td), repaired=True)
        self.assertIn("cleanup_phase=running", source)
        self.assertIn("rv=$? cleanup_phase=exit", source)
        self.assertIn(
            "trap 'trap \"\" INT TERM; cleanup_signal 130' INT", source
        )
        self.assertIn(
            "trap 'trap \"\" INT TERM; cleanup_signal 143' TERM", source
        )
        self.assertIn('if [ "$cleanup_phase" = exit ]; then', source)


if __name__ == "__main__":
    unittest.main()
