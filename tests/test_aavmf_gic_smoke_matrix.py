from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "investigations/aavmf-gic-smoke-matrix/run_matrix.py"
SPEC = importlib.util.spec_from_file_location("aavmf_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MATRIX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATRIX)


def case(label: str, mode: str, passed: bool) -> dict[str, object]:
    return {
        "revision_label": label,
        "gic_mode": mode,
        "passed": passed,
        "infrastructure_timeout": False,
    }


def build(label: str, status: int = 0) -> dict[str, object]:
    return {
        "revision_label": label,
        "exit_status": status,
        "infrastructure_timeout": False,
    }


class AavmfGicMatrixTest(unittest.TestCase):
    def test_classification(self) -> None:
        examples = {
            "all": (
                {mode: {"passed": True} for mode in MATRIX.MODES},
                "all-gic-modes-reach-systemd-boot",
            ),
            "max": (
                {
                    "default": {"passed": True},
                    "2": {"passed": True},
                    "3": {"passed": True},
                    "max": {"passed": False},
                },
                "max-only-fails",
            ),
            "v3": (
                {
                    "default": {"passed": True},
                    "2": {"passed": True},
                    "3": {"passed": False},
                    "max": {"passed": False},
                },
                "gicv3-and-max-fail",
            ),
            "default": (
                {mode: {"passed": False} for mode in MATRIX.MODES},
                "default-mode-does-not-reach-systemd-boot",
            ),
        }
        for name, (records, expected) in examples.items():
            with self.subTest(name=name):
                self.assertEqual(MATRIX.classify(records), expected)

    def test_valid_tcg_boundary_is_separate_from_environment_control(self) -> None:
        revisions = dict(MATRIX.DEFAULT_REVISIONS)
        builds = [build(label) for label in revisions]
        cases = []
        for label in revisions:
            for mode in MATRIX.MODES:
                passed = True
                if label == "known-bad" and mode == "max":
                    passed = False
                cases.append(case(label, mode, passed))

        summary = MATRIX.build_summary(
            builds,
            cases,
            revisions,
            MATRIX.DEFAULT_QEMU_REVISION,
        )
        self.assertTrue(summary["valid_environment"])
        self.assertTrue(summary["tcg_reproduces_reported_boundary"])
        self.assertEqual(summary["classifications"]["known-bad"], "max-only-fails")

    def test_all_tcg_modes_pass_is_valid_negative_reproduction(self) -> None:
        revisions = dict(MATRIX.DEFAULT_REVISIONS)
        builds = [build(label) for label in revisions]
        cases = [
            case(label, mode, True)
            for label in revisions
            for mode in MATRIX.MODES
        ]
        summary = MATRIX.build_summary(
            builds,
            cases,
            revisions,
            MATRIX.DEFAULT_QEMU_REVISION,
        )
        self.assertTrue(summary["valid_environment"])
        self.assertFalse(summary["tcg_reproduces_reported_boundary"])
        self.assertEqual(
            summary["current_decision"],
            "all-gic-modes-reach-systemd-boot",
        )

    def test_build_failure_is_retained_as_capability_result(self) -> None:
        revisions = dict(MATRIX.DEFAULT_REVISIONS)
        builds = [
            build("known-good", status=1),
            build("known-bad", status=1),
            build("current", status=1),
        ]
        summary = MATRIX.build_summary(
            builds,
            [],
            revisions,
            MATRIX.DEFAULT_QEMU_REVISION,
        )
        self.assertFalse(summary["valid_environment"])
        self.assertFalse(summary["controls"]["all_builds_succeeded"])
        self.assertEqual(
            summary["classifications"],
            {
                "known-good": "case-app-build-failed",
                "known-bad": "case-app-build-failed",
                "current": "case-app-build-failed",
            },
        )

    def test_infrastructure_timeout_invalidates_environment(self) -> None:
        revisions = dict(MATRIX.DEFAULT_REVISIONS)
        builds = [build(label) for label in revisions]
        cases = [
            case(label, mode, True)
            for label in revisions
            for mode in MATRIX.MODES
        ]
        cases[-1]["infrastructure_timeout"] = True
        summary = MATRIX.build_summary(
            builds,
            cases,
            revisions,
            MATRIX.DEFAULT_QEMU_REVISION,
        )
        self.assertFalse(summary["valid_environment"])
        self.assertFalse(summary["controls"]["no_infrastructure_timeout"])


if __name__ == "__main__":
    unittest.main()
