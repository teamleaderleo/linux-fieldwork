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
SOURCE = ROOT / "upstream/mmdebstrap/tarfilter"
SOURCE_BYTES = SOURCE.read_bytes()
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
        if shutil.which("patch") is None or shutil.which("tar") is None:
            raise unittest.SkipTest("patch and GNU tar are required")

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
        if completed.returncode != 0:
            raise AssertionError(output)
        if "fuzz" in output.lower():
            raise AssertionError(output)

    def compile_source(self, source: pathlib.Path) -> None:
        compiled = subprocess.run(
            [sys.executable, "-m", "py_compile", str(source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

    def prepare_predecessor(self, root: pathlib.Path) -> pathlib.Path:
        tree = root / "candidate"
        destination = tree / "upstream/mmdebstrap/tarfilter"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(SOURCE_BYTES)
        self.apply_patch(tree, TRANSFORM_PATCH)
        self.apply_patch(tree, PREDECESSOR_PATCH)
        self.compile_source(destination)
        return destination

    def apply_candidate(self, tree: pathlib.Path) -> pathlib.Path:
        self.apply_patch(tree, CANDIDATE_PATCH)
        source = tree / "upstream/mmdebstrap/tarfilter"
        self.compile_source(source)
        return source

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

    @staticmethod
    def false_rejection_archive() -> bytes:
        output = io.BytesIO()
        payload = b"final-name-target\n"
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            retained = tarfile.TarInfo("prefix/base")
            retained.size = len(payload)
            retained.mtime = 946684800
            archive.addfile(retained, io.BytesIO(payload))

            excluded = tarfile.TarInfo("root/base")
            excluded.type = tarfile.SYMTYPE
            excluded.linkname = "missing"
            excluded.mtime = 946684800
            archive.addfile(excluded)

            peer = tarfile.TarInfo("root/peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "root/base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    @staticmethod
    def expected_false_rejection_output() -> bytes:
        output = io.BytesIO()
        payload = b"final-name-target\n"
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            retained = tarfile.TarInfo("base")
            retained.size = len(payload)
            retained.mtime = 946684800
            archive.addfile(retained, io.BytesIO(payload))

            peer = tarfile.TarInfo("peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    @staticmethod
    def false_acceptance_archive() -> bytes:
        output = io.BytesIO()
        payload = b"excluded-target\n"
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            excluded = tarfile.TarInfo("root/base")
            excluded.size = len(payload)
            excluded.mtime = 946684800
            archive.addfile(excluded, io.BytesIO(payload))

            peer = tarfile.TarInfo("prefix/peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "prefix/root/base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    @staticmethod
    def genuine_removed_target_archive() -> bytes:
        output = io.BytesIO()
        payload = b"genuine-removed-target\n"
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            excluded = tarfile.TarInfo("root/base")
            excluded.size = len(payload)
            excluded.mtime = 946684800
            archive.addfile(excluded, io.BytesIO(payload))

            peer = tarfile.TarInfo("root/peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "root/base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    @staticmethod
    def strip_dropped_target_archive() -> bytes:
        output = io.BytesIO()
        payload = b"strip-dropped-target\n"
        with tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as archive:
            dropped = tarfile.TarInfo("base")
            dropped.size = len(payload)
            dropped.mtime = 946684800
            archive.addfile(dropped, io.BytesIO(payload))

            excluded = tarfile.TarInfo("base")
            excluded.type = tarfile.SYMTYPE
            excluded.linkname = "missing"
            excluded.mtime = 946684800
            archive.addfile(excluded)

            peer = tarfile.TarInfo("root/peer")
            peer.type = tarfile.LNKTYPE
            peer.linkname = "base"
            peer.mtime = 946684800
            archive.addfile(peer)
        return output.getvalue()

    def test_final_identity_accepts_retained_rewritten_target(self) -> None:
        archive = self.false_rejection_archive()
        options = ("--type-exclude=SYMTYPE", "--strip-components=1")

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-false-reject-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)
            result = self.run_filter(predecessor, archive, *options)

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "root/peer -> root/base",
                result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(result.stdout),
                {"base": (tarfile.REGTYPE, "")},
            )
            partial_extract, partial_root = self.extract(
                result.stdout, root, "predecessor-partial"
            )
            self.assertEqual(
                partial_extract.returncode,
                0,
                partial_extract.stdout + partial_extract.stderr,
            )
            self.assertEqual(
                (partial_root / "base").read_bytes(), b"final-name-target\n"
            )

            expected = self.expected_false_rejection_output()
            expected_extract, expected_root = self.extract(
                expected, root, "expected-valid"
            )
            self.assertEqual(
                expected_extract.returncode,
                0,
                expected_extract.stdout + expected_extract.stderr,
            )
            self.assertEqual(
                (expected_root / "base").stat().st_ino,
                (expected_root / "peer").stat().st_ino,
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

    def test_final_identity_rejects_missing_rewritten_target(self) -> None:
        archive = self.false_acceptance_archive()
        options = ("--type-exclude=REGTYPE", "--strip-components=1")

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-false-accept-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)
            result = self.run_filter(predecessor, archive, *options)

            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(result.stdout),
                {"peer": (tarfile.LNKTYPE, "root/base")},
            )
            extracted, destination = self.extract(
                result.stdout, root, "predecessor-broken"
            )
            self.assertNotEqual(extracted.returncode, 0)
            self.assertIn("root/base", extracted.stderr)
            self.assertFalse((destination / "root/base").exists())
            self.assertFalse((destination / "peer").exists())

            candidate = self.apply_candidate(root / "candidate")
            rejected = self.run_filter(candidate, archive, *options)
            self.assertEqual(rejected.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "prefix/peer -> prefix/root/base",
                rejected.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(self.member_map(rejected.stdout), {})
            extracted, destination = self.extract(
                rejected.stdout, root, "candidate-rejected"
            )
            self.assertEqual(
                extracted.returncode, 0, extracted.stdout + extracted.stderr
            )
            self.assertEqual(list(destination.rglob("*")), [])

    def test_genuine_removed_target_remains_rejected(self) -> None:
        archive = self.genuine_removed_target_archive()
        options = ("--type-exclude=REGTYPE",)

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-final-name-genuine-"
        ) as td:
            root = pathlib.Path(td)
            predecessor = self.prepare_predecessor(root)
            predecessor_result = self.run_filter(predecessor, archive, *options)
            self.assertEqual(predecessor_result.returncode, 1)
            self.assertEqual(self.member_map(predecessor_result.stdout), {})

            candidate = self.apply_candidate(root / "candidate")
            candidate_result = self.run_filter(candidate, archive, *options)
            self.assertEqual(candidate_result.returncode, 1)
            self.assertIn(
                "hard-link target excluded by type filter: "
                "root/peer -> root/base",
                candidate_result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(self.member_map(candidate_result.stdout), {})

    def test_strip_dropped_target_and_link_produce_empty_archive(self) -> None:
        archive = self.strip_dropped_target_archive()
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
            extracted, destination = self.extract(
                candidate_result.stdout, root, "candidate-strip-drop"
            )
            self.assertEqual(
                extracted.returncode, 0, extracted.stdout + extracted.stderr
            )
            self.assertEqual(list(destination.rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
