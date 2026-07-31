from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/relative-exec-cwd-audit.yml"


class RelativeExecCwdAuditReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_receipt_test_triggers_and_runs_in_dedicated_workflow(self) -> None:
        self.assertIn(
            '- "tests/test_relative_exec_cwd_audit_receipt.py"',
            self.workflow,
        )
        focused_start = self.workflow.index("      - name: Run focused regressions")
        focused_end = self.workflow.index(
            "      - name: Inventory current repository findings",
            focused_start,
        )
        focused = self.workflow[focused_start:focused_end]
        self.assertIn("tests.test_relative_exec_cwd_audit", focused)
        self.assertIn("tests.test_relative_exec_cwd_audit_receipt", focused)

    def test_downloaded_inventory_revalidates_complete_schema(self) -> None:
        start = self.workflow.index("  artifact-receipt:")
        end = self.workflow.index("  windows-receipt:", start)
        receipt = self.workflow[start:end]
        for field in (
            '"path"',
            '"line"',
            '"language"',
            '"kind"',
            '"program"',
            '"cwd"',
            '"explanation"',
        ):
            self.assertIn(field, receipt)
        self.assertIn("invalid downloaded finding", receipt)
        self.assertIn("must be an exact integer", receipt)
        self.assertIn("must be a string", receipt)

    def test_windows_receipt_uses_explicit_schema_and_identity_validation(self) -> None:
        start = self.workflow.index("  windows-receipt:")
        receipt = self.workflow[start:]
        self.assertNotIn("assert summary", receipt)
        self.assertIn("invalid Windows evidence schema", receipt)
        self.assertIn(
            'if type(summary.get("schema_version")) is not int:',
            receipt,
        )
        self.assertIn("unsupported schema_version", receipt)
        self.assertIn("nullable_strings", receipt)
        self.assertIn("ntpath.normcase", receipt)
        self.assertIn("ntpath.normpath", receipt)
        self.assertIn("absolute-path control identity differs", receipt)

    def test_receipt_remains_read_only(self) -> None:
        permissions = self.workflow.split("jobs:", 1)[0]
        self.assertIn("  actions: read", permissions)
        self.assertIn("  contents: read", permissions)
        self.assertNotIn("write", permissions)


if __name__ == "__main__":
    unittest.main()
