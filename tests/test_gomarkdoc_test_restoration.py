from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "investigations/gomarkdoc-test-restoration/run_matrix.py"
SPEC = importlib.util.spec_from_file_location("gomarkdoc_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MATRIX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATRIX)


def cases(*passing: str) -> dict[str, dict[str, object]]:
    selected = set(passing)
    return {
        mode: {"exit_status": 0 if mode in selected else 1}
        for mode in MATRIX.MODES
    }


def record(label: str, mode: str, status: int, *, timed_out: bool = False) -> dict[str, object]:
    return {
        "revision_label": label,
        "mode": mode,
        "exit_status": status,
        "timed_out": timed_out,
    }


class GomarkdocMatrixTest(unittest.TestCase):
    def test_revision_classification(self) -> None:
        examples = {
            "baseline": (
                cases("baseline"),
                "suite-passes-unchanged",
            ),
            "flags": (
                cases("unset-goflags", "filter-goflags"),
                "test-time-goflags-is-sufficient",
            ),
            "fixture": (
                cases("add-fixture"),
                "missing-fixture-is-sufficient",
            ),
            "either": (
                cases("unset-goflags", "add-fixture"),
                "either-narrow-repair-is-sufficient",
            ),
            "combined": (
                cases("add-fixture-unset-goflags"),
                "fixture-and-test-flags-interact",
            ),
            "unresolved": (
                cases(),
                "no-tested-repair-restores-suite",
            ),
        }
        for name, (matrix, expected) in examples.items():
            with self.subTest(name=name):
                self.assertEqual(MATRIX.classify_revision(matrix), expected)

    def test_symptoms_are_counted_separately_from_status(self) -> None:
        log = """
flag provided but not defined: -mod
flag provided but not defined: -other
open ../.gomarkdoc-empty.yml: no such file or directory
FAIL  github.com/princjef/gomarkdoc/cmd/gomarkdoc
"""
        symptoms = MATRIX.symptom_counts(log)
        self.assertEqual(symptoms["unsupported_mod_flag"], 1)
        self.assertEqual(symptoms["unsupported_other_flag"], 1)
        self.assertEqual(symptoms["missing_empty_config"], 1)
        self.assertEqual(symptoms["gomarkdoc_package_fail"], 1)

    def test_summary_requires_reported_good_and_bad_controls(self) -> None:
        revisions = {
            "known-good": "good",
            "known-bad": "bad",
            "current": "current",
        }
        records = []
        for label in revisions:
            for mode in MATRIX.MODES:
                status = 1
                if label == "known-good":
                    status = 0
                if label == "current" and mode == "unset-goflags":
                    status = 0
                records.append(record(label, mode, status))

        summary = MATRIX.build_summary(records, revisions)
        self.assertTrue(summary["valid_reproduction"])
        self.assertEqual(
            summary["current_decision"], "test-time-goflags-is-sufficient"
        )

        records[0]["exit_status"] = 1
        invalid = MATRIX.build_summary(records, revisions)
        self.assertFalse(invalid["valid_reproduction"])
        self.assertFalse(invalid["controls"]["known_good_baseline_passed"])

    def test_timeout_invalidates_reproduction(self) -> None:
        revisions = {
            "known-good": "good",
            "known-bad": "bad",
            "current": "current",
        }
        records = []
        for label in revisions:
            for mode in MATRIX.MODES:
                status = 0 if label == "known-good" else 1
                records.append(record(label, mode, status))
        records[-1]["timed_out"] = True
        summary = MATRIX.build_summary(records, revisions)
        self.assertFalse(summary["valid_reproduction"])
        self.assertFalse(summary["controls"]["no_case_timed_out"])


if __name__ == "__main__":
    unittest.main()
