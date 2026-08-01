from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_BLOB = "ad776167a8473d5d15dbe22e850f4f6db35cf278"
TRANSFORM_PATCH = ROOT / (
    "investigations/tarfilter-transform-target-scopes/"
    "tarfilter-transform-target-scopes.patch"
)
PREDECESSOR_PATCH = ROOT / (
    "upstream-packets/units/16-tarfilter-type-hardlinks/patches/"
    "0001-compose-pr310-predecessor-on-transform-carrier.patch"
)
CANDIDATE_PATCH = ROOT / (
    "upstream-packets/units/16-tarfilter-type-hardlinks/patches/"
    "0002-use-rewritten-identities-for-type-hardlinks.patch"
)


class TarfilterTypeExcludedFinalNameIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("git", "patch", "tar"):
            if shutil.which(command) is None:
                raise unittest.SkipTest(f"{command} is required")
        cls.source_bytes = subprocess.run(
            ["git", "cat-file", "blob", SOURCE_BLOB],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        ).stdout

    @staticmethod
    def apply_patch(tree: pathlib.Path, patch_path: pathlib.Path) -> None:
        completed = subprocess.run(
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
        output = completed.stdout + completed.stderr
        if completed.returncode != 0 or "fuzz" in output.lower():
            raise AssertionError(output)

    def compile_source(self, source: pathlib.Path) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "py_compile", str(source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def prepare_predecessor(self, root: pathlib.Path) -> pathlib.Path:
        tree = root / "candidate"
        source = tree / "upstream/mmdebstrap/tarfilter"
        source.parent.mkdir(parents=True)
        source.write_bytes(self.source_bytes)
        self.apply_patch(tree, TRANSFORM_PATCH)
        self.apply_patch(tree, PREDECESSOR_PATCH)
        self.compile_source(source)
        return source

    def apply_candidate(self, tree: pathlib.Path) -> pathlib.Path:
        self.apply_patch(tree, CANDIDATE_PATCH)
        source = tree / "upstream/mmdebstrap/tarfilter"
        self.compile_source(source)
        return source

    @staticmethod
    def archive_bytes(
        entries: tuple[tuple[str, bytes, str, bytes], ...]
    ) -> bytes:
        output = io.BytesIO()
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            for name, member_type, linkname, payload in entries:
                member = tarfile.TarInfo(name)
                member.type = member_type
                member.linkname = linkname
                member.mtime = 946684800
                if member_type in (tarfile.REGTYPE, tarfile.AREGTYPE):
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                else:
                    archive.addfile(member)
        return output.getvalue()

    @staticmethod
    def run_filter(
        source: pathlib.Path, archive: bytes, *options: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(source), *options],
            input=archive,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

    @staticmethod
    def member_map(archive: bytes) -> dict[str, tuple[bytes, str]]:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
            return {
                member.name: (member.type, member.linkname)
                for member in handle
            }

    @staticmethod
    def extract(
        archive: bytes, root: pathlib.Path, label: str
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
        archive_path = root / f"{label}.tar"
        destination = root / label
        archive_path.write_bytes(archive)
        destination.mkdir()
        completed = subprocess.run(
            ["tar", "-xf", str(archive_path), "-C", str(destination)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        return completed, destination

    def assert_empty_extract(
        self, archive: bytes, root: pathlib.Path, label: str
    ) -> None:
        completed, destination = self.extract(archive, root, label)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(list(destination.rglob("*")), [])

    def test_final_identity_accepts_retained_rewritten_target(self) -> None:
        archive = self.archive_bytes(
            (
                ("prefix/base", tarfile.REGTYPE, "", b"final-name-target\n"),
                ("root/base", tarfile.SYMTYPE, "missing", b""),
                ("root/peer", tarfile.LNKTYPE, "root/base", b""),
            )
        )
        options = ("--type-exclude=SYMTYPE", "--strip-components=1")

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-false-reject-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)
            rejected = self.run_filter(predecessor, archive, *options)
            self.assertEqual(rejected.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "root/peer -> root/base",
                rejected.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(rejected.stdout),
                {"base": (tarfile.REGTYPE, "")},
            )

            candidate = self.apply_candidate(root / "candidate")
            accepted = self.run_filter(candidate, archive, *options)
            self.assertEqual(
                accepted.returncode,
                0,
                accepted.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(accepted.stdout),
                {
                    "base": (tarfile.REGTYPE, ""),
                    "peer": (tarfile.LNKTYPE, "base"),
                },
            )
            extracted, destination = self.extract(
                accepted.stdout, root, "candidate-valid"
            )
            self.assertEqual(
                extracted.returncode, 0, extracted.stdout + extracted.stderr
            )
            self.assertEqual(
                (destination / "base").stat().st_ino,
                (destination / "peer").stat().st_ino,
            )

    def test_strip_break_preexists_type_exclusion_and_alias_candidate_rejects(self) -> None:
        archive = self.archive_bytes(
            (
                ("root/base", tarfile.REGTYPE, "", b"excluded-target\n"),
                (
                    "prefix/peer",
                    tarfile.LNKTYPE,
                    "prefix/root/base",
                    b"",
                ),
            )
        )

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-false-accept-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)

            unfiltered = self.run_filter(
                predecessor, archive, "--strip-components=1"
            )
            self.assertEqual(
                unfiltered.returncode,
                0,
                unfiltered.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(unfiltered.stdout),
                {
                    "base": (tarfile.REGTYPE, ""),
                    "peer": (tarfile.LNKTYPE, "root/base"),
                },
            )
            direct_extract, _ = self.extract(
                unfiltered.stdout, root, "unfiltered-broken"
            )
            self.assertNotEqual(direct_extract.returncode, 0)

            filtered = self.run_filter(
                predecessor,
                archive,
                "--type-exclude=REGTYPE",
                "--strip-components=1",
            )
            self.assertEqual(filtered.returncode, 0)
            self.assertEqual(
                self.member_map(filtered.stdout),
                {"peer": (tarfile.LNKTYPE, "root/base")},
            )

            candidate = self.apply_candidate(root / "candidate")
            candidate_result = self.run_filter(
                candidate,
                archive,
                "--type-exclude=REGTYPE",
                "--strip-components=1",
            )
            self.assertEqual(candidate_result.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "prefix/peer -> prefix/root/base",
                candidate_result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(self.member_map(candidate_result.stdout), {})
            self.assert_empty_extract(
                candidate_result.stdout, root, "candidate-rejected"
            )

    def test_genuine_removed_target_remains_rejected(self) -> None:
        archive = self.archive_bytes(
            (
                ("root/base", tarfile.REGTYPE, "", b"removed-target\n"),
                ("root/peer", tarfile.LNKTYPE, "root/base", b""),
            )
        )

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-genuine-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)
            predecessor_result = self.run_filter(
                predecessor, archive, "--type-exclude=REGTYPE"
            )
            self.assertEqual(predecessor_result.returncode, 1)
            self.assertEqual(self.member_map(predecessor_result.stdout), {})

            candidate = self.apply_candidate(root / "candidate")
            candidate_result = self.run_filter(
                candidate, archive, "--type-exclude=REGTYPE"
            )
            self.assertEqual(candidate_result.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "root/peer -> root/base",
                candidate_result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(self.member_map(candidate_result.stdout), {})

    def test_strip_dropped_target_and_link_produce_empty_archive(self) -> None:
        archive = self.archive_bytes(
            (
                ("base", tarfile.REGTYPE, "", b"strip-dropped-target\n"),
                ("base", tarfile.SYMTYPE, "missing", b""),
                ("root/peer", tarfile.LNKTYPE, "base", b""),
            )
        )
        options = ("--type-exclude=SYMTYPE", "--strip-components=1")

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-strip-drop-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)
            predecessor_result = self.run_filter(predecessor, archive, *options)
            self.assertEqual(predecessor_result.returncode, 1)
            self.assertEqual(self.member_map(predecessor_result.stdout), {})

            candidate = self.apply_candidate(root / "candidate")
            candidate_result = self.run_filter(candidate, archive, *options)
            self.assertEqual(
                candidate_result.returncode,
                0,
                candidate_result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(self.member_map(candidate_result.stdout), {})
            self.assert_empty_extract(
                candidate_result.stdout, root, "candidate-strip-drop"
            )


if __name__ == "__main__":
    unittest.main()
