from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap"
PACKET = ROOT / "upstream-packets/units/08-current-sid-package-tests"
PATCHES = PACKET / "patches"
SERIES = PATCHES / "series"

CHANGED_FILES = (
    pathlib.Path("coverage.txt"),
    pathlib.Path("coverage.py"),
    pathlib.Path("debian/tests/sourcesfilter"),
    pathlib.Path("debian/tests/testsuite"),
    pathlib.Path("tests/sigint-during-customize-hook"),
)
PYTHON_FILES = (
    pathlib.Path("coverage.py"),
    pathlib.Path("debian/tests/sourcesfilter"),
)
SHELL_FILES = (
    pathlib.Path("debian/tests/testsuite"),
    pathlib.Path("tests/sigint-during-customize-hook"),
)
EXPECTED_SERIES = (
    "0001-tests-sourcesfilter-accept-deb822.patch",
    "0002-tests-use-absolute-installed-mmdebstrap.patch",
    "0003-tests-use-current-sid-process-group-sigint.patch",
    "0004-tests-run-capability-case-in-phase-local-hook-free-pass.patch",
)
EXPECTED_PATCHED_PATHS = {
    EXPECTED_SERIES[0]: ("debian/tests/sourcesfilter",),
    EXPECTED_SERIES[1]: ("debian/tests/testsuite",),
    EXPECTED_SERIES[2]: ("tests/sigint-during-customize-hook",),
    EXPECTED_SERIES[3]: (
        "coverage.txt",
        "coverage.py",
        "debian/tests/testsuite",
    ),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Unit08CurrentSidPackageTestsSeriesTest(unittest.TestCase):
    maxDiff = None

    def series_names(self) -> tuple[str, ...]:
        return tuple(
            line.strip()
            for line in SERIES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def apply_once(self) -> tuple[dict[str, str], tuple[str, ...]]:
        baseline_digests = {
            str(relative): digest(SOURCE / relative) for relative in CHANGED_FILES
        }

        with tempfile.TemporaryDirectory(prefix="unit-08-current-sid-series-") as tmp:
            tree = pathlib.Path(tmp) / "mmdebstrap"
            for relative in CHANGED_FILES:
                destination = tree / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE / relative, destination)

            receipts: list[str] = []
            for patch_name in self.series_names():
                patch_path = PATCHES / patch_name
                self.assertTrue(patch_path.is_file(), patch_path)
                applied = subprocess.run(
                    [
                        "patch",
                        "--batch",
                        "--forward",
                        "--fuzz=0",
                        "-p1",
                        "-i",
                        str(patch_path),
                    ],
                    cwd=tree,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                )
                receipt = applied.stdout + applied.stderr
                self.assertEqual(applied.returncode, 0, receipt)
                lowered = receipt.lower()
                self.assertNotIn("fuzz", lowered, receipt)
                self.assertNotIn("offset", lowered, receipt)
                for expected_path in EXPECTED_PATCHED_PATHS[patch_name]:
                    self.assertIn(f"patching file {expected_path}", receipt)
                receipts.append(receipt)

            compiled = subprocess.run(
                [
                    "python3",
                    "-m",
                    "py_compile",
                    *(str(tree / relative) for relative in PYTHON_FILES),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

            for relative in SHELL_FILES:
                syntax = subprocess.run(
                    ["/bin/sh", "-n", str(tree / relative)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    syntax.returncode,
                    0,
                    f"{relative}: {syntax.stdout}{syntax.stderr}",
                )

            candidate_digests = {
                str(relative): digest(tree / relative) for relative in CHANGED_FILES
            }
            for relative in CHANGED_FILES:
                key = str(relative)
                self.assertNotEqual(
                    candidate_digests[key],
                    baseline_digests[key],
                    f"series did not change {relative}",
                )

        self.assertEqual(
            {str(relative): digest(SOURCE / relative) for relative in CHANGED_FILES},
            baseline_digests,
            "series gate mutated the imported source tree",
        )
        return candidate_digests, tuple(receipts)

    def test_series_applies_exactly_and_reruns_cleanly(self) -> None:
        self.assertEqual(self.series_names(), EXPECTED_SERIES)
        first_digests, first_receipts = self.apply_once()
        second_digests, second_receipts = self.apply_once()
        self.assertEqual(second_digests, first_digests)
        self.assertEqual(second_receipts, first_receipts)


if __name__ == "__main__":
    unittest.main()
