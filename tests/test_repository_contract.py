from __future__ import annotations

import pathlib
import re
import unittest


class RepositoryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]

    def read(self, relative: str) -> str:
        return (self.repo / relative).read_text(encoding="utf-8")

    def test_entry_documents_link_agent_contract(self) -> None:
        self.assertIn("[`AGENTS.md`](AGENTS.md)", self.read("README.md"))
        self.assertIn("[`AGENTS.md`](AGENTS.md)", self.read("START_HERE.md"))

    def test_agent_contract_requires_core_work_products(self) -> None:
        contract = self.read("AGENTS.md")
        required_phrases = (
            "Search open and closed issues and pull requests",
            "Read the relevant imported source and nearby tests",
            "negative control",
            "Durable notes are part of the work",
            "Self-review contract",
            "Peer-review contract",
            "Guard every caller-controlled path",
            "No issue, email, merge request, patch submission, comment, review",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, contract)

    def test_investigation_template_has_completion_fields(self) -> None:
        template = self.read("templates/investigation.md")
        required_headings = (
            "## Existing work and duplicate search",
            "## Source and test map",
            "## Assertions and negative control",
            "## Cleanup and rerun",
            "## Self-review",
            "## Peer review",
            "## Reusable notes",
            "## Authority",
        )
        for heading in required_headings:
            with self.subTest(heading=heading):
                self.assertIn(heading, template)

    def test_note_template_has_provenance_and_validation(self) -> None:
        template = self.read("templates/note.md")
        self.assertIn("## Source and provenance", template)
        self.assertIn("## Validation", template)
        self.assertIn("Related issues or pull requests", template)

    def test_local_markdown_links_from_contract_documents_exist(self) -> None:
        for relative in (
            "AGENTS.md",
            "README.md",
            "START_HERE.md",
            "templates/investigation.md",
            "templates/note.md",
        ):
            text = self.read(relative)
            base = (self.repo / relative).parent
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                path = (base / target.split("#", 1)[0]).resolve()
                with self.subTest(document=relative, target=target):
                    self.assertTrue(path.exists(), f"missing local link target: {target}")


if __name__ == "__main__":
    unittest.main()
