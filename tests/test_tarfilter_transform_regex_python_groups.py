from __future__ import annotations

import pathlib
import tempfile

import test_tarfilter_transform_regex_edge_cases as edge_tests


class TarfilterTransformRegexPythonGroupsTest(
    edge_tests.TarfilterTransformRegexEdgeCasesTest
):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.python_group_patch = cls.repo / (
            "investigations/tarfilter-transform-regex-candidate/"
            "tarfilter-transform-regex-python-groups.patch"
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
            self.apply_patch(candidate.parents[2], self.python_group_patch)
        return candidate

    def test_python_group_extensions_are_rejected_like_gnu(self) -> None:
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
            for index, (member_name, expression) in enumerate(cases):
                with self.subTest(member=member_name, expression=expression):
                    filtered = self.run_filter(candidate, member_name, expression)
                    reference = self.run_gnu(
                        work / f"reference-{index}", member_name, expression
                    )
                    self.assertNotEqual(filtered.returncode, 0)
                    self.assertEqual(filtered.stdout, b"")
                    self.assertIn(
                        "unsupported extended-regex group extension",
                        filtered.stderr.decode("utf-8", "replace"),
                    )
                    self.assertNotEqual(reference.returncode, 0)

    def test_escaped_parenthesis_and_bracket_content_remain_ordinary_ere(self) -> None:
        cases = (
            ("(", r"s/\(?/X/x", "X"),
            ("(", r"s/[(?]/X/x", "X"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-python-controls-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for index, (member_name, expression, expected_name) in enumerate(cases):
                with self.subTest(member=member_name, expression=expression):
                    self.assert_matches_gnu(
                        candidate,
                        work / f"reference-{index}",
                        member_name,
                        expression,
                        {expected_name: ("file", "")},
                    )

    def test_python_group_patch_source_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-python-source-") as td:
            candidate = self.prepare_candidate(
                pathlib.Path(td), include_regex_patch=True
            )
            source = candidate.read_text(encoding="utf-8")
            self.assertIn('and pattern[index + 1] == "?"', source)
            self.assertIn(
                'raise ValueError("unsupported extended-regex group extension")',
                source,
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
