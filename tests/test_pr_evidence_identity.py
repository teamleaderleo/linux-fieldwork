from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.audit_pr_evidence_identity import IdentityError, build_receipt, classify_identity


BASE = "1" * 40
HEAD = "2" * 40
MERGE = "3" * 40
OTHER = "4" * 40
PARENT = "5" * 40


class PullRequestEvidenceIdentityTest(unittest.TestCase):
    def receipt(self, **overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "checkout_sha": HEAD,
            "head_sha": HEAD,
            "base_sha": BASE,
            "event_sha": MERGE,
            "parents": [PARENT],
            "event_name": "pull_request",
            "ref": "refs/pull/42/merge",
            "head_ref": "feature/example",
            "base_ref": "main",
            "run_id": "100",
            "run_attempt": "1",
            "expected": "exact-head",
        }
        data.update(overrides)
        return data

    def test_exact_head_checkout(self) -> None:
        receipt = build_receipt(self.receipt())
        self.assertEqual(receipt.classification, "exact-head")
        self.assertEqual(receipt.checkout_sha, HEAD)
        self.assertEqual(receipt.head_sha, HEAD)

    def test_synthetic_merge_ref_checkout(self) -> None:
        receipt = build_receipt(
            self.receipt(
                checkout_sha=MERGE,
                event_sha=MERGE,
                parents=[BASE, HEAD],
                expected="synthetic-merge-ref",
            )
        )
        self.assertEqual(receipt.classification, "synthetic-merge-ref")
        self.assertEqual(receipt.parents, (BASE, HEAD))

    def test_unrelated_checkouts_remain_typed_other(self) -> None:
        cases = (
            self.receipt(
                checkout_sha=OTHER,
                parents=[PARENT],
                expected="other-checkout",
            ),
            self.receipt(
                checkout_sha=OTHER,
                event_sha=OTHER,
                parents=[BASE, PARENT],
                expected="other-checkout",
            ),
            self.receipt(
                checkout_sha=MERGE,
                event_sha=MERGE,
                parents=[HEAD, BASE],
                expected="other-checkout",
            ),
        )
        for data in cases:
            with self.subTest(data=data):
                self.assertEqual(build_receipt(data).classification, "other-checkout")

    def test_expected_classification_fails_on_identity_mismatch(self) -> None:
        with self.assertRaisesRegex(IdentityError, "expected exact-head"):
            build_receipt(
                self.receipt(
                    checkout_sha=MERGE,
                    event_sha=MERGE,
                    parents=[BASE, HEAD],
                )
            )

    def test_malformed_types_and_shas_fail_closed(self) -> None:
        cases = (
            self.receipt(checkout_sha=True),
            self.receipt(head_sha="A" * 40),
            self.receipt(base_sha="1" * 39),
            self.receipt(parents=True),
            self.receipt(parents=[PARENT, PARENT]),
            self.receipt(run_id=True),
            self.receipt(run_attempt="0"),
            self.receipt(head_ref=""),
        )
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises(IdentityError):
                    build_receipt(data)

    def test_checkout_cannot_be_its_own_parent(self) -> None:
        with self.assertRaisesRegex(IdentityError, "own parent"):
            classify_identity(
                checkout_sha=MERGE,
                head_sha=HEAD,
                base_sha=BASE,
                event_sha=MERGE,
                parents=[BASE, MERGE],
            )

    def test_non_pr_event_can_have_empty_branch_refs(self) -> None:
        receipt = build_receipt(
            self.receipt(
                event_name="workflow_dispatch",
                head_ref="",
                base_ref="",
            )
        )
        self.assertEqual(receipt.classification, "exact-head")

    def test_cli_output_and_optimizer_status_match(self) -> None:
        root = Path(__file__).resolve().parents[1]
        tool = root / "tools" / "audit_pr_evidence_identity.py"
        data = self.receipt(
            checkout_sha=MERGE,
            event_sha=MERGE,
            parents=[BASE, HEAD],
            expected="synthetic-merge-ref",
        )
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "input.json"
            output_path = Path(temporary) / "output.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            runs = []
            for optimized in (False, True):
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command.extend(
                    [str(tool), str(input_path), "--output", str(output_path)]
                )
                runs.append(
                    subprocess.run(
                        command,
                        cwd=root,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                )

        ordinary, optimized = runs
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
        self.assertEqual(optimized.returncode, 0, optimized.stderr)
        self.assertEqual(json.loads(ordinary.stdout), json.loads(optimized.stdout))
        payload = json.loads(ordinary.stdout)
        self.assertEqual(payload["classification"], "synthetic-merge-ref")
        self.assertEqual(payload["parents"], [BASE, HEAD])


if __name__ == "__main__":
    unittest.main()
