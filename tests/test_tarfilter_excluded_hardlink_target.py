from __future__ import annotations

import io
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterExcludedHardlinkTargetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        if shutil.which("tar") is None:
            raise unittest.SkipTest("GNU tar is required")

    @staticmethod
    def archive_bytes() -> bytes:
        output = io.BytesIO()
        payload = b"hard-link-payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            base = tarfile.TarInfo("root/base")
            base.size = len(payload)
            base.mtime = 946684800
            archive.addfile(base, io.BytesIO(payload))

            peer = tarfile.TarInfo("root/peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "root/base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    def run_filter(self, archive: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                str(self.source),
                "--path-exclude=/root/base",
            ],
            input=archive,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    @staticmethod
    def extract(
        archive: bytes, root: pathlib.Path, label: str
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
        archive_path = root / f"{label}.tar"
        target = root / label
        archive_path.write_bytes(archive)
        target.mkdir()
        completed = subprocess.run(
            ["tar", "-xf", str(archive_path), "-C", str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return completed, target

    @staticmethod
    def member_map(archive: bytes) -> dict[str, tuple[bytes, str]]:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
            return {
                member.name: (member.type, member.linkname)
                for member in handle
            }

    def test_excluding_data_member_retains_dangling_hardlink(self) -> None:
        archive = self.archive_bytes()
        with tempfile.TemporaryDirectory(prefix="tarfilter-excluded-hardlink-") as td:
            root = pathlib.Path(td)

            direct, direct_root = self.extract(archive, root, "direct")
            self.assertEqual(direct.returncode, 0, direct.stdout + direct.stderr)
            self.assertEqual((direct_root / "root/base").read_bytes(), b"hard-link-payload\n")
            self.assertEqual((direct_root / "root/peer").read_bytes(), b"hard-link-payload\n")
            self.assertEqual(
                os.stat(direct_root / "root/base").st_ino,
                os.stat(direct_root / "root/peer").st_ino,
            )

            filtered = self.run_filter(archive)
            self.assertEqual(
                filtered.returncode,
                0,
                filtered.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(filtered.stdout),
                {"root/peer": (tarfile.LNKTYPE, "root/base")},
            )

            extracted, filtered_root = self.extract(filtered.stdout, root, "filtered")
            self.assertNotEqual(extracted.returncode, 0)
            self.assertIn("root/base", extracted.stderr)
            self.assertFalse((filtered_root / "root/base").exists())
            self.assertFalse((filtered_root / "root/peer").exists())


if __name__ == "__main__":
    unittest.main()
