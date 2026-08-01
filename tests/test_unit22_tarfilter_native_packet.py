from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import tempfile
import unittest


EXPECTED_TARFILTER_BLOB = "ad776167a8473d5d15dbe22e850f4f6db35cf278"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class Unit22TarfilterNativePacketTest(unittest.TestCase):
    def test_native_regression_distinguishes_baseline_and_candidate(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        source = repo / "upstream/mmdebstrap/tarfilter"
        packet = (
            repo
            / "upstream-packets/units/22-tarfilter-regular-type-class"
        )
        patch_file = (
            packet / "patches/0001-tarfilter-treat-nul-as-regular.patch"
        )
        native_test = (
            packet / "native/tests/tarfilter-regular-type-class"
        )
        coverage_fragment = packet / "native/coverage.txt.fragment"

        self.assertEqual(
            git_blob_sha(source.read_bytes()),
            EXPECTED_TARFILTER_BLOB,
            "the native packet must execute against the reviewed source blob",
        )
        self.assertEqual(
            coverage_fragment.read_text(),
            "Test: tarfilter-regular-type-class\n",
        )
        self.assertTrue(native_test.read_text().startswith("#!/bin/sh\n"))

        with tempfile.TemporaryDirectory(prefix="unit22-native-") as td:
            work = pathlib.Path(td)
            baseline = work / "baseline"
            candidate = work / "candidate"
            baseline.mkdir()
            candidate.mkdir()

            for checkout in (baseline, candidate):
                target = checkout / "tarfilter"
                shutil.copy2(source, target)
                target.chmod(0o755)

            baseline_run = subprocess.run(
                ["sh", str(native_test)],
                cwd=baseline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertNotEqual(
                baseline_run.returncode,
                0,
                "negative control: the unmodified source must fail the native test",
            )
            self.assertIn("nul-regular", baseline_run.stderr)

            applied = subprocess.run(
                [
                    "patch",
                    "--fuzz=0",
                    "-p1",
                    "-d",
                    str(candidate),
                    "-i",
                    str(patch_file),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(
                applied.returncode,
                0,
                applied.stdout + applied.stderr,
            )

            for run_number in (1, 2):
                candidate_run = subprocess.run(
                    ["sh", str(native_test)],
                    cwd=candidate,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    candidate_run.returncode,
                    0,
                    f"candidate native run {run_number}: "
                    + candidate_run.stdout
                    + candidate_run.stderr,
                )


if __name__ == "__main__":
    unittest.main()
