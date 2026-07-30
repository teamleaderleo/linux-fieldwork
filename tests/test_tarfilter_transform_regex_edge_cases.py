from __future__ import annotations

import pathlib
import tempfile

import test_tarfilter_transform_regex_candidate as candidate_tests


class TarfilterTransformRegexEdgeCasesTest(
    candidate_tests.TarfilterTransformRegexCandidateTest
):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.edge_patch = cls.repo / (
            "investigations/tarfilter-transform-regex-candidate/"
            "tarfilter-transform-regex-edge-cases.patch"
        )

    def prepare_candidate(
        self,
        work: pathlib.Path,
        *,
        include_regex_patch: bool,
    ) -> pathlib.Path:
        candidate = super().prepare_candidate(
            work, include_regex_patch=include_regex_patch
        )
        if include_regex_patch:
            self.apply_patch(candidate.parents[2], self.edge_patch)
        return candidate

    def test_branch_leading_basic_star_is_literal(self) -> None:
        cases = (
            ("*a", "s/*a/X/", "X"),
            ("*b", r"s/a\|*b/X/", "X"),
            ("*a", r"s/\(*a\)/X/", "X"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-basic-star-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression, expected_name in cases:
                with self.subTest(member=member_name, expression=expression):
                    self.assert_matches_gnu(
                        candidate,
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                        {expected_name: ("file", "")},
                    )

    def test_escaped_zero_is_literal_zero_in_both_dialects(self) -> None:
        cases = (
            ("0", r"s/\0/X/", "X"),
            ("x0", r"s/\0/X/", "xX"),
            ("0", r"s/\0/X/x", "X"),
            ("x0", r"s/\0/X/x", "xX"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-zero-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression, expected_name in cases:
                with self.subTest(member=member_name, expression=expression):
                    self.assert_matches_gnu(
                        candidate,
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                        {expected_name: ("file", "")},
                    )

    def test_extended_stacked_repetition_is_normalized(self) -> None:
        cases = (
            ("a", "s/a**/X/x", "X"),
            ("a", "s/a+*/X/x", "X"),
            ("a", "s/a++/X/x", "X"),
            ("a", "s/a??/X/x", "X"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-repeat-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression, expected_name in cases:
                with self.subTest(member=member_name, expression=expression):
                    self.assert_matches_gnu(
                        candidate,
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                        {expected_name: ("file", "")},
                    )

    def test_edge_patch_source_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-edge-source-") as td:
            candidate = self.prepare_candidate(
                pathlib.Path(td), include_regex_patch=True
            )
            source = candidate.read_text(encoding="utf-8")
            self.assertIn("def _normalize_extended_repetition", source)
            self.assertIn('if escaped == "0":', source)
            self.assertIn(
                'if not extended and char == "*" and branch_start:', source
            )
            self.assertIn(
                'if extended and char in "*+?" and not branch_start:', source
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
