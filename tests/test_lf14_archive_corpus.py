from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


class LF14ArchiveCorpusTest(unittest.TestCase):
    def test_reference_and_tarfilter_matrix(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        runner = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts/run-probes.py"
        )
        with tempfile.TemporaryDirectory(prefix="lf14-") as td:
            output = pathlib.Path(td) / "run"
            cp = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--repo-root",
                    str(repo),
                    "--output",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            results = json.loads((output / "extraction-results.json").read_text())
            failures = {(row["path"], row["case"]) for row in results if not row["pass"]}
            self.assertEqual(failures, {("mmdebstrap-tarfilter", "sparse")})
            direct = next(
                row for row in results
                if row["path"] == "gnu-tar-direct" and row["case"] == "sparse"
            )
            filtered = next(
                row for row in results
                if row["path"] == "mmdebstrap-tarfilter" and row["case"] == "sparse"
            )
            self.assertTrue(direct["pass"])
            self.assertFalse(filtered["pass"])


if __name__ == "__main__":
    unittest.main()
