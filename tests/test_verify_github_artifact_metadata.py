from __future__ import annotations

import pathlib
import unittest

from tools.verify_github_artifact_metadata import (
    ArtifactMetadataError,
    verify_metadata,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/mmdebstrap-autopkgtest-artifact-receipt.yml"
ARTIFACT_ID = "8799126060"
ARTIFACT_NAME = "mmdebstrap-reproduction-gha-30641621084-1"
RUN_ID = "30641621084"
DIGEST = "sha256:" + "a" * 64


def metadata() -> dict[str, object]:
    return {
        "id": int(ARTIFACT_ID),
        "name": ARTIFACT_NAME,
        "expired": False,
        "digest": DIGEST,
        "workflow_run": {"id": int(RUN_ID)},
    }


class VerifyGithubArtifactMetadataTest(unittest.TestCase):
    def verify(self, payload: object) -> dict[str, object]:
        return verify_metadata(
            payload,
            expected_id=ARTIFACT_ID,
            expected_name=ARTIFACT_NAME,
            expected_run_id=RUN_ID,
            expected_digest=DIGEST,
        )

    def test_exact_metadata_produces_typed_receipt(self) -> None:
        receipt = self.verify(metadata())
        self.assertEqual(receipt["schema_version"], 1)
        self.assertIs(receipt["verified"], True)
        self.assertEqual(
            receipt["artifact"],
            {
                "id": int(ARTIFACT_ID),
                "name": ARTIFACT_NAME,
                "digest": DIGEST,
                "expired": False,
                "workflow_run_id": int(RUN_ID),
            },
        )

    def test_wrong_identity_fields_fail_closed(self) -> None:
        cases = (
            ("id", int(ARTIFACT_ID) + 1, "artifact id mismatch"),
            ("name", ARTIFACT_NAME + "-other", "artifact name mismatch"),
            ("digest", "sha256:" + "b" * 64, "artifact digest mismatch"),
            ("expired", True, "artifact is expired"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                payload = metadata()
                payload[field] = value
                with self.assertRaisesRegex(ArtifactMetadataError, message):
                    self.verify(payload)

    def test_wrong_workflow_run_fails_closed(self) -> None:
        payload = metadata()
        payload["workflow_run"] = {"id": int(RUN_ID) + 1}
        with self.assertRaisesRegex(
            ArtifactMetadataError, "artifact workflow run mismatch"
        ):
            self.verify(payload)

    def test_missing_or_wrong_types_fail_closed(self) -> None:
        cases = (
            ({}, "artifact id must be a positive integer"),
            ({**metadata(), "id": True}, "artifact id must be a positive integer"),
            ({**metadata(), "expired": "false"}, "expired must be a boolean"),
            ({**metadata(), "workflow_run": []}, "workflow_run must be an object"),
            (
                {**metadata(), "workflow_run": {"id": 0}},
                "workflow run id must be a positive integer",
            ),
        )
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ArtifactMetadataError, message):
                    self.verify(payload)

    def test_invalid_expected_values_fail_before_comparison(self) -> None:
        payload = metadata()
        with self.assertRaisesRegex(ArtifactMetadataError, "expected_id"):
            verify_metadata(
                payload,
                expected_id="0",
                expected_name=ARTIFACT_NAME,
                expected_run_id=RUN_ID,
                expected_digest=DIGEST,
            )
        with self.assertRaisesRegex(ArtifactMetadataError, "expected_digest"):
            verify_metadata(
                payload,
                expected_id=ARTIFACT_ID,
                expected_name=ARTIFACT_NAME,
                expected_run_id=RUN_ID,
                expected_digest="not-a-digest",
            )

    def test_workflow_verifies_then_downloads_exact_id_and_retains_receipts(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        verify_index = source.index("- name: Verify exact source artifact metadata")
        download_index = source.index("- name: Download exact retained source artifact")
        summarize_index = source.index("- name: Build typed artifact receipt")
        self.assertLess(verify_index, download_index)
        self.assertLess(download_index, summarize_index)

        download_block = source[download_index:summarize_index]
        self.assertIn(
            "artifact-ids: ${{ env.SOURCE_ARTIFACT_ID }}", download_block
        )
        self.assertNotIn(
            "name: ${{ env.SOURCE_ARTIFACT_NAME }}", download_block
        )

        required = (
            "actions/artifacts/$SOURCE_ARTIFACT_ID",
            "tools/verify_github_artifact_metadata.py",
            '--expected-id "$SOURCE_ARTIFACT_ID"',
            '--expected-name "$SOURCE_ARTIFACT_NAME"',
            '--expected-run-id "$SOURCE_RUN_ID"',
            '--expected-digest "$SOURCE_ARTIFACT_DIGEST"',
            "source-artifact-metadata.json",
            "source-artifact-metadata-receipt.json",
            "derived receipt artifact id contradicts verified metadata",
            "derived receipt digest contradicts verified metadata",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, source)


if __name__ == "__main__":
    unittest.main()
