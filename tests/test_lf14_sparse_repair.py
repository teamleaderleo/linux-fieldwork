from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


class LF14SparseRepairTest(unittest.TestCase):
    def test_candidate_preserves_gnu_sparse_member(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        lane = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts"
        )
        patch = lane / "mmdebstrap-tarfilter-preserve-gnu-sparse.patch"
        runner = lane / "run-probes.py"

        with tempfile.TemporaryDirectory(prefix="lf14-sparse-repair-") as td:
            work = pathlib.Path(td)
            candidate_repo = work / "candidate"
            upstream = candidate_repo / "upstream/mmdebstrap"
            upstream.mkdir(parents=True)
            shutil.copy2(repo / "upstream/mmdebstrap/tarfilter", upstream / "tarfilter")

            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            output = work / "run"
            probe = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--repo-root",
                    str(candidate_repo),
                    "--output",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(probe.returncode, 0, probe.stdout + probe.stderr)

            results = json.loads((output / "extraction-results.json").read_text())
            failures = [row for row in results if not row["pass"]]
            self.assertEqual(failures, [])

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
            direct_file = direct["details"]["file"]
            filtered_file = filtered["details"]["file"]
            self.assertEqual(filtered_file["size"], direct_file["size"])
            self.assertLess(filtered_file["allocated_bytes"], filtered_file["size"] // 4)
            self.assertLessEqual(
                filtered_file["allocated_bytes"], direct_file["allocated_bytes"] * 4
            )

            original_archive = output / "fixtures/sparse.tar"
            filtered_archive = output / "filtered/sparse.tar"
            self.assertLess(filtered_archive.stat().st_size, filtered_file["size"] // 4)
            self.assertLessEqual(
                filtered_archive.stat().st_size, original_archive.stat().st_size * 2
            )


if __name__ == "__main__":
    unittest.main()
