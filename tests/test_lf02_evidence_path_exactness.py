from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPERS_PATH = ROOT / "tests/test_lf02_upgrade_failure_summary.py"

spec = importlib.util.spec_from_file_location("lf02_summary_helpers", HELPERS_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load LF-02 test helpers from {HELPERS_PATH}")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


class LF02EvidencePathExactnessTest(unittest.TestCase):
    def run_in_both_modes(self, mutator) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as tmp:
                results, target = helpers.make_results(pathlib.Path(tmp))
                mutator(results, target)
                completed = helpers.run_summary(results, target, optimized=optimized)
                self.assertEqual(
                    completed.returncode,
                    2,
                    completed.stdout + completed.stderr,
                )
                self.assertIn("evidence validation failed:", completed.stderr)
                self.assertFalse((results / "summary.json").exists())

    def test_script_root_prefix_collision_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "purge.snapshot.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            decoy = f"{target}-decoy"
            record["script_log"] = [
                f"phase=postinst script_version=3.0 args_hex=- dpkg_root={decoy} cwd={decoy}",
                f"phase=postinst script_version=3.1 args_hex=- dpkg_root={decoy} cwd={decoy}",
            ]
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)

    def test_classifier_artifact_parent_escape_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            outside = results.parent / "outside.tsv"
            outside.write_text(
                "operation\tpath\tresult\tcategory\n",
                encoding="utf-8",
            )
            path = results / "install-v1-access.summary.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["artifacts"]["events"] = "../outside.tsv"
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)

    def test_fixed_json_symlink_escape_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            outside = results.parent / "outside-provenance.json"
            helpers.write_json(outside, {"schema_version": 1})
            path = results / "provenance.json"
            path.unlink()
            path.symlink_to(outside)

        self.run_in_both_modes(mutate)

    def test_nested_directory_symlink_escape_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            outside = results.parent / "outside-fixtures"
            outside.mkdir()
            helpers.write_json(outside / "manifest.json", {"schema_version": 1})
            fixtures = results / "fixtures"
            (fixtures / "manifest.json").unlink()
            fixtures.rmdir()
            fixtures.symlink_to(outside, target_is_directory=True)

        self.run_in_both_modes(mutate)

    def test_phase_symlink_escape_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            source = results / "install-v1.phase.json"
            outside = results.parent / "outside-phase.json"
            outside.write_bytes(source.read_bytes())
            source.unlink()
            source.symlink_to(outside)

        self.run_in_both_modes(mutate)

    def test_host_fingerprint_symlink_escape_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            outside = results.parent / "outside-host-fingerprint.diff"
            outside.write_text("", encoding="utf-8")
            path = results / "host-fingerprint.diff"
            path.unlink()
            path.symlink_to(outside)

        self.run_in_both_modes(mutate)

    def test_boolean_schema_version_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            helpers.write_json(results / "provenance.json", {"schema_version": True})

        self.run_in_both_modes(mutate)

    def test_boolean_phase_duration_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "install-v1.phase.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["duration_ms"] = True
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)

    def test_boolean_phase_exit_status_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "install-v1.phase.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["exit_status"] = False
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)

    def test_boolean_category_count_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "install-v1-access.summary.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["categories"]["required_host_read"] = True
            record["category_total"] = 1
            record["outside_access_events"] = 1
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)

    def test_boolean_category_total_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "install-v1-access.summary.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["category_total"] = False
            record["outside_access_events"] = False
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)

    def test_summary_output_replaces_symlink_without_touching_target(self) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as tmp:
                results, target = helpers.make_results(pathlib.Path(tmp))
                outside = results.parent / "outside-summary.json"
                sentinel = "do not overwrite\n"
                outside.write_text(sentinel, encoding="utf-8")
                summary = results / "summary.json"
                summary.symlink_to(outside)

                completed = helpers.run_summary(results, target, optimized=optimized)

                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(outside.read_text(encoding="utf-8"), sentinel)
                self.assertFalse(summary.is_symlink())
                record = json.loads(summary.read_text(encoding="utf-8"))
                self.assertEqual(record["disposition"], "retain-mapped-behavior")
                self.assertEqual(
                    list(results.glob(".summary.json.*.tmp")),
                    [],
                )

    def test_duplicate_script_field_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "purge.snapshot.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["script_log"] = [
                f"phase=postinst phase=preinst script_version=3.0 args_hex=- "
                f"dpkg_root={target} cwd={target}",
                f"phase=postinst script_version=3.1 args_hex=- "
                f"dpkg_root={target} cwd={target}",
            ]
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)


if __name__ == "__main__":
    unittest.main()
