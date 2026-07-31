from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/linux-fieldwork-ci.yml"
REPRODUCTION_SCRIPT = REPOSITORY_ROOT / "scripts/reproduce-mmdebstrap-autopkgtest.sh"


class MmdebstrapSidCheckoutIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.script = REPRODUCTION_SCRIPT.read_text(encoding="utf-8")

    def make_non_root_environment(
        self,
        root: pathlib.Path,
        *,
        checkout_line: str | None = None,
        base_sha: str | None = None,
        head_sha: str | None = None,
        event_sha: str | None = None,
    ) -> tuple[dict[str, str], pathlib.Path]:
        fake_bin = root / "bin"
        fake_bin.mkdir()
        fake_id = fake_bin / "id"
        fake_id.write_text("#!/bin/sh\nprintf '1000\\n'\n", encoding="utf-8")
        fake_id.chmod(0o755)

        run_dir = root / "run"
        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        environment["RUN_DIR"] = str(run_dir)
        if checkout_line is not None:
            environment.update(
                {
                    "FIELDWORK_CHECKOUT_REV_LINE": checkout_line,
                    "FIELDWORK_EVENT_NAME": "pull_request",
                    "FIELDWORK_EVENT_SHA": event_sha or "c" * 40,
                    "FIELDWORK_PR_HEAD_SHA": head_sha or "b" * 40,
                    "FIELDWORK_PR_BASE_SHA": base_sha or "a" * 40,
                    "FIELDWORK_REF": "refs/pull/361/merge",
                    "FIELDWORK_HEAD_REF": "repair/361-sid-checkout-identity",
                    "FIELDWORK_BASE_REF": "investigation/mmdebstrap-autopkgtest-current-main-v2",
                    "FIELDWORK_RUN_ID": "123456",
                    "FIELDWORK_RUN_ATTEMPT": "1",
                    "FIELDWORK_EXPECTED_CHECKOUT_CLASSIFICATION": "synthetic-merge-ref",
                }
            )
        return environment, run_dir

    def run_early_preflight(
        self,
        environment: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(REPRODUCTION_SCRIPT)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_workflow_transfers_generated_merge_identity_into_container(self) -> None:
        self.assertIn("fetch-depth: 2", self.workflow)
        self.assertIn(
            "checkout_rev_line=$(git rev-list --parents -n 1 HEAD)",
            self.workflow,
        )
        self.assertIn(
            "FIELDWORK_EXPECTED_CHECKOUT_CLASSIFICATION: synthetic-merge-ref",
            self.workflow,
        )
        for name in (
            "FIELDWORK_CHECKOUT_REV_LINE",
            "FIELDWORK_EVENT_NAME",
            "FIELDWORK_EVENT_SHA",
            "FIELDWORK_PR_HEAD_SHA",
            "FIELDWORK_PR_BASE_SHA",
            "FIELDWORK_REF",
            "FIELDWORK_HEAD_REF",
            "FIELDWORK_BASE_REF",
            "FIELDWORK_RUN_ID",
            "FIELDWORK_RUN_ATTEMPT",
            "FIELDWORK_EXPECTED_CHECKOUT_CLASSIFICATION",
        ):
            with self.subTest(name=name):
                self.assertIn(f"--env {name}", self.workflow)

    def test_expected_generated_merge_is_retained_before_root_preflight(self) -> None:
        checkout = "c" * 40
        base = "a" * 40
        head = "b" * 40
        with tempfile.TemporaryDirectory(prefix="sid-checkout-identity-") as temporary:
            environment, run_dir = self.make_non_root_environment(
                pathlib.Path(temporary),
                checkout_line=f"{checkout} {base} {head}",
                base_sha=base,
                head_sha=head,
                event_sha=checkout,
            )
            completed = self.run_early_preflight(environment)

            self.assertEqual(completed.returncode, 77, completed.stderr)
            receipt = json.loads(
                (run_dir / "repository-identity.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["classification"], "synthetic-merge-ref")
            self.assertEqual(receipt["checkout_sha"], checkout)
            self.assertEqual(receipt["parents"], [base, head])
            self.assertEqual(
                (run_dir / "repository-rev-list.txt").read_text(encoding="utf-8"),
                f"{checkout} {base} {head}\n",
            )
            self.assertEqual(
                (run_dir / "repository-identity-classification.txt").read_text(
                    encoding="utf-8"
                ),
                "synthetic-merge-ref\n",
            )
            result = (run_dir / "result.md").read_text(encoding="utf-8")
            self.assertIn(
                "Repository checkout classification: `synthetic-merge-ref`",
                result,
            )
            self.assertNotIn(
                "Repository identity receipt SHA-256: `unavailable`",
                result,
            )
            self.assertIn("reproduction requires root", result)

    def test_reversed_merge_parents_fail_before_root_preflight(self) -> None:
        checkout = "c" * 40
        base = "a" * 40
        head = "b" * 40
        with tempfile.TemporaryDirectory(prefix="sid-checkout-reversed-") as temporary:
            environment, run_dir = self.make_non_root_environment(
                pathlib.Path(temporary),
                checkout_line=f"{checkout} {head} {base}",
                base_sha=base,
                head_sha=head,
                event_sha=checkout,
            )
            completed = self.run_early_preflight(environment)

            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertFalse((run_dir / "repository-identity.json").exists())
            self.assertTrue((run_dir / "repository-identity-input.json").is_file())
            identity_error = (run_dir / "repository-identity.stderr").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                "expected synthetic-merge-ref, observed other-checkout",
                identity_error,
            )
            self.assertEqual(
                (run_dir / "preflight-error.txt").read_text(encoding="utf-8"),
                "repository checkout identity receipt failed\n",
            )
            self.assertNotIn("reproduction requires root", completed.stderr)

    def test_local_preflight_records_non_pr_identity_without_false_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sid-checkout-local-") as temporary:
            environment, run_dir = self.make_non_root_environment(
                pathlib.Path(temporary)
            )
            for name in tuple(environment):
                if name.startswith("FIELDWORK_"):
                    environment.pop(name)
            completed = self.run_early_preflight(environment)

            self.assertEqual(completed.returncode, 77, completed.stderr)
            identity = (run_dir / "repository-identity.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("classification=not-a-pull-request", identity)
            self.assertFalse((run_dir / "repository-identity.json").exists())
            result = (run_dir / "result.md").read_text(encoding="utf-8")
            self.assertIn(
                "Repository checkout classification: `not-a-pull-request`",
                result,
            )


if __name__ == "__main__":
    unittest.main()
