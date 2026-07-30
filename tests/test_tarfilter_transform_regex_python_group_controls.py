from __future__ import annotations

import pathlib
import tempfile

import test_tarfilter_transform_regex_edge_cases as edge_tests


class TarfilterTransformRegexPythonGroupControlsTest(
    edge_tests.TarfilterTransformRegexEdgeCasesTest
):
    def test_group_extension_guard_preserves_escaped_and_bracket_forms(self) -> None:
        cases = (
            ("(", r"s/\(?/X/x", "X"),
            ("(", r"s/[(?]/X/x", "X"),
            ("(", r"s/\(/X/x", "X"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-group-controls-") as td:
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


if __name__ == "__main__":
    import unittest

    unittest.main()
