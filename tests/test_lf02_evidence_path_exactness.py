from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPERS_PATH = ROOT / "tests/test_lf02_upgrade_failure_summary.py"

spec = importlib.util.spec_from_file_location("lf02_summary_helpers", HELPERS_PATH)
assert spec is not None and spec.loader is not None
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
                f"phase=postinst script_version=3.0 dpkg_root={decoy} cwd={decoy}",
                f"phase=postinst script_version=3.1 dpkg_root={decoy} cwd={decoy}",
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

    def test_duplicate_script_field_is_rejected(self) -> None:
        def mutate(results: pathlib.Path, target: pathlib.Path) -> None:
            path = results / "purge.snapshot.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["script_log"] = [
                f"phase=postinst phase=preinst script_version=3.0 "
                f"dpkg_root={target} cwd={target}",
                f"phase=postinst script_version=3.1 "
                f"dpkg_root={target} cwd={target}",
            ]
            helpers.write_json(path, record)

        self.run_in_both_modes(mutate)


if __name__ == "__main__":
    unittest.main()
