from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


class LF02SummarySchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        module_path = repo / (
            "programmes/rootless-execution/lanes/"
            "LF-02-chrootless-dpkg-root-containment/scouts/"
            "LF-SCOUT-ROOT-01/artifacts/summarize-probe.py"
        )
        spec = importlib.util.spec_from_file_location("lf02_summary", module_path)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def write_json(self, path: pathlib.Path, value: dict) -> None:
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    def phase(self, root: pathlib.Path, name: str, duration: float = 12.5) -> None:
        (root / f"{name}.status").write_text("0\n", encoding="utf-8")
        (root / f"{name}.command").write_text("<runtime>/tool\n", encoding="utf-8")
        (root / f"{name}.command.raw").write_text(
            "/tmp/runtime/tool\n", encoding="utf-8"
        )
        (root / f"{name}.stdout").write_text("", encoding="utf-8")
        (root / f"{name}.stderr").write_text("", encoding="utf-8")
        (root / f"{name}.trace.1").write_text("trace\n", encoding="utf-8")
        self.write_json(
            root / f"{name}.phase.json",
            {
                "exit_status": 0,
                "started_utc": "2026-07-30T00:00:00.000Z",
                "finished_utc": "2026-07-30T00:00:00.013Z",
                "duration_ms": duration,
                "artifacts": {
                    "command_normalized": f"{name}.command",
                    "command_raw": f"{name}.command.raw",
                    "stdout": f"{name}.stdout",
                    "stderr": f"{name}.stderr",
                    "status": f"{name}.status",
                    "trace_glob": f"{name}.trace*",
                },
            },
        )

    def classification(
        self,
        root: pathlib.Path,
        name: str,
        *,
        service_actions: int,
        host_reads: int,
    ) -> None:
        categories = {
            "required_host_read": host_reads,
            "harmless_runtime_interaction": 2,
            "unexpected_mutation": 0,
            "service_action": service_actions,
            "unresolved": 0,
        }
        total = sum(categories.values())
        self.write_json(
            root / f"{name}-access.summary.json",
            {
                "schema_version": 1,
                "target": f"/tmp/{name}-root",
                "trace_files": 3,
                "outside_access_events": total,
                "categories": categories,
                "category_total": total,
                "category_total_matches_events": True,
                "artifacts": {
                    "events": f"{name}-access.tsv",
                    "text_summary": f"{name}-access.summary.txt",
                    "structured_summary": f"{name}-access.summary.json",
                },
            },
        )
        (root / f"{name}-access.tsv").write_text("", encoding="utf-8")
        (root / f"{name}-access.summary.txt").write_text("", encoding="utf-8")

    def populated_root(self) -> tuple[tempfile.TemporaryDirectory, pathlib.Path]:
        temporary = tempfile.TemporaryDirectory()
        root = pathlib.Path(temporary.name)
        self.write_json(
            root / "provenance.json",
            {
                "schema_version": 1,
                "repository": {"checked_out_head": "abc"},
                "github_actions": {"active": False},
            },
        )
        for index, name in enumerate(self.module.PHASE_ORDER):
            self.phase(root, name, 15.25 + index)
        self.classification(root, "direct", service_actions=1, host_reads=4)
        self.classification(root, "mmdebstrap-one", service_actions=2, host_reads=8)
        self.classification(root, "mmdebstrap-two", service_actions=0, host_reads=8)
        for name in (
            "host-fingerprint.diff",
            "mmdebstrap-rerun-script.diff",
            "mmdebstrap-rerun-alternative.diff",
        ):
            (root / name).write_text("", encoding="utf-8")
        return temporary, root

    def test_schema_uses_typed_fixture_categories_phases_and_decision_inputs(self) -> None:
        temporary, root = self.populated_root()
        try:
            fixture = {
                "package": "lf-fieldwork-probe",
                "version": "1.0",
                "architecture": "all",
                "archive_name": "lf-fieldwork-probe_1.0_all.deb",
                "size_bytes": 1018,
                "sha256": "a" * 64,
            }
            tools = {
                "dpkg": {"version": "1.22.6", "raw": "dpkg 1.22.6"},
                "mmdebstrap": {"version": "1.5.7", "raw": "source VERSION=1.5.7"},
            }
            summary = self.module.build_summary(
                root, fixture=fixture, tools=tools
            )
        finally:
            temporary.cleanup()

        self.assertEqual(summary["schema_version"], 4)
        self.assertEqual(summary["fixture"], fixture)
        self.assertEqual(summary["tools"], tools)
        self.assertEqual(summary["phases"]["direct-install"]["duration_ms"], 15.25)
        self.assertEqual(
            summary["phases"]["mmdebstrap-one"]["artifacts"]["trace_glob"],
            "mmdebstrap-one.trace*",
        )
        direct = summary["classifications"]["direct"]
        self.assertEqual(direct["categories"]["required_host_read"], 4)
        self.assertEqual(direct["category_total"], direct["outside_access_events"])
        self.assertTrue(direct["category_total_matches_events"])
        self.assertEqual(summary["decision_inputs"]["service_actions"], 3)
        self.assertEqual(summary["decision_inputs"]["unexpected_mutations"], 0)
        self.assertTrue(summary["decision_inputs"]["promotion_signal"])
        self.assertTrue(summary["decision_inputs"]["phases_successful"])
        self.assertTrue(summary["decision_inputs"]["comparisons_successful"])
        self.assertEqual(summary["receipt_status"], "passed")
        self.assertEqual(summary["decision"], "promote")
        self.assertTrue(self.module.summary_passes(summary))

    def test_category_total_mismatch_is_rejected(self) -> None:
        value = {
            "schema_version": 1,
            "target": "/target",
            "trace_files": 1,
            "outside_access_events": 8,
            "categories": {
                "required_host_read": 1,
                "harmless_runtime_interaction": 2,
                "unexpected_mutation": 0,
                "service_action": 3,
                "unresolved": 0,
            },
            "artifacts": {},
        }
        with self.assertRaisesRegex(ValueError, "category total"):
            self.module.validate_classification("case", value)

    def test_classification_rejects_coercible_and_invalid_numbers(self) -> None:
        baseline = {
            "schema_version": 1,
            "target": "/target",
            "trace_files": 1,
            "outside_access_events": 0,
            "categories": dict.fromkeys(self.module.CATEGORY_IDS, 0),
            "category_total": 0,
            "category_total_matches_events": True,
            "artifacts": {},
        }
        for field, invalid in (
            ("trace_files", True),
            ("trace_files", "1"),
            ("trace_files", -1),
            ("outside_access_events", "0"),
        ):
            with self.subTest(field=field, invalid=invalid):
                value = dict(baseline)
                value[field] = invalid
                with self.assertRaisesRegex(ValueError, "JSON integer"):
                    self.module.validate_classification("case", value)

        for invalid in (True, "0", -1):
            with self.subTest(category=invalid):
                value = dict(baseline)
                value["categories"] = dict(baseline["categories"])
                value["categories"]["unresolved"] = invalid
                with self.assertRaisesRegex(ValueError, "JSON integer"):
                    self.module.validate_classification("case", value)

    def test_exact_phase_and_classification_inventories_are_required(self) -> None:
        temporary, root = self.populated_root()
        try:
            (root / "direct-reinstall.phase.json").unlink()
            with self.assertRaisesRegex(ValueError, "phase inventory"):
                self.module.build_summary(root, fixture={}, tools={})
        finally:
            temporary.cleanup()

        temporary, root = self.populated_root()
        try:
            (root / "mmdebstrap-two-access.summary.json").unlink()
            with self.assertRaisesRegex(ValueError, "classification inventory"):
                self.module.build_summary(root, fixture={}, tools={})
        finally:
            temporary.cleanup()

    def test_missing_phase_artifact_and_unfinished_phase_are_rejected(self) -> None:
        temporary, root = self.populated_root()
        try:
            (root / "direct-install.stderr").unlink()
            with self.assertRaisesRegex(ValueError, "regular-file artifact"):
                self.module.build_summary(root, fixture={}, tools={})
        finally:
            temporary.cleanup()

        temporary, root = self.populated_root()
        try:
            self.write_json(
                root / "direct-install.phase-start.json",
                {"started_monotonic_ns": 1, "started_utc": "start"},
            )
            with self.assertRaisesRegex(ValueError, "unfinished phase"):
                self.module.build_summary(root, fixture={}, tools={})
        finally:
            temporary.cleanup()

    def test_phase_duration_and_artifact_types_are_strict(self) -> None:
        for invalid in (True, "1", -1, float("nan"), float("inf")):
            with self.subTest(duration=invalid):
                temporary, root = self.populated_root()
                try:
                    path = root / "direct-install.phase.json"
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["duration_ms"] = invalid
                    self.write_json(path, value)
                    with self.assertRaisesRegex(ValueError, "JSON number"):
                        self.module.build_summary(root, fixture={}, tools={})
                finally:
                    temporary.cleanup()

        temporary, root = self.populated_root()
        try:
            path = root / "direct-install.phase.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["artifacts"] = []
            self.write_json(path, value)
            with self.assertRaisesRegex(ValueError, "artifacts must be an object"):
                self.module.build_summary(root, fixture={}, tools={})
        finally:
            temporary.cleanup()

    def test_unresolved_and_comparison_drift_have_explicit_dispositions(self) -> None:
        temporary, root = self.populated_root()
        try:
            value = json.loads(
                (root / "mmdebstrap-two-access.summary.json").read_text(
                    encoding="utf-8"
                )
            )
            value["categories"]["unresolved"] = 1
            value["outside_access_events"] += 1
            value["category_total"] += 1
            self.write_json(root / "mmdebstrap-two-access.summary.json", value)
            summary = self.module.build_summary(root, fixture={}, tools={})
            self.assertEqual(summary["receipt_status"], "failed")
            self.assertEqual(summary["decision"], "promote")
        finally:
            temporary.cleanup()

        temporary, root = self.populated_root()
        try:
            for name in self.module.CLASSIFICATION_ORDER:
                value = json.loads(
                    (root / f"{name}-access.summary.json").read_text(
                        encoding="utf-8"
                    )
                )
                value["categories"]["service_action"] = 0
                value["categories"]["unresolved"] = 1 if name == "direct" else 0
                value["outside_access_events"] = sum(value["categories"].values())
                value["category_total"] = value["outside_access_events"]
                self.write_json(root / f"{name}-access.summary.json", value)
            summary = self.module.build_summary(root, fixture={}, tools={})
            self.assertEqual(summary["receipt_status"], "failed")
            self.assertEqual(summary["decision"], "blocked")
        finally:
            temporary.cleanup()

        temporary, root = self.populated_root()
        try:
            for name in self.module.CLASSIFICATION_ORDER:
                value = json.loads(
                    (root / f"{name}-access.summary.json").read_text(
                        encoding="utf-8"
                    )
                )
                value["categories"]["service_action"] = 0
                value["outside_access_events"] = sum(value["categories"].values())
                value["category_total"] = value["outside_access_events"]
                self.write_json(root / f"{name}-access.summary.json", value)
            (root / "host-fingerprint.diff").write_text("changed\n", encoding="utf-8")
            summary = self.module.build_summary(root, fixture={}, tools={})
            self.assertEqual(summary["receipt_status"], "failed")
            self.assertEqual(summary["decision"], "invalid-receipt")
        finally:
            temporary.cleanup()

    def test_optimized_python_keeps_type_validation(self) -> None:
        module_path = pathlib.Path(self.module.__file__)
        code = """
import runpy
module = runpy.run_path({module_path!r})
value = {{
    "schema_version": 1,
    "target": "/target",
    "trace_files": True,
    "outside_access_events": 0,
    "categories": dict.fromkeys(module["CATEGORY_IDS"], 0),
    "category_total": 0,
    "category_total_matches_events": True,
    "artifacts": {{}},
}}
module["validate_classification"]("case", value)
""".format(module_path=str(module_path))
        for optimize in (False, True):
            command = [sys.executable]
            if optimize:
                command.append("-O")
            completed = subprocess.run(
                command + ["-c", code],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("expected non-negative JSON integer", completed.stderr)

    def test_unknown_or_missing_category_is_rejected(self) -> None:
        value = {
            "schema_version": 1,
            "target": "/target",
            "trace_files": 1,
            "outside_access_events": 0,
            "categories": {
                "required_host_read": 0,
                "harmless_runtime_interaction": 0,
                "unexpected_mutation": 0,
                "service_action": 0,
            },
            "artifacts": {},
        }
        with self.assertRaisesRegex(ValueError, "categories differ"):
            self.module.validate_classification("case", value)

    def test_phase_duration_is_observation_not_equality_rule(self) -> None:
        record = self.module.finish_phase_record(
            started_monotonic_ns=1_000_000_000,
            started_utc="1970-01-01T00:00:02.000Z",
            finished_monotonic_ns=2_234_567_890,
            finished_utc="1970-01-01T00:00:01.000Z",
            exit_status=0,
            artifacts={"stdout": "phase.stdout"},
        )
        self.assertEqual(record["duration_ms"], 1234.568)
        self.assertEqual(record["exit_status"], 0)

    def test_phase_finish_before_start_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "precedes"):
            self.module.finish_phase_record(
                started_monotonic_ns=2,
                started_utc="start",
                finished_monotonic_ns=1,
                finished_utc="finish",
                exit_status=0,
                artifacts={},
            )


if __name__ == "__main__":
    unittest.main()
