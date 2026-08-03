from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/kmod-modprobe-config-path.yml"


class KmodModprobeConfigWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_source_and_compiler_matrix_remain(self) -> None:
        self.assertIn("5086df53090b2fe9fa1c31351c05a78a12a4ba71", self.workflow)
        self.assertIn("compiler: [gcc, clang]", self.workflow)
        self.assertIn("-Db_sanitize=address,undefined", self.workflow)

    def test_unavailable_mbedtls_backend_is_explicitly_disabled(self) -> None:
        self.assertIn("-Dmbedtls=disabled", self.workflow)
        self.assertNotIn("libmbedtls-dev", self.workflow)
        self.assertIn("libssl-dev", self.workflow)
        self.assertIn("-Dopenssl=enabled", self.workflow)

    def test_proposed_code_has_no_persisted_checkout_credentials(self) -> None:
        self.assertEqual(self.workflow.count("persist-credentials: false"), 2)
        permissions = self.workflow.split("jobs:", 1)[0]
        self.assertIn("  contents: read", permissions)
        self.assertNotIn("write", permissions)

    def test_failure_artifact_keeps_source_configure_and_build_receipts(self) -> None:
        for receipt in (
            "source-head.txt",
            "source-modprobe-blob.txt",
            "source-status.txt",
            "toolchain.txt",
            "meson-setup.log",
            "build.log",
            "final-source-status.txt",
        ):
            self.assertIn(receipt, self.workflow)
        self.assertIn("if: always()", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)
        self.assertIn("retention-days: 30", self.workflow)

    def test_discriminator_and_rerun_contract_remain(self) -> None:
        self.assertEqual(
            self.workflow.count(
                "python3 investigations/kmod-modprobe-options-config-path/"
                "test_modprobe_options_config_path.py"
            ),
            2,
        )
        self.assertIn('cmp "$out/first.json" "$out/rerun.json"', self.workflow)
        self.assertIn('("spaced nested marker count", spaced["nested"]["marker_count"], 0)', self.workflow)

    def test_result_verifier_uses_explicit_failures(self) -> None:
        self.assertNotIn("          assert ", self.workflow)
        self.assertIn("for label, observed, expected in checks:", self.workflow)
        self.assertIn("raise SystemExit(", self.workflow)
        self.assertIn("expected {expected!r}, observed {observed!r}", self.workflow)


if __name__ == "__main__":
    unittest.main()
