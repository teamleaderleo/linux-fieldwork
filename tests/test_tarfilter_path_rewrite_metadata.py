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


class TarfilterPathRewriteMetadataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.patch = cls.repo / (
            "investigations/tarfilter-path-rewrite-metadata/"
            "tarfilter-path-rewrite-metadata.patch"
        )

    def prepare_candidate(self, root: pathlib.Path) -> pathlib.Path:
        candidate = root / "candidate"
        target = candidate / "upstream/mmdebstrap/tarfilter"
        target.parent.mkdir(parents=True)
        shutil.copy2(self.source, target)
        applied = subprocess.run(
            ["patch", "-p1", "-d", str(candidate), "-i", str(self.patch)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        return target

    def regular(self, name: str, payload: bytes = b"hard-link-payload\n"):
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        member.mtime = 946684800
        return member, payload

    def hardlink(self, name: str, target: str):
        member = tarfile.TarInfo(name)
        member.type = tarfile.LNKTYPE
        member.linkname = target
        member.mtime = 946684800
        return member, None

    def symlink(self, name: str, target: str):
        member = tarfile.TarInfo(name)
        member.type = tarfile.SYMTYPE
        member.linkname = target
        member.mtime = 946684800
        return member, None

    def archive_bytes(self, entries) -> bytes:
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for member, payload in entries:
                archive.addfile(
                    member,
                    io.BytesIO(payload) if payload is not None else None,
                )
        return output.getvalue()

    def run_filter(self, source: pathlib.Path, archive: bytes, *options: str):
        return subprocess.run(
            [sys.executable, str(source), *options],
            input=archive,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def extract(self, archive: bytes, target: pathlib.Path) -> subprocess.CompletedProcess[str]:
        archive_path = target.parent / f"{target.name}.tar"
        archive_path.write_bytes(archive)
        target.mkdir()
        return subprocess.run(
            ["tar", "-xf", str(archive_path), "-C", str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def assert_hardlink_extracts(self, archive: bytes, base: str, peer: str, root: pathlib.Path) -> None:
        extracted = self.extract(archive, root)
        self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
        base_path = root / base
        peer_path = root / peer
        self.assertEqual(base_path.read_bytes(), b"hard-link-payload\n")
        self.assertEqual(peer_path.read_bytes(), base_path.read_bytes())
        self.assertEqual(os.stat(base_path).st_ino, os.stat(peer_path).st_ino)

    def test_strip_rewrites_short_hard_link_target(self) -> None:
        archive = self.archive_bytes(
            [
                self.regular("prefix/base"),
                self.hardlink("prefix/peer", "prefix/base"),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-strip-link-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)
            negative = self.run_filter(
                self.source, archive, "--strip-components=1"
            )
            repaired = self.run_filter(
                candidate, archive, "--strip-components=1"
            )
            self.assertEqual(negative.returncode, 0)
            self.assertEqual(repaired.returncode, 0)

            negative_extract = self.extract(negative.stdout, root / "negative")
            self.assertNotEqual(negative_extract.returncode, 0)
            self.assertIn("prefix/base", negative_extract.stderr)

            with tarfile.open(fileobj=io.BytesIO(repaired.stdout), mode="r:*") as result:
                peer = result.getmember("peer")
                self.assertEqual(peer.linkname, "base")
            self.assert_hardlink_extracts(repaired.stdout, "base", "peer", root / "repaired")

    def test_transform_rewrites_hard_link_but_not_symlink_target(self) -> None:
        archive = self.archive_bytes(
            [
                self.regular("prefix/base"),
                self.hardlink("prefix/peer", "prefix/base"),
                self.symlink("prefix/sym", "prefix/target"),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-transform-link-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)
            repaired = self.run_filter(
                candidate, archive, "--transform=s,^prefix/,,"
            )
            self.assertEqual(
                repaired.returncode,
                0,
                repaired.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(fileobj=io.BytesIO(repaired.stdout), mode="r:*") as result:
                self.assertEqual(result.getmember("peer").linkname, "base")
                self.assertEqual(result.getmember("sym").linkname, "prefix/target")
            self.assert_hardlink_extracts(repaired.stdout, "base", "peer", root / "repaired")
            self.assertEqual(os.readlink(root / "repaired/sym"), "prefix/target")

    def test_strip_regenerates_long_pax_path_and_linkpath(self) -> None:
        leaf = "x" * 120
        archive = self.archive_bytes(
            [
                self.regular(f"prefix/{leaf}"),
                self.hardlink("prefix/peer", f"prefix/{leaf}"),
            ]
        )
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as source:
            self.assertEqual(source.getmember(f"prefix/{leaf}").pax_headers["path"], f"prefix/{leaf}")
            self.assertEqual(source.getmember("prefix/peer").pax_headers["linkpath"], f"prefix/{leaf}")

        with tempfile.TemporaryDirectory(prefix="tarfilter-pax-path-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)
            negative = self.run_filter(
                self.source, archive, "--strip-components=1"
            )
            repaired = self.run_filter(
                candidate, archive, "--strip-components=1"
            )
            self.assertEqual(negative.returncode, 0)
            self.assertEqual(repaired.returncode, 0)
            with tarfile.open(fileobj=io.BytesIO(negative.stdout), mode="r:*") as result:
                self.assertIn(f"prefix/{leaf}", result.getnames())
            with tarfile.open(fileobj=io.BytesIO(repaired.stdout), mode="r:*") as result:
                long_member = result.getmember(leaf)
                peer = result.getmember("peer")
                self.assertEqual(long_member.pax_headers.get("path"), leaf)
                self.assertEqual(peer.linkname, leaf)
                self.assertEqual(peer.pax_headers.get("linkpath"), leaf)
            self.assert_hardlink_extracts(repaired.stdout, leaf, "peer", root / "repaired")


if __name__ == "__main__":
    unittest.main()
