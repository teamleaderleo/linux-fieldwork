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
PATCH1 = (
    ROOT
    / "investigations"
    / "run-qemu-result-precedence"
    / "0001-preserve-primary-result.patch"
)
PATCH2 = (
    ROOT
    / "investigations"
    / "run-qemu-result-precedence"
    / "0002-retain-first-signal-through-cleanup.patch"
)


class RunQemuFirstSignalCleanupTest(unittest.TestCase):
    def prepare_candidate(
        self, root: pathlib.Path, *, include_repair: bool
    ) -> str:
        tree = root / ("repaired-tree" if include_repair else "pre-repair-tree")
        destination = tree / "upstream/mmdebstrap/run_qemu.sh"
        destination.parent.mkdir(parents=True)
        destination.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")

        patches = [PATCH1]
        if include_repair:
            patches.append(PATCH2)
        for patch in patches:
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(patch),
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
        start = source.index(f"{name}() {{\n")
        end = source.index("\n}\n", start) + len("\n}\n")
        return source[start:end]

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
        cleanup_hold: bool = False,
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
            f"cleanup_hold={'yes' if cleanup_hold else 'no'}\n"
            "rm() {\n"
            "  printf 'rm\\n' >>\"$runtime/cleanup.log\"\n"
            "  if [ \"$cleanup_hold\" = yes ]; then\n"
            "    : >\"$runtime/cleanup-ready\"\n"
            "    while [ ! -e \"$runtime/cleanup-release\" ]; do :; done\n"
            "  fi\n"
            "  if [ \"$cleanup_failure\" = yes ]; then return 74; fi\n"
            "  command rm \"$@\"\n"
            "}\n"
            "rmdir() {\n"
            "  printf 'rmdir\\n' >>\"$runtime/cleanup.log\"\n"
            "  if [ \"$cleanup_failure\" = yes ]; then return 75; fi\n"
            "  command rmdir \"$@\"\n"
            "}\n"
            + functions
            + "\n"
            + traps
            + (
                "while :; do :; done\n"
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

    def run_competing_signals(
        self,
        script: pathlib.Path,
        first: signal.Signals,
        second: signal.Signals,
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        time.sleep(0.05)
        os.kill(process.pid, first)

        ready = script.parent / "cleanup-ready"
        deadline = time.monotonic() + 5
        while not ready.exists():
            if process.poll() is not None:
                self.fail(
                    "process exited before reaching cleanup barrier: "
                    f"{process.returncode}"
                )
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=5)
                self.fail("cleanup barrier was not reached")
            time.sleep(0.01)

        os.kill(process.pid, second)
        time.sleep(0.05)
        if process.poll() is None:
            (script.parent / "cleanup-release").touch()
        stdout, stderr = process.communicate(timeout=5)
        return subprocess.CompletedProcess(
            process.args, process.returncode, stdout, stderr
        )

    @staticmethod
    def cleanup_log(runtime: pathlib.Path) -> list[str]:
        path = runtime / "cleanup.log"
        return path.read_text().splitlines() if path.exists() else []

    def test_composed_result_precedence_matrix(self) -> None:
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
        with tempfile.TemporaryDirectory(prefix="run-qemu-composed-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, include_repair=True)
            blocks = self.candidate_blocks(source)
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

    def test_pre_repair_candidate_loses_first_signal_during_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-pre-repair-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, include_repair=False)
            script = self.write_case(
                root,
                "pre-repair",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="0",
                cleanup_hold=True,
                wait_for_signal=True,
            )
            result = self.run_competing_signals(
                script, signal.SIGTERM, signal.SIGINT
            )
            self.assertEqual(result.returncode, -int(signal.SIGINT), result.stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["rm"])
            self.assertTrue((script.parent / "tmp").exists())
            self.assertFalse((script.parent / "later").exists())

    def test_repair_retains_first_signal_and_finishes_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-repair-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root, include_repair=True)
            script = self.write_case(
                root,
                "repair",
                self.candidate_blocks(source),
                host_status=0,
                guest_status="0",
                cleanup_hold=True,
                wait_for_signal=True,
            )
            result = self.run_competing_signals(
                script, signal.SIGTERM, signal.SIGINT
            )
            self.assertEqual(result.returncode, 143, result.stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["rm", "rmdir"])
            self.assertFalse((script.parent / "tmp").exists())
            self.assertFalse((script.parent / "later").exists())

    def test_composed_source_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-contract-") as td:
            source = self.prepare_candidate(
                pathlib.Path(td), include_repair=True
            )
        self.assertNotIn("trap - INT TERM EXIT", source)
        self.assertEqual(source.count("trap '' INT TERM"), 2)
        self.assertEqual(source.count("trap - EXIT"), 2)
        self.assertIn("trap cleanup_exit EXIT", source)
        self.assertIn("trap 'cleanup_signal 130' INT", source)
        self.assertIn("trap 'cleanup_signal 143' TERM", source)


if __name__ == "__main__":
    unittest.main()
