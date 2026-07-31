from __future__ import annotations

import dataclasses
import json
import pathlib
import tempfile
import unittest

from tools.audit_pr_evidence_identity import build_receipt
from tools.summarize_mmdebstrap_reproduction import (
    ArtifactSummaryError,
    summarize_artifact,
)


BASE = "a" * 40
HEAD = "b" * 40
CHECKOUT = "c" * 40
RUN_ID = "30641621084"
RUN_ATTEMPT = "1"
ARTIFACT_ID = "8799126060"
ARTIFACT_DIGEST = "sha256:" + "d" * 64


class MmdebstrapReproductionArtifactSummaryTest(unittest.TestCase):
    def make_artifact(
        self,
        root: pathlib.Path,
        console: str,
        *,
        exit_status: int = 6,
        head: str = HEAD,
        duplicate_console: bool = False,
    ) -> pathlib.Path:
        run = root / "gha-30641621084-1"
        run.mkdir(parents=True)
        identity_input = {
            "checkout_sha": CHECKOUT,
            "parents": [BASE, head],
            "head_sha": head,
            "base_sha": BASE,
            "event_sha": CHECKOUT,
            "event_name": "pull_request",
            "ref": "refs/pull/366/merge",
            "head_ref": "investigation/mmdebstrap-autopkgtest-checkout-identity",
            "base_ref": "investigation/mmdebstrap-autopkgtest-current-main-v2",
            "run_id": RUN_ID,
            "run_attempt": RUN_ATTEMPT,
            "expected": "synthetic-merge-ref",
        }
        receipt = build_receipt(identity_input)
        (run / "repository-identity-input.json").write_text(
            json.dumps(identity_input, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (run / "repository-identity.json").write_text(
            json.dumps(dataclasses.asdict(receipt), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        (run / "repository-rev-list.txt").write_text(
            f"{CHECKOUT} {BASE} {head}\n",
            encoding="utf-8",
        )
        (run / "autopkgtest-console.log").write_text(console, encoding="utf-8")
        if duplicate_console:
            nested = run / "nested"
            nested.mkdir()
            (nested / "autopkgtest-console.log").write_text(
                console, encoding="utf-8"
            )
        (run / "exit-status").write_text(f"{exit_status}\n", encoding="utf-8")
        (run / "container-exit-status").write_text(
            f"{exit_status}\n", encoding="utf-8"
        )
        (run / "result.md").write_text(
            "# Reproduction result\n\n"
            f"- Exit status: `{exit_status}`\n"
            "- Classification: `failure`\n"
            "- Repository checkout classification: `synthetic-merge-ref`\n",
            encoding="utf-8",
        )
        (run / "phase-order.stdout").write_text(
            "hook-free hard phase precedes broad matrix\n",
            encoding="utf-8",
        )
        return run

    def summarize(self, root: pathlib.Path, *, head: str = HEAD):
        return summarize_artifact(
            root,
            expected_head=head,
            expected_base=BASE,
            expected_checkout=CHECKOUT,
            expected_run_id=RUN_ID,
            expected_run_attempt=RUN_ATTEMPT,
            artifact_id=ARTIFACT_ID,
            artifact_digest=ARTIFACT_DIGEST,
        )

    def test_focus_pass_before_later_broad_failure(self) -> None:
        console = """\
(1/2) create-directory
 dist: unstable mode: root variant: apt format: directory
result: SUCCESS
(2/2) root-without-cap-sys-admin
 dist: unstable mode: root variant: apt format: tar
result: SUCCESS
(1/3) help
 dist: unstable mode: root variant: apt format: auto
result: SUCCESS
(2/3) later-broad-case
 dist: unstable mode: unshare variant: apt format: tar
result: FAILURE
testsuite FAIL non-zero exit status 6
"""
        with tempfile.TemporaryDirectory(prefix="artifact-summary-pass-") as td:
            root = pathlib.Path(td)
            self.make_artifact(root, console)
            summary = self.summarize(root)

        self.assertEqual(summary["statuses"], {"script": 6, "container": 6})
        self.assertEqual(summary["focus_case"]["state"], "passed")
        self.assertTrue(summary["focus_case"]["before_first_failure"])
        self.assertTrue(summary["focus_case"]["completed_before_first_failure"])
        self.assertEqual(
            summary["console"]["classifier"]["first_failed_test"]["name"],
            "later-broad-case",
        )
        self.assertEqual(
            summary["repository_identity"]["classification"],
            "synthetic-merge-ref",
        )
        self.assertTrue(summary["console"]["failure_context"])

    def test_focus_pass_before_wrapper_only_failure(self) -> None:
        console = """\
(1/2) create-directory
result: SUCCESS
(2/2) root-without-cap-sys-admin
result: SUCCESS
generated package helper exited unexpectedly
testsuite FAIL non-zero exit status 6
"""
        with tempfile.TemporaryDirectory(prefix="artifact-summary-wrapper-") as td:
            root = pathlib.Path(td)
            self.make_artifact(root, console)
            summary = self.summarize(root)

        classifier = summary["console"]["classifier"]
        self.assertEqual(classifier["phase"], "unknown")
        self.assertIsNone(classifier["first_failure_line"])
        self.assertTrue(classifier["wrapper_failure_only"])
        self.assertEqual(summary["focus_case"]["state"], "passed")
        self.assertTrue(summary["focus_case"]["before_first_failure"])
        self.assertTrue(summary["focus_case"]["completed_before_first_failure"])
        self.assertEqual(summary["console"]["first_wrapper_failure_line"], 6)
        self.assertEqual(summary["console"]["ordering_failure_line"], 6)

    def test_focus_failure_is_authoritative(self) -> None:
        console = """\
(1/2) create-directory
result: SUCCESS
(2/2) root-without-cap-sys-admin
 dist: unstable mode: root variant: apt format: tar
result: FAILURE
testsuite FAIL non-zero exit status 1
"""
        with tempfile.TemporaryDirectory(prefix="artifact-summary-fail-") as td:
            root = pathlib.Path(td)
            self.make_artifact(root, console, exit_status=1)
            summary = self.summarize(root)

        self.assertEqual(summary["focus_case"]["state"], "failed")
        self.assertEqual(
            summary["console"]["classifier"]["first_failed_test"]["name"],
            "root-without-cap-sys-admin",
        )
        self.assertFalse(summary["focus_case"]["completed_before_first_failure"])

    def test_absent_focus_case_is_not_promoted(self) -> None:
        console = """\
(1/2) help
result: SUCCESS
(2/2) broad-failure
result: FAILURE
testsuite FAIL non-zero exit status 6
"""
        with tempfile.TemporaryDirectory(prefix="artifact-summary-absent-") as td:
            root = pathlib.Path(td)
            self.make_artifact(root, console)
            summary = self.summarize(root)

        self.assertEqual(summary["focus_case"]["state"], "absent")
        self.assertFalse(summary["focus_case"]["before_first_failure"])
        self.assertEqual(summary["focus_case"]["occurrences"], [])

    def test_identity_mismatch_fails_closed(self) -> None:
        console = "(1/1) root-without-cap-sys-admin\nresult: SUCCESS\n"
        wrong_head = "e" * 40
        with tempfile.TemporaryDirectory(prefix="artifact-summary-identity-") as td:
            root = pathlib.Path(td)
            self.make_artifact(root, console, head=wrong_head)
            with self.assertRaisesRegex(ArtifactSummaryError, "head mismatch"):
                self.summarize(root)

    def test_duplicate_required_basename_fails_closed(self) -> None:
        console = "(1/1) root-without-cap-sys-admin\nresult: SUCCESS\n"
        with tempfile.TemporaryDirectory(prefix="artifact-summary-duplicate-") as td:
            root = pathlib.Path(td)
            self.make_artifact(root, console, duplicate_console=True)
            with self.assertRaisesRegex(
                ArtifactSummaryError,
                "expected exactly one autopkgtest-console.log, found 2",
            ):
                self.summarize(root)

    def test_status_disagreement_fails_closed(self) -> None:
        console = "(1/1) root-without-cap-sys-admin\nresult: SUCCESS\n"
        with tempfile.TemporaryDirectory(prefix="artifact-summary-status-") as td:
            root = pathlib.Path(td)
            run = self.make_artifact(root, console)
            (run / "container-exit-status").write_text("7\n", encoding="utf-8")
            with self.assertRaisesRegex(ArtifactSummaryError, "status mismatch"):
                self.summarize(root)


if __name__ == "__main__":
    unittest.main()
