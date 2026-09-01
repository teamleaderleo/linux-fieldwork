from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/systemd-bind-path-source-compare.yml"


class SystemdBindPathSourceCompareWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_meson_setup_names_build_and_source_directories(self) -> None:
        self.assertIn("test -f systemd/meson.build", self.workflow)
        self.assertIn("meson setup systemd/build systemd", self.workflow)
        self.assertNotIn("meson setup systemd/build \\\n", self.workflow)

    def test_exact_variants_remain_pinned(self) -> None:
        self.assertIn("63e35ca3f99566095c84248e9eb41a3a6b32f2eb", self.workflow)
        self.assertIn("d32993d1f67ec1b42719c89eeda9425042df57ce", self.workflow)

    def test_comparison_remains_read_only_and_credential_free(self) -> None:
        permissions = self.workflow.split("jobs:", 1)[0]
        self.assertIn("  contents: read", permissions)
        self.assertNotIn("write", permissions)
        self.assertEqual(self.workflow.count("persist-credentials: false"), 2)

    def test_evidence_upload_survives_earlier_failure(self) -> None:
        self.assertIn("if: always()", self.workflow)
        self.assertIn("meson-setup.log", self.workflow)
        self.assertIn("retention-days: 30", self.workflow)


if __name__ == "__main__":
    unittest.main()
