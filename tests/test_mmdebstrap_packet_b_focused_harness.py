from __future__ import annotations

import os
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_mmdebstrap_packet_b_focused.sh"
WORKFLOW = ROOT / ".github/workflows/mmdebstrap-packet-b-focused.yml"


class PacketBFocusedHarnessTest(unittest.TestCase):
    def test_shell_syntax_and_exact_carrier_boundaries(self) -> None:
        syntax = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("validate_disposable_runtime", source)
        self.assertIn("trap '' INT TERM", source)
        self.assertIn("trap - EXIT", source)
        self.assertIn("apply_exact_patch capability", source)
        self.assertIn("apply_exact_patch installed-proxy", source)
        self.assertLess(
            source.index("apply_exact_patch capability"),
            source.index("apply_exact_patch installed-proxy"),
        )
        self.assertIn("prepare_mmdebstrap_packet_b_focused.py", source)
        self.assertIn("verify_mmdebstrap_packet_b_focused.py", source)
        self.assertEqual(source.count("autopkgtest --test-name=testsuite"), 2)
        self.assertNotIn("--ignore-restrictions=hint-testsuite-triggers", source)
        self.assertIn("124)", source)
        self.assertNotIn("124|137)", source)
        self.assertIn("outer-timeout-neutral", source)
        self.assertIn("focused-hard-failure", source)
        self.assertNotIn("sourcesfilter-deb822.patch", source)
        self.assertNotIn("sigint-process-group-kill-sid.patch", source)
        self.assertNotIn("debian_bug_report", source)

    def test_privileged_workflow_requires_owned_exact_branch(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        job_start = source.index("  focused-sid:\n")
        checkout = source.index("      - name: Check out proposed repository state")
        guard_block = source[job_start:checkout]
        self.assertIn("github.event_name == 'pull_request'", guard_block)
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            guard_block,
        )
        self.assertIn(
            "github.head_ref == 'packet-b-focused-current-main'", guard_block
        )
        self.assertLess(guard_block.index("if: >-"), guard_block.index("runs-on:"))
        self.assertEqual(source.count("docker run --privileged --rm"), 1)

    def test_merge_identity_uses_observed_parent_and_retains_event_base(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        start = source.index("- name: Retain exact generated-merge identity")
        end = source.index("- name: Run only the focused producer", start)
        block = source[start:end]
        self.assertIn('"base_sha": revision[1]', block)
        self.assertIn(
            '"event_base_sha": os.environ["FIELDWORK_EVENT_BASE_SHA"]', block
        )
        self.assertNotIn(
            '"base_sha": os.environ["FIELDWORK_EVENT_BASE_SHA"]', block
        )
        self.assertNotIn("FIELDWORK_PR_BASE_SHA", source)
        self.assertIn('"parents": revision[1:]', block)
        self.assertIn('"head_sha": os.environ["FIELDWORK_PR_HEAD_SHA"]', block)
        self.assertIn('"event_sha": os.environ["FIELDWORK_EVENT_SHA"]', block)
        self.assertIn('"expected": "synthetic-merge-ref"', block)

    def test_workflow_receipt_gate_is_explicit_and_optimizer_safe(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        start = source.index("- name: Require focused completion")
        block = source[start:]
        self.assertNotIn("assert receipt", block)
        self.assertIn("if type(receipt) is not dict", block)
        self.assertIn("if not condition:", block)
        self.assertIn("focused receipt validation failed", block)
        self.assertIn("type(receipt.get(\"raw_status\")) is int", block)
        self.assertIn("type(receipt.get(\"named_test_count\")) is int", block)
        self.assertIn("type(receipt.get(\"later_named_tests\")) is list", block)

    def run_classify(
        self, raw_status: int, verifier_status: int
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--classify-status",
                str(raw_status),
                str(verifier_status),
            ],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

    def test_status_precedence(self) -> None:
        cases = (
            (0, 0, "0 focused-pass\n"),
            (0, 2, "2 evidence-verification-failure\n"),
            (124, 2, "77 outer-timeout-neutral\n"),
            (1, 2, "1 focused-hard-failure\n"),
            (2, 2, "2 focused-hard-failure\n"),
            (137, 2, "137 focused-hard-failure\n"),
        )
        for raw_status, verifier_status, expected in cases:
            with self.subTest(raw_status=raw_status, verifier_status=verifier_status):
                result = self.run_classify(raw_status, verifier_status)
                self.assertEqual(
                    result.returncode, 0, result.stdout + result.stderr
                )
                self.assertEqual(result.stdout, expected)
                self.assertEqual(result.stderr, "")

    def test_invalid_status_classifier_input_fails_closed(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--classify-status", "broken", "0"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)

    def run_check(
        self, parent: str, *, run_id: str = "focused-guard-control"
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["RUN_ID"] = run_id
        return subprocess.run(
            ["bash", str(SCRIPT), "--check-runtime-parent", parent],
            cwd=ROOT,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

    def test_safe_tmp_parent_is_accepted_without_creating_state(self) -> None:
        result = self.run_check("/tmp")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(
            pathlib.Path("/tmp/lf-mmdebstrap-packet-b-focused-guard-control").exists()
        )

    def test_unsafe_parent_is_rejected(self) -> None:
        result = self.run_check("/etc")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing unsafe runtime parent", result.stderr)

    def test_unsafe_run_id_is_rejected_before_runtime_selection(self) -> None:
        result = self.run_check("/tmp", run_id="../escape")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing unsafe run id", result.stderr)


if __name__ == "__main__":
    unittest.main()
