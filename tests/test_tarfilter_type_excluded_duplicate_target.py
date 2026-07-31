from __future__ import annotations

import io
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest

from tests import test_tarfilter_type_excluded_hardlink_candidate as candidate_tests


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPAIR_PATCH = (
    ROOT
    / "investigations"
    / "tarfilter-type-excluded-hardlink-target"
    / "0002-honor-retained-duplicate-targets.patch"
)


class TarfilterTypeExcludedDuplicateTargetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidate_tests.TarfilterTypeExcludedHardlinkCandidateTest.setUpClass()

    @staticmethod
    def duplicate_name_archive() -> bytes:
        output = io.BytesIO()
        payload = b"retained-target\n"
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            regular = tarfile.TarInfo("root/base")
            regular.size = len(payload)
            regular.mtime = 946684800
            archive.addfile(regular, io.BytesIO(payload))

            excluded_duplicate = tarfile.TarInfo("root/base")
            excluded_duplicate.type = tarfile.SYMTYPE
            excluded_duplicate.linkname = "missing"
            excluded_duplicate.mtime = 946684800
            archive.addfile(excluded_duplicate)

            peer = tarfile.TarInfo("root/peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "root/base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    def apply_repair(self, tree: pathlib.Path) -> pathlib.Path:
        completed = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(REPAIR_PATCH),
            ],
            cwd=tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertNotIn("fuzz", (completed.stdout + completed.stderr).lower())

        source = tree / "upstream/mmdebstrap/tarfilter"
        compiled = subprocess.run(
            [sys.executable, "-m", "py_compile", str(source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        return source

    def test_retained_duplicate_name_keeps_hardlink_target_valid(self) -> None:
        helper = candidate_tests.TarfilterTypeExcludedHardlinkCandidateTest(
            methodName="runTest"
        )
        archive = self.duplicate_name_archive()
        expected = {
            "root/base": (tarfile.REGTYPE, ""),
            "root/peer": (tarfile.LNKTYPE, "root/base"),
        }

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-duplicate-target-"
        ) as td:
            root = pathlib.Path(td)

            baseline = helper.run_filter(
                helper.source, archive, "--type-exclude=SYMTYPE"
            )
            self.assertEqual(
                baseline.returncode,
                0,
                baseline.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(helper.member_map(baseline.stdout), expected)
            extracted, destination = helper.extract(
                baseline.stdout, root, "baseline"
            )
            self.assertEqual(
                extracted.returncode, 0, extracted.stdout + extracted.stderr
            )
            self.assertEqual(
                (destination / "root/base").read_bytes(), b"retained-target\n"
            )
            self.assertEqual(
                os.stat(destination / "root/base").st_ino,
                os.stat(destination / "root/peer").st_ino,
            )

            predecessor = helper.prepare_candidate(root)
            rejected = helper.run_filter(
                predecessor, archive, "--type-exclude=SYMTYPE"
            )
            self.assertEqual(rejected.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "root/peer -> root/base",
                rejected.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                helper.member_map(rejected.stdout),
                {"root/base": (tarfile.REGTYPE, "")},
            )

            repaired = self.apply_repair(root / "candidate")
            accepted = helper.run_filter(
                repaired, archive, "--type-exclude=SYMTYPE"
            )
            self.assertEqual(
                accepted.returncode,
                0,
                accepted.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(helper.member_map(accepted.stdout), expected)
            extracted, destination = helper.extract(
                accepted.stdout, root, "repaired"
            )
            self.assertEqual(
                extracted.returncode, 0, extracted.stdout + extracted.stderr
            )
            self.assertEqual(
                (destination / "root/base").read_bytes(), b"retained-target\n"
            )
            self.assertEqual(
                os.stat(destination / "root/base").st_ino,
                os.stat(destination / "root/peer").st_ino,
            )


if __name__ == "__main__":
    unittest.main()
