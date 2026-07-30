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

    def test_entry_documents_link_the_field_guide(self) -> None:
        link = "[`FIELD_GUIDE.md`](FIELD_GUIDE.md)"
        self.assertIn(link, self.readme)
        self.assertIn(link, self.start_here)

    def test_guide_contains_required_review_surfaces(self) -> None:
        required = (
            "## Do",
            "## Do not",
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


if __name__ == "__main__":
    unittest.main()
