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

    def test_repeated_simple_quantifiers_match_gnu_nested_semantics(self) -> None:
        cases = (
            ("a", "s/a**/X/x", "X"),
            ("0", "s/a+*/X/x", "X0"),
            ("0", "s/a*+/X/x", "X0"),
            ("aa", "s/a++/X/x", "X"),
            ("b", "s/a+?/X/x", "Xb"),
            ("b", r"s/a\?\+/X/", "Xb"),
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

    def test_repeated_intervals_remain_nested_in_both_dialects(self) -> None:
        cases = (
            ("aaaaa", "s/a{2}{2,3}/X/x", "Xa"),
            ("aaa", "s/a{1,2}+/X/x", "X"),
            ("aaa", "s/a+{1,2}/X/x", "X"),
            ("b", "s/a{1,2}*/X/x", "Xb"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-interval-") as td:
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

    def test_consecutive_basic_intervals_are_rejected_like_gnu(self) -> None:
        expression = r"s/a\{2\}\{2,3\}/X/"
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-basic-interval-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            filtered = self.run_filter(candidate, "aaaaa", expression)
            reference = self.run_gnu(work / "reference", "aaaaa", expression)
            self.assertNotEqual(filtered.returncode, 0)
            self.assertEqual(filtered.stdout, b"")
            self.assertNotEqual(reference.returncode, 0)

    def test_python_only_extended_groups_are_rejected_like_gnu(self) -> None:
        cases = (
            ("ab", "s/a(?=b)/X/x"),
            ("a", "s/(?:a)/X/x"),
            ("A", "s/(?i)a/X/x"),
            ("a", "s/(?P<n>a)/X/x"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-python-groups-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression in cases:
                with self.subTest(member=member_name, expression=expression):
                    filtered = self.run_filter(candidate, member_name, expression)
                    reference = self.run_gnu(
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                    )
                    self.assertNotEqual(filtered.returncode, 0)
                    self.assertEqual(filtered.stdout, b"")
                    self.assertIn(
                        "unsupported extended-regex group extension",
                        filtered.stderr.decode("utf-8", "replace"),
                    )
                    self.assertNotEqual(reference.returncode, 0)

    def test_edge_patch_source_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-edge-source-") as td:
            candidate = self.prepare_candidate(
                pathlib.Path(td), include_regex_patch=True
            )
            source = candidate.read_text(encoding="utf-8")
            self.assertIn("def _quantifier_at", source)
            self.assertIn("def _normalize_repeated_quantifiers", source)
            self.assertIn('if escaped == "0":', source)
            self.assertIn(
                'if not extended and char == "*" and branch_start:', source
            )
            self.assertIn(
                'raise ValueError("unsupported extended-regex group extension")',
                source,
            )
            self.assertIn(
                'return _normalize_repeated_quantifiers("".join(result), extended)',
                source,
            )
            self.assertIn('result[atom_start:] = ["(?:" + nested + ")"]', source)
            self.assertIn(
                'raise ValueError("consecutive basic-regex intervals are invalid")',
                source,
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
