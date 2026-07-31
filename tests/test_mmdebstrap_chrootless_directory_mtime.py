import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


SOURCE_DATE_EPOCH = 1_700_000_000
OLDER_DIRECTORY_MTIME = SOURCE_DATE_EPOCH - 100_000
NEWER_DIRECTORY_MTIME = SOURCE_DATE_EPOCH + 100_000
PACKAGE_FILE_MTIME = SOURCE_DATE_EPOCH - 50_000


def make_tree(root: Path, directory_mtime: int) -> None:
    payload = root / "usr" / "share" / "demo" / "payload"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"same bytes\n")
    os.utime(payload, (PACKAGE_FILE_MTIME, PACKAGE_FILE_MTIME))

    directories = [root, *[path for path in root.rglob("*") if path.is_dir()]]
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        os.utime(directory, (directory_mtime, directory_mtime), follow_symlinks=False)


def normalize_directory_mtimes(root: Path, timestamp: int) -> None:
    directories = [root, *[path for path in root.rglob("*") if path.is_dir()]]
    for directory in directories:
        os.utime(directory, (timestamp, timestamp), follow_symlinks=False)


def create_archive(root: Path, archive: Path, *, clamp: bool) -> None:
    command = [
        "tar",
        "--sort=name",
        f"--mtime=@{SOURCE_DATE_EPOCH}",
        "--numeric-owner",
        "--owner=0",
        "--group=0",
        "--one-file-system",
        "--format=pax",
        "--pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime",
    ]
    if clamp:
        command.append("--clamp-mtime")
    command.extend(["-C", str(root), "-cf", str(archive), "."])
    subprocess.run(command, check=True, capture_output=True, text=True)


def archive_manifest(archive: Path) -> list[tuple[object, ...]]:
    result: list[tuple[object, ...]] = []
    with tarfile.open(archive, "r:*") as tar:
        for member in tar:
            digest = None
            if member.isfile():
                stream = tar.extractfile(member)
                if stream is None:
                    raise AssertionError(f"missing stream for regular member {member.name}")
                digest = hashlib.sha256(stream.read()).hexdigest()
            result.append(
                (
                    member.name,
                    member.type,
                    member.mode,
                    member.uid,
                    member.gid,
                    member.size,
                    int(member.mtime),
                    member.linkname,
                    digest,
                )
            )
    return result


def normalize_directory_manifest(
    manifest: list[tuple[object, ...]],
) -> list[tuple[object, ...]]:
    return [
        row[:6]
        + ((SOURCE_DATE_EPOCH,) if row[1] == tarfile.DIRTYPE else (row[6],))
        + row[7:]
        for row in manifest
    ]


@unittest.skipUnless(shutil.which("tar"), "GNU tar is required")
class ChrootlessDirectoryMtimePolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root_mode = self.root / "root-mode"
        self.chrootless = self.root / "chrootless"
        self.root_mode.mkdir()
        self.chrootless.mkdir()
        make_tree(self.root_mode, NEWER_DIRECTORY_MTIME)
        make_tree(self.chrootless, OLDER_DIRECTORY_MTIME)

    def archive_pair(self, prefix: str, *, clamp: bool) -> tuple[Path, Path]:
        root_archive = self.root / f"{prefix}-root.tar"
        chrootless_archive = self.root / f"{prefix}-chrootless.tar"
        create_archive(self.root_mode, root_archive, clamp=clamp)
        create_archive(self.chrootless, chrootless_archive, clamp=clamp)
        return root_archive, chrootless_archive

    def test_current_clamp_policy_diverges_only_on_directory_mtimes(self) -> None:
        root_archive, chrootless_archive = self.archive_pair("current", clamp=True)
        root_manifest = archive_manifest(root_archive)
        chrootless_manifest = archive_manifest(chrootless_archive)

        self.assertNotEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())
        self.assertEqual(
            [row[:6] + row[7:] for row in root_manifest],
            [row[:6] + row[7:] for row in chrootless_manifest],
        )

        differences = [
            (root_row, chrootless_row)
            for root_row, chrootless_row in zip(root_manifest, chrootless_manifest)
            if root_row != chrootless_row
        ]
        self.assertTrue(differences)
        self.assertTrue(
            all(
                root_row[1] == tarfile.DIRTYPE
                and chrootless_row[1] == tarfile.DIRTYPE
                for root_row, chrootless_row in differences
            )
        )
        self.assertTrue(
            all(
                root_row[6] == SOURCE_DATE_EPOCH
                and chrootless_row[6] == OLDER_DIRECTORY_MTIME
                for root_row, chrootless_row in differences
            )
        )

    def test_full_normalization_converges_but_discards_package_file_mtime(self) -> None:
        root_archive, chrootless_archive = self.archive_pair("full", clamp=False)

        self.assertEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())
        payload = next(
            row for row in archive_manifest(root_archive) if str(row[0]).endswith("/payload")
        )
        self.assertEqual(payload[6], SOURCE_DATE_EPOCH)
        self.assertNotEqual(payload[6], PACKAGE_FILE_MTIME)

    def test_directory_only_pre_tar_normalization_converges_and_preserves_file_mtime(self) -> None:
        normalize_directory_mtimes(self.root_mode, SOURCE_DATE_EPOCH)
        normalize_directory_mtimes(self.chrootless, SOURCE_DATE_EPOCH)
        root_archive, chrootless_archive = self.archive_pair("directories", clamp=True)

        self.assertEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())
        manifest = archive_manifest(root_archive)
        payload = next(row for row in manifest if str(row[0]).endswith("/payload"))
        self.assertEqual(payload[6], PACKAGE_FILE_MTIME)
        self.assertTrue(
            all(row[6] == SOURCE_DATE_EPOCH for row in manifest if row[1] == tarfile.DIRTYPE)
        )

    def test_comparison_only_normalization_explains_but_does_not_fix_output(self) -> None:
        root_archive, chrootless_archive = self.archive_pair("comparison", clamp=True)

        self.assertEqual(
            normalize_directory_manifest(archive_manifest(root_archive)),
            normalize_directory_manifest(archive_manifest(chrootless_archive)),
        )
        self.assertNotEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())


if __name__ == "__main__":
    unittest.main()
