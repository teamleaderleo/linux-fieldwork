from __future__ import annotations

import pathlib
import signal
import subprocess
import tempfile
import unittest

from tests import test_run_qemu_exit_cleanup_signal as exit_signal


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH4 = (
    ROOT
    / "investigations"
    / "run-qemu-result-precedence"
    / "0004-preserve-completed-guest-before-cleanup-signal.patch"
)


class RunQemuGuestBeforeCleanupSignalTest(unittest.TestCase):
    def prepare_candidate(
        self,
        root: pathlib.Path,
        *,
        preserve_completed_guest: bool,
    ) -> str:
        helper = exit_signal.RunQemuExitCleanupSignalTest(methodName="runTest")
        source = helper.prepare_candidate(root, include_exit_repair=True)
        tree = root / "repaired-tree"
        destination = tree / "upstream/mmdebstrap/run_qemu.sh"

        if preserve_completed_guest:
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(PATCH4),
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

    def run_cleanup_signal_case(
        self,
        root: pathlib.Path,
        label: str,
        source: str,
        *,
        guest_status: str | None,
        signals: tuple[signal.Signals, ...] = (signal.SIGTERM,),
        host_status: int = 0,
        cleanup_failure: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
        helper = exit_signal.RunQemuExitCleanupSignalTest(methodName="runTest")
        script = helper.make_case(
            root,
            label,
            source,
            host_status=host_status,
            guest_status=guest_status,
            cleanup_failure=cleanup_failure,
        )
        result = helper.run_signals_during_cleanup(script, signals)
        return result, script

    def test_current_policy_replaces_completed_guest_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-guest-current-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(
                root,
                preserve_completed_guest=False,
            )
            result, script = self.run_cleanup_signal_case(
                root,
                "current-policy",
                source,
                guest_status="1",
            )
            self.assertEqual(result.returncode, 143, result.stderr)
            self.assertEqual(
                exit_signal.RunQemuExitCleanupSignalTest.cleanup_log(script.parent),
                ["rm", "rmdir"],
            )

    def test_event_order_candidate_retains_completed_guest_failures(self) -> None:
        cases = (
            ("guest-nonzero", "1"),
            ("guest-malformed", "broken"),
            ("guest-missing", None),
        )
        for label, guest_status in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(
                    prefix=f"run-qemu-{label}-"
                ) as td:
                    root = pathlib.Path(td)
                    source = self.prepare_candidate(
                        root,
                        preserve_completed_guest=True,
                    )
                    result, script = self.run_cleanup_signal_case(
                        root,
                        label,
                        source,
                        guest_status=guest_status,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(
                        exit_signal.RunQemuExitCleanupSignalTest.cleanup_log(
                            script.parent
                        ),
                        ["rm", "rmdir"],
                    )
                    self.assertFalse((script.parent / "tmp").exists())

    def test_signal_remains_authoritative_after_guest_success(self) -> None:
        cases = (
            ("int", (signal.SIGINT,), False, 130),
            ("term", (signal.SIGTERM,), False, 143),
            ("term-over-cleanup", (signal.SIGTERM,), True, 143),
            ("first-int", (signal.SIGINT, signal.SIGTERM), False, 130),
            ("first-term", (signal.SIGTERM, signal.SIGINT), False, 143),
        )
        for label, signals, cleanup_failure, expected in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(
                    prefix=f"run-qemu-{label}-"
                ) as td:
                    root = pathlib.Path(td)
                    source = self.prepare_candidate(
                        root,
                        preserve_completed_guest=True,
                    )
                    result, script = self.run_cleanup_signal_case(
                        root,
                        label,
                        source,
                        guest_status="0",
                        signals=signals,
                        cleanup_failure=cleanup_failure,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(
                        exit_signal.RunQemuExitCleanupSignalTest.cleanup_log(
                            script.parent
                        ),
                        ["rm", "rmdir"],
                    )

    def test_host_failure_stays_ahead_of_guest_and_cleanup_signal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-host-first-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(
                root,
                preserve_completed_guest=True,
            )
            result, _ = self.run_cleanup_signal_case(
                root,
                "host-first",
                source,
                host_status=42,
                guest_status="1",
            )
            self.assertEqual(result.returncode, 42, result.stderr)

    def test_event_order_candidate_reruns_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-event-rerun-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(
                root,
                preserve_completed_guest=True,
            )
            first_result, first = self.run_cleanup_signal_case(
                root,
                "first",
                source,
                guest_status="1",
            )
            self.assertEqual(first_result.returncode, 1, first_result.stderr)
            self.assertFalse((first.parent / "tmp").exists())

            helper = exit_signal.RunQemuExitCleanupSignalTest(methodName="runTest")
            second = helper.make_case(
                root,
                "second",
                source,
                guest_status="0",
                cleanup_hold=False,
            )
            ordinary = exit_signal.first_signal.RunQemuFirstSignalCleanupTest(
                methodName="runTest"
            )
            second_result = ordinary.run_ordinary(second)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertFalse((second.parent / "tmp").exists())

    def test_source_contract_matches_event_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-event-contract-") as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(
                root,
                preserve_completed_guest=True,
            )

        helper = exit_signal.RunQemuExitCleanupSignalTest(methodName="runTest")
        finish = helper.extract_exact_function(source, "finish")
        host_check = finish.index('if [ "$rv" -ne 0 ]; then')
        guest_check = finish.index('if [ "$guest" -ne 0 ]; then')
        signal_check = finish.index(
            'if [ "$cleanup_signal_status" -ne 0 ]; then'
        )
        cleanup_exit = finish.index('exit "$cleanup_status"')

        self.assertLess(host_check, guest_check)
        self.assertLess(guest_check, signal_check)
        self.assertLess(signal_check, cleanup_exit)
        self.assertNotIn(
            'if [ "$rv" -eq 0 ] && [ "$cleanup_signal_status" -ne 0 ]',
            finish,
        )


if __name__ == "__main__":
    unittest.main()
