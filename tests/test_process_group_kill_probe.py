from __future__ import annotations

import signal
import unittest

from tools.probe_process_group_kill import (
    CaseResult,
    ProbeError,
    classify,
    command_cases,
    run_case,
    run_probe,
)


class ProcessGroupKillProbeTest(unittest.TestCase):
    def test_classifier_distinguishes_rejection_owner_group_and_overbroad(self) -> None:
        cases = (
            (
                {
                    "parent_signal": None,
                    "child_signal": None,
                    "unrelated_signal": None,
                    "returncode": 1,
                    "stderr": "Usage: kill [options] <pid> [...]",
                },
                "parser-or-target-rejection",
            ),
            (
                {
                    "parent_signal": signal.SIGINT,
                    "child_signal": None,
                    "unrelated_signal": None,
                    "returncode": 0,
                    "stderr": "",
                },
                "owner-only-delivery",
            ),
            (
                {
                    "parent_signal": signal.SIGINT,
                    "child_signal": signal.SIGINT,
                    "unrelated_signal": None,
                    "returncode": 0,
                    "stderr": "",
                },
                "whole-group-delivery",
            ),
            (
                {
                    "parent_signal": signal.SIGINT,
                    "child_signal": signal.SIGINT,
                    "unrelated_signal": signal.SIGINT,
                    "returncode": 0,
                    "stderr": "",
                },
                "overbroad-delivery",
            ),
        )
        for arguments, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify(**arguments), expected)

    def test_command_inventory_keeps_observed_and_candidate_spellings(self) -> None:
        inventory = dict(command_cases())
        self.assertEqual(
            set(inventory),
            {
                "owner-only-external",
                "external-long",
                "external-short",
                "external-compact",
                "dash-builtin-short",
            },
        )
        parent = 1234
        pgid = 5678
        self.assertEqual(
            tuple(inventory["external-long"](parent, pgid)),
            ("/bin/kill", "--signal", "INT", "--", "-5678"),
        )
        self.assertEqual(
            tuple(inventory["external-short"](parent, pgid)),
            ("/bin/kill", "-s", "INT", "--", "-5678"),
        )
        self.assertEqual(
            tuple(inventory["dash-builtin-short"](parent, pgid)),
            (
                "/bin/dash",
                "-c",
                'kill -s INT -- "$1"',
                "dash",
                "-5678",
            ),
        )

    def test_owner_only_and_whole_group_controls_rerun_cleanly(self) -> None:
        owner_builder = dict(command_cases())["owner-only-external"]
        for iteration in range(2):
            with self.subTest(control="owner-only", iteration=iteration):
                owner = run_case("owner-only-unit", owner_builder)
                self.assertEqual(owner.classification, "owner-only-delivery")
                self.assertEqual(owner.parent_signal, signal.SIGINT)
                self.assertIsNone(owner.child_signal)
                self.assertTrue(owner.child_running)
                self.assertTrue(owner.unrelated_running)

            with self.subTest(control="python-killpg", iteration=iteration):
                group = run_case(
                    "python-killpg-unit",
                    None,
                    python_group_control=True,
                )
                self.assertEqual(group.classification, "whole-group-delivery")
                self.assertEqual(group.parent_signal, signal.SIGINT)
                self.assertEqual(group.child_signal, signal.SIGINT)
                self.assertFalse(group.parent_running)
                self.assertFalse(group.child_running)
                self.assertTrue(group.unrelated_running)

    def test_complete_probe_has_exact_schema_and_selects_real_group_delivery(self) -> None:
        record = run_probe()
        self.assertIs(type(record.get("schema_version")), int)
        self.assertEqual(record["schema_version"], 1)
        self.assertIsInstance(record.get("kill_version"), str)
        self.assertTrue(record["kill_version"])
        self.assertIsInstance(record.get("dash_version"), str)
        self.assertTrue(record["dash_version"])

        results = record.get("results")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 6)
        by_name = {result["name"]: result for result in results}
        self.assertEqual(
            by_name["owner-only-external"]["classification"],
            "owner-only-delivery",
        )
        self.assertEqual(
            by_name["python-killpg-control"]["classification"],
            "whole-group-delivery",
        )

        selected = record.get("selected_candidate")
        self.assertIn(
            selected,
            {
                "dash-builtin-short",
                "external-short",
                "external-compact",
                "external-long",
            },
        )
        candidate = by_name[selected]
        self.assertEqual(candidate["classification"], "whole-group-delivery")
        self.assertFalse(candidate["parent_running"])
        self.assertFalse(candidate["child_running"])
        self.assertTrue(candidate["unrelated_running"])


if __name__ == "__main__":
    unittest.main()
