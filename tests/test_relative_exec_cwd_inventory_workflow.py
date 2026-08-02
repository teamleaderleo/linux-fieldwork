from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/relative-exec-cwd-inventory.yml"


class RelativeExecCwdInventoryWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_audited_trees_trigger_the_inventory(self) -> None:
        for path in (
            '      - "tools/**"',
            '      - "tests/**"',
            '      - "scripts/**"',
            '      - "investigations/**"',
            '      - "programmes/**"',
            '      - "upstream/**"',
            '      - ".github/workflows/relative-exec-cwd-inventory.yml"',
        ):
            self.assertIn(path, self.workflow)

    def test_inventory_scans_the_same_repository_roots(self) -> None:
        self.assertIn("python3 tools/relative_exec_cwd_audit.py --json", self.workflow)
        self.assertIn(
            "tools tests scripts investigations programmes upstream",
            self.workflow,
        )
        self.assertNotIn("--fail-on-findings", self.workflow)
        self.assertIn("Findings are review prompts", self.workflow)

    def test_inventory_validates_and_retains_typed_evidence(self) -> None:
        for field in (
            '"path"',
            '"line"',
            '"language"',
            '"kind"',
            '"program"',
            '"cwd"',
            '"explanation"',
        ):
            self.assertIn(field, self.workflow)
        self.assertIn("invalid finding", self.workflow)
        self.assertIn("must be an exact integer", self.workflow)
        self.assertIn("must be a string", self.workflow)
        self.assertIn("actions/upload-artifact@v4", self.workflow)
        self.assertIn("retention-days: 14", self.workflow)

    def test_pr_controlled_finding_text_is_escaped_in_summary(self) -> None:
        self.assertIn("import html", self.workflow)
        self.assertIn('stream.write("<pre>\\n")', self.workflow)
        self.assertIn("html.escape(rendered)", self.workflow)
        self.assertIn('stream.write("</pre>\\n")', self.workflow)
        self.assertNotIn('stream.write("```text\\n")', self.workflow)

    def test_inventory_is_lightweight_and_read_only(self) -> None:
        permissions = self.workflow.split("jobs:", 1)[0]
        self.assertIn("  contents: read", permissions)
        self.assertNotIn("write", permissions)
        self.assertIn("runs-on: ubuntu-24.04", self.workflow)
        self.assertNotIn("windows-latest", self.workflow)
        self.assertIn("timeout-minutes: 5", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)


if __name__ == "__main__":
    unittest.main()
