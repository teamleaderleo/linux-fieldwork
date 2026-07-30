from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterNoOptionPassthroughTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.patch = cls.repo / (
            "investigations/tarfilter-no-option-passthrough/"
            "tarfilter-no-option-passthrough.patch"
        )

    def make_archive(self, path: pathlib.Path, mode: str) -> None:
        payload = b"linux-fieldwork-no-option\n"
        info = tarfile.TarInfo("original.txt")
        info.size = len(payload)
        info.uid = 123
        info.gid = 456
        info.mtime = 946684800
        with tarfile.open(path, mode, format=tarfile.PAX_FORMAT) as archive:
            archive.addfile(info, io.BytesIO(payload))

    def run_filter(
        self, source: pathlib.Path, archive: pathlib.Path, *options: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(source), *options],
            input=archive.read_bytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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

    def test_unmodified_source_proves_no_option_path_is_not_passthrough(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-no-option-negative-") as td:
            archive = pathlib.Path(td) / "input.tar.gz"
            self.make_archive(archive, "w:gz")
            completed = self.run_filter(self.source, archive)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", "replace"),
            )
            self.assertNotEqual(completed.stdout, archive.read_bytes())
            self.assertTrue(archive.read_bytes().startswith(b"\x1f\x8b"))
            self.assertFalse(completed.stdout.startswith(b"\x1f\x8b"))

    def test_candidate_preserves_no_option_archives_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-no-option-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)
            archives = []
            for suffix, mode in (
                ("tar", "w"),
                ("tar.gz", "w:gz"),
                ("tar.bz2", "w:bz2"),
                ("tar.xz", "w:xz"),
            ):
                archive = root / f"ordinary.{suffix}"
                self.make_archive(archive, mode)
                archives.append(archive)

            sparse_source = root / "sparse-file"
            with sparse_source.open("wb") as stream:
                stream.write(b"BEGIN")
                stream.seek(1024 * 1024)
                stream.write(b"MIDDLE")
                stream.seek(8 * 1024 * 1024)
                stream.write(b"END")
            sparse_archive = root / "sparse.tar"
            created = subprocess.run(
                [
                    "tar",
                    "--format=pax",
                    "--sparse",
                    "-cf",
                    str(sparse_archive),
                    "-C",
                    str(root),
                    sparse_source.name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            archives.append(sparse_archive)

            for archive in archives:
                with self.subTest(archive=archive.name):
                    completed = self.run_filter(candidate, archive)
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr.decode("utf-8", "replace"),
                    )
                    self.assertEqual(completed.stdout, archive.read_bytes())

            for no_op in (
                ("--strip-components=0",),
                ("--idshift=0",),
            ):
                with self.subTest(no_op=no_op):
                    completed = self.run_filter(candidate, archives[0], *no_op)
                    self.assertEqual(completed.returncode, 0)
                    self.assertEqual(completed.stdout, archives[0].read_bytes())

    def test_candidate_does_not_bypass_transform_or_idshift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-no-option-options-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)
            archive = root / "input.tar"
            self.make_archive(archive, "w")

            transformed = self.run_filter(
                candidate, archive, "--transform=s,original,renamed,"
            )
            self.assertEqual(
                transformed.returncode,
                0,
                transformed.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(fileobj=io.BytesIO(transformed.stdout), mode="r:*") as result:
                self.assertEqual(result.getnames(), ["renamed.txt"])

            shifted = self.run_filter(candidate, archive, "--idshift=1")
            self.assertEqual(
                shifted.returncode,
                0,
                shifted.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(fileobj=io.BytesIO(shifted.stdout), mode="r:*") as result:
                member = result.getmember("original.txt")
                self.assertEqual((member.uid, member.gid), (124, 457))


if __name__ == "__main__":
    unittest.main()
