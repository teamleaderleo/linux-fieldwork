from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest

from tests import test_make_mirror_update_cache_signal_ownership as ownership


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH2 = (
    ROOT
    / "investigations"
    / "make-mirror-update-cache-subshell"
    / "0002-retain-signals-through-cleanup.patch"
)


class MakeMirrorUpdateCacheCleanupSignalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ownership.MakeMirrorUpdateCacheSignalOwnershipTest.setUpClass()

    def prepare_candidate(
        self, root: pathlib.Path, *, include_repair: bool
    ) -> str:
        helper = ownership.MakeMirrorUpdateCacheSignalOwnershipTest(
            methodName="runTest"
        )
        helper.prepare_candidate(root)
        tree = root / "candidate-tree"
        destination = tree / "upstream/mmdebstrap/make_mirror.sh"

        if include_repair:
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(PATCH2),
                ],
                cwd=tree,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertNotIn(
                "fuzz", (applied.stdout + applied.stderr).lower()
            )

        checked = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination.read_text(encoding="utf-8")

    def candidate_blocks(self, source: str) -> tuple[str, str]:
        helper = ownership.MakeMirrorUpdateCacheSignalOwnershipTest(
            methodName="runTest"
        )
        names = [
            "update_cache_finish",
            "update_cache_exit_cleanup",
            "update_cache_signal_exit",
        ]
        functions: list[str] = []
        if "record_update_cache_cleanup_signal() {" in source:
            initialization = "  update_cache_cleanup_signal_status=0\n"
            self.assertEqual(source.count(initialization), 1)
            functions.extend(
                [
                    initialization.rstrip("\n"),
                    helper.extract_nested_function(
                        source, "record_update_cache_cleanup_signal"
                    ),
                ]
            )
        functions.extend(
            helper.extract_nested_function(source, name) for name in names
        )
        traps = (
            "  trap 'update_cache_exit_cleanup' EXIT\n"
            "  trap 'update_cache_signal_exit 130' INT\n"
            "  trap 'update_cache_signal_exit 131' QUIT\n"
            "  trap 'update_cache_signal_exit 143' TERM\n"
        )
        for line in traps.splitlines(keepends=True):
            self.assertEqual(source.count(line), 1)
        return "\n".join(functions), traps

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def write_case(
        self,
        root: pathlib.Path,
        label: str,
        source: str,
        *,
        mode: str,
        host_status: int = 0,
        cleanup_failure: bool = False,
    ) -> pathlib.Path:
        runtime = root / label
        runtime.mkdir(parents=True)
        functions, traps = self.candidate_blocks(source)
        script = runtime / "case.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.shell_quote(str(runtime))}\n"
            f"host_status={host_status}\n"
            f"cleanup_failure={'yes' if cleanup_failure else 'no'}\n"
            "cleanupapt() {\n"
            "  printf 'start\\n' >>\"$runtime/cleanup.log\"\n"
            "  : >\"$runtime/cleanup-ready\"\n"
            "  while [ ! -e \"$runtime/cleanup-release\" ]; do :; done\n"
            "  printf 'end\\n' >>\"$runtime/cleanup.log\"\n"
            "  rm -f \"$runtime/apt-state\"\n"
            "  if [ \"$cleanup_failure\" = yes ]; then return 74; fi\n"
            "}\n"
            + functions
            + "\n"
            + traps
            + "touch \"$runtime/apt-state\"\n"
            + (
                "update_cache_finish \"$host_status\"\n"
                if mode == "ordinary"
                else (
                    ": >\"$runtime/work-ready\"\n"
                    "while :; do :; done\n"
                )
            )
            + "printf 'later\\n' >\"$runtime/later\"\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    def wait_for_file(
        self,
        path: pathlib.Path,
        process: subprocess.Popen[str],
    ) -> None:
        deadline = time.monotonic() + 5
        while not path.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"process exited before {path.name}: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=5)
                self.fail(f"timed out waiting for {path}")
            time.sleep(0.01)

    def run_signals_during_cleanup(
        self,
        script: pathlib.Path,
        *,
        first_signal: signal.Signals,
        second_signal: signal.Signals | None = None,
        first_starts_cleanup: bool,
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        if first_starts_cleanup:
            self.wait_for_file(script.parent / "work-ready", process)
            os.kill(process.pid, first_signal)
            self.wait_for_file(script.parent / "cleanup-ready", process)
        else:
            self.wait_for_file(script.parent / "cleanup-ready", process)
            os.kill(process.pid, first_signal)

        if second_signal is not None:
            time.sleep(0.05)
            if process.poll() is None:
                os.kill(process.pid, second_signal)

        time.sleep(0.05)
        if process.poll() is None:
            (script.parent / "cleanup-release").touch()
        stdout, stderr = process.communicate(timeout=5)
        return subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout,
            stderr,
        )

    @staticmethod
    def cleanup_log(runtime: pathlib.Path) -> list[str]:
        path = runtime / "cleanup.log"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def test_predecessor_second_signal_replaces_explicit_term(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="update-cache-cleanup-predecessor-explicit-"
        ) as temporary:
            root = pathlib.Path(temporary)
            source = self.prepare_candidate(root, include_repair=False)
            script = self.write_case(
                root,
                "predecessor-explicit",
                source,
                mode="explicit",
            )
            result = self.run_signals_during_cleanup(
                script,
                first_signal=signal.SIGTERM,
                second_signal=signal.SIGINT,
                first_starts_cleanup=True,
            )
            self.assertEqual(result.returncode, -int(signal.SIGINT), result.stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["start"])
            self.assertTrue((script.parent / "apt-state").exists())
            self.assertFalse((script.parent / "later").exists())

    def test_predecessor_first_signal_interrupts_ordinary_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="update-cache-cleanup-predecessor-ordinary-"
        ) as temporary:
            root = pathlib.Path(temporary)
            source = self.prepare_candidate(root, include_repair=False)
            script = self.write_case(
                root,
                "predecessor-ordinary",
                source,
                mode="ordinary",
            )
            result = self.run_signals_during_cleanup(
                script,
                first_signal=signal.SIGTERM,
                first_starts_cleanup=False,
            )
            self.assertEqual(result.returncode, -int(signal.SIGTERM), result.stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["start"])
            self.assertTrue((script.parent / "apt-state").exists())
            self.assertFalse((script.parent / "later").exists())

    def test_repair_retains_explicit_term_and_completes_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="update-cache-cleanup-repair-explicit-"
        ) as temporary:
            root = pathlib.Path(temporary)
            source = self.prepare_candidate(root, include_repair=True)
            script = self.write_case(
                root,
                "repair-explicit",
                source,
                mode="explicit",
            )
            result = self.run_signals_during_cleanup(
                script,
                first_signal=signal.SIGTERM,
                second_signal=signal.SIGINT,
                first_starts_cleanup=True,
            )
            self.assertEqual(result.returncode, 143, result.stderr)
            self.assertEqual(self.cleanup_log(script.parent), ["start", "end"])
            self.assertFalse((script.parent / "apt-state").exists())
            self.assertFalse((script.parent / "later").exists())

    def test_repair_records_first_signal_during_ordinary_cleanup(self) -> None:
        cases = (
            (signal.SIGINT, 130),
            (signal.SIGQUIT, 131),
            (signal.SIGTERM, 143),
        )
        for index, (first_signal, expected) in enumerate(cases):
            with self.subTest(signal=first_signal.name):
                with tempfile.TemporaryDirectory(
                    prefix=f"update-cache-cleanup-repair-{index}-"
                ) as temporary:
                    root = pathlib.Path(temporary)
                    source = self.prepare_candidate(root, include_repair=True)
                    script = self.write_case(
                        root,
                        "repair-ordinary",
                        source,
                        mode="ordinary",
                    )
                    result = self.run_signals_during_cleanup(
                        script,
                        first_signal=first_signal,
                        second_signal=signal.SIGTERM,
                        first_starts_cleanup=False,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(
                        self.cleanup_log(script.parent), ["start", "end"]
                    )
                    self.assertFalse((script.parent / "apt-state").exists())
                    self.assertFalse((script.parent / "later").exists())

    def test_repair_precedence_and_source_contract(self) -> None:
        cases = (
            ("host-over-signal", 42, False, 42),
            ("signal-over-cleanup", 0, True, 143),
        )
        for label, host_status, cleanup_failure, expected in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(
                    prefix=f"update-cache-cleanup-{label}-"
                ) as temporary:
                    root = pathlib.Path(temporary)
                    source = self.prepare_candidate(root, include_repair=True)
                    script = self.write_case(
                        root,
                        label,
                        source,
                        mode="ordinary",
                        host_status=host_status,
                        cleanup_failure=cleanup_failure,
                    )
                    result = self.run_signals_during_cleanup(
                        script,
                        first_signal=signal.SIGTERM,
                        first_starts_cleanup=False,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(
                        self.cleanup_log(script.parent), ["start", "end"]
                    )
                    self.assertFalse((script.parent / "apt-state").exists())

        with tempfile.TemporaryDirectory(
            prefix="update-cache-cleanup-source-contract-"
        ) as temporary:
            source = self.prepare_candidate(
                pathlib.Path(temporary), include_repair=True
            )
        helper = ownership.MakeMirrorUpdateCacheSignalOwnershipTest(
            methodName="runTest"
        )
        recorder = helper.extract_nested_function(
            source, "record_update_cache_cleanup_signal"
        )
        finish = helper.extract_nested_function(source, "update_cache_finish")
        signal_handler = helper.extract_nested_function(
            source, "update_cache_signal_exit"
        )
        self.assertIn("update_cache_cleanup_signal_status=0", source)
        self.assertIn(
            'if [ "$update_cache_cleanup_signal_status" -eq 0 ]; then',
            recorder,
        )
        self.assertIn("trap '' INT QUIT TERM", recorder)
        self.assertLess(
            finish.index("trap 'record_update_cache_cleanup_signal 130' INT"),
            finish.index("trap - EXIT"),
        )
        self.assertIn("trap '' INT QUIT TERM", finish)
        self.assertIn(
            'exit "$update_cache_cleanup_signal_status"', finish
        )
        self.assertLess(
            signal_handler.index("update_cache_cleanup_signal_status=$1"),
            signal_handler.index("trap '' INT QUIT TERM"),
        )
        self.assertLess(
            signal_handler.index("trap '' INT QUIT TERM"),
            signal_handler.index('update_cache_finish "$1"'),
        )


if __name__ == "__main__":
    unittest.main()
