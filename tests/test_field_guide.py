from __future__ import annotations

import pathlib
import unittest


class FieldGuideTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.guide = (cls.repo / "FIELD_GUIDE.md").read_text(encoding="utf-8")
        cls.readme = (cls.repo / "README.md").read_text(encoding="utf-8")
        cls.start_here = (cls.repo / "START_HERE.md").read_text(encoding="utf-8")
        cls.coordination = (
            cls.repo / "ADAPTIVE_COORDINATION.md"
        ).read_text(encoding="utf-8")
        cls.upstream_template = (
            cls.repo / "templates/upstream-packet.md"
        ).read_text(encoding="utf-8")

    def test_entry_documents_link_the_field_guide(self) -> None:
        link = "[`FIELD_GUIDE.md`](FIELD_GUIDE.md)"
        self.assertIn(link, self.readme)
        self.assertIn(link, self.start_here)

    def test_guide_contains_required_review_surfaces(self) -> None:
        required = (
            "## Do",
            "## Do not",
            "## Relationship to the working rules",
            "## 🍩 Donuts",
            "## Areas that have been fruitful",
            "## Things to keep in mind during review",
            "## Investigation selection heuristic",
            "exact reviewed head",
            "negative control",
            "permissions",
            "cleanup",
            "first failure",
            "upstream contact",
            "TL;DR",
            "Explain like I'm five",
            "Why care",
            "[`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md)",
        )
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, self.guide)

    def test_donuts_name_recurring_incomplete_boundaries(self) -> None:
        expected_donuts = (
            "Atomic but inaccessible",
            "Guarded but unresolved",
            "Sanitized but broken",
            "Green but unexecuted",
            "Correct label, wrong event",
            "Equal components, unequal target",
            "Correct cache, damaged first client",
            "One source gate bypassed, another remains",
            "Correct sparse bytes, stale sparse metadata",
            "Signal observed, success still reported",
        )
        for donut in expected_donuts:
            with self.subTest(donut=donut):
                self.assertIn(donut, self.guide)

    def test_release_desk_uses_one_comment_card_per_live_unit(self) -> None:
        required = (
            "## Use comment cards for live release work",
            "one stable front-door issue",
            "one top-level comment",
            "edits that unit's comment in place",
            "The set of live card comments is the board",
            "remove the live card",
            "ARCHIVED",
            "Exact head:",
            "External-contact state:",
        )
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, self.coordination)

    def test_upstream_packet_template_has_reader_and_release_fields(self) -> None:
        required = (
            "State: `INTERNAL DRAFT`",
            "## TL;DR",
            "## Explain like I'm five",
            "## Why care",
            "## Issue draft",
            "## Pull-request draft",
            "## Review passes",
            "External contact authorized: `false`",
        )
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, self.upstream_template)


if __name__ == "__main__":
    unittest.main()
