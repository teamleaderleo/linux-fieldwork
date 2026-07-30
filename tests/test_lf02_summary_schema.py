from __future__ import annotations

import importlib.util
import json
import pathlib
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
        self.phase(root, "direct-install", 15.25)
        self.phase(root, "mmdebstrap-one", 1020.75)
        self.classification(root, "direct", service_actions=1, host_reads=4)
        self.classification(root, "mmdebstrap-one", service_actions=2, host_reads=8)
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

        self.assertEqual(summary["schema_version"], 3)
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
            started_ns=1_000_000_000,
            started_utc="1970-01-01T00:00:01.000Z",
            finished_ns=2_234_567_890,
            finished_utc="1970-01-01T00:00:02.235Z",
            exit_status=0,
            artifacts={"stdout": "phase.stdout"},
        )
        self.assertEqual(record["duration_ms"], 1234.568)
        self.assertEqual(record["exit_status"], 0)

    def test_phase_finish_before_start_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "precedes"):
            self.module.finish_phase_record(
                started_ns=2,
                started_utc="start",
                finished_ns=1,
                finished_utc="finish",
                exit_status=0,
                artifacts={},
            )


if __name__ == "__main__":
    unittest.main()
