from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterPathFilterMatchingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.patch = cls.repo / (
            "investigations/tarfilter-path-filter-matching/"
            "tarfilter-path-filter-matching.patch"
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

    def archive_bytes(self, entries: list[tuple[tarfile.TarInfo, bytes | None]]) -> bytes:
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for member, payload in entries:
                archive.addfile(
                    member,
                    io.BytesIO(payload) if payload is not None else None,
                )
        return output.getvalue()

    def regular(self, name: str, payload: bytes = b"payload\n") -> tuple[tarfile.TarInfo, bytes]:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        member.mtime = 946684800
        return member, payload

    def directory(self, name: str) -> tuple[tarfile.TarInfo, None]:
        member = tarfile.TarInfo(name)
        member.type = tarfile.DIRTYPE
        member.mode = 0o755
        member.mtime = 946684800
        return member, None

    def symlink(self, name: str, target: str) -> tuple[tarfile.TarInfo, None]:
        member = tarfile.TarInfo(name)
        member.type = tarfile.SYMTYPE
        member.linkname = target
        member.mode = 0o777
        member.mtime = 946684800
        return member, None

    def run_filter(
        self, source: pathlib.Path, archive: bytes, *options: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(source), *options],
            input=archive,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def names(self, archive: bytes) -> list[str]:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as result:
            return result.getnames()

    def test_unmodified_source_reproduces_dotfile_mismatch(self) -> None:
        archive = self.archive_bytes([self.regular("./.secret")])
        expected_exclude = self.run_filter(
            self.source, archive, "--path-exclude=/.secret"
        )
        wrong_exclude = self.run_filter(
            self.source, archive, "--path-exclude=/secret"
        )
        self.assertEqual(expected_exclude.returncode, 0)
        self.assertEqual(wrong_exclude.returncode, 0)
        self.assertEqual(self.names(expected_exclude.stdout), ["./.secret"])
        self.assertEqual(self.names(wrong_exclude.stdout), [])

    def test_candidate_matches_dotfiles_without_stripping_filename_dots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-path-dotfile-") as td:
            candidate = self.prepare_candidate(pathlib.Path(td))
            archive = self.archive_bytes([self.regular("./.secret")])

            expected_exclude = self.run_filter(
                candidate, archive, "--path-exclude=/.secret"
            )
            wrong_exclude = self.run_filter(
                candidate, archive, "--path-exclude=/secret"
            )
            self.assertEqual(expected_exclude.returncode, 0)
            self.assertEqual(wrong_exclude.returncode, 0)
            self.assertEqual(self.names(expected_exclude.stdout), [])
            self.assertEqual(self.names(wrong_exclude.stdout), ["./.secret"])

            traversal = self.archive_bytes([self.regular("../etc/passwd")])
            filtered = self.run_filter(
                candidate, traversal, "--path-exclude=/etc/passwd"
            )
            self.assertEqual(filtered.returncode, 0)
            self.assertEqual(self.names(filtered.stdout), ["../etc/passwd"])

    def test_candidate_retains_parent_directory_for_reincluded_descendant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-path-parent-") as td:
            candidate = self.prepare_candidate(pathlib.Path(td))
            archive = self.archive_bytes(
                [self.directory("./foo"), self.regular("./foo/bar")]
            )
            options = ("--path-exclude=/*", "--path-include=/foo/bar")

            negative = self.run_filter(self.source, archive, *options)
            repaired = self.run_filter(candidate, archive, *options)
            self.assertEqual(negative.returncode, 0)
            self.assertEqual(repaired.returncode, 0)
            self.assertNotIn("./foo", self.names(negative.stdout))
            self.assertEqual(self.names(repaired.stdout), ["./foo", "./foo/bar"])

    def test_candidate_retains_symlink_parent_for_reincluded_descendant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-path-symlink-") as td:
            candidate = self.prepare_candidate(pathlib.Path(td))
            archive = self.archive_bytes(
                [
                    self.symlink("./pivot", "target"),
                    self.regular("./pivot/leaf"),
                ]
            )
            repaired = self.run_filter(
                candidate,
                archive,
                "--path-exclude=/*",
                "--path-include=/pivot/leaf",
            )
            self.assertEqual(
                repaired.returncode,
                0,
                repaired.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(fileobj=io.BytesIO(repaired.stdout), mode="r:*") as result:
                members = result.getmembers()
                self.assertEqual([member.name for member in members], ["./pivot", "./pivot/leaf"])
                self.assertTrue(members[0].issym())
                self.assertEqual(members[0].linkname, "target")


if __name__ == "__main__":
    unittest.main()
