from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


def load_runner(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("lf14_run_probes", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runner from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LF14ArchiveCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.runner_path = cls.repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts/run-probes.py"
        )
        cls.runner = load_runner(cls.runner_path)

    def test_reference_and_tarfilter_matrix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf14-") as td:
            output = pathlib.Path(td) / "run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.runner_path),
                    "--repo-root",
                    str(self.repo),
                    "--output",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                1,
                completed.stdout + completed.stderr,
            )
            results = json.loads((output / "extraction-results.json").read_text())
            failures = {
                (row["path"], row["case"])
                for row in results
                if not row["pass"]
            }
            self.assertEqual(failures, {("mmdebstrap-tarfilter", "sparse")})

            direct = next(
                row
                for row in results
                if row["path"] == "gnu-tar-direct" and row["case"] == "sparse"
            )
            filtered = next(
                row
                for row in results
                if row["path"] == "mmdebstrap-tarfilter"
                and row["case"] == "sparse"
            )
            self.assertTrue(direct["pass"])
            self.assertTrue(direct["details"]["content"]["content_ok"])
            self.assertFalse(filtered["pass"])

            ownership_rows = [
                row for row in results if row["case"] == "numeric-owner"
            ]
            self.assertEqual(len(ownership_rows), 2)
            for row in ownership_rows:
                details = row["details"]
                self.assertTrue(row["pass"])
                self.assertEqual(
                    details["file"]["uid"],
                    details["expected_extracted_uid"],
                )
                self.assertEqual(
                    details["file"]["gid"],
                    details["expected_extracted_gid"],
                )

    def test_sparse_content_detector_rejects_wrong_extents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf14-negative-") as td:
            path = pathlib.Path(td) / "wrong-sparse"
            with path.open("wb") as stream:
                stream.write(b"WRONG")
                stream.seek(1024 * 1024)
                stream.write(b"BROKEN")
                stream.seek(8 * 1024 * 1024)
                stream.write(b"BAD")
            details = self.runner.sparse_content(path)
            self.assertFalse(details["content_ok"])
            self.assertNotEqual(details["sha256"], details["expected_sha256"])

    def test_output_guard_rejects_destructive_root(self) -> None:
        with self.assertRaises(ValueError):
            self.runner.prepare_output(pathlib.Path("/"), self.runner_path.parent)


if __name__ == "__main__":
    unittest.main()
