from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/relative-exec-cwd-audit.yml"


class RelativeExecCwdAuditReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_windows_receipt_uses_explicit_validation(self) -> None:
        start = self.workflow.index("  windows-receipt:")
        receipt = self.workflow[start:]
        self.assertNotIn("assert summary", receipt)
        self.assertIn(
            'if type(summary.get("schema_version")) is not int:',
            receipt,
        )
        self.assertIn("unsupported schema_version", receipt)
        self.assertIn(
            'if summary.get("absolute_identity") '
            '!= summary.get("repository_candidate"):',
            receipt,
        )
        self.assertIn("absolute-path control identity differs", receipt)

    def test_receipt_remains_read_only(self) -> None:
        permissions = self.workflow.split("jobs:", 1)[0]
        self.assertIn("  actions: read", permissions)
        self.assertIn("  contents: read", permissions)
        self.assertNotIn("write", permissions)


if __name__ == "__main__":
    unittest.main()
