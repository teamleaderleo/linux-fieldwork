import errno
import hashlib
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Callable


SOURCE_DATE_EPOCH = 1_700_000_000
OLDER_DIRECTORY_MTIME = SOURCE_DATE_EPOCH - 100_000
NEWER_DIRECTORY_MTIME = SOURCE_DATE_EPOCH + 100_000
PACKAGE_FILE_MTIME = SOURCE_DATE_EPOCH - 50_000
SYMLINK_MTIME = SOURCE_DATE_EPOCH - 75_000
FOREIGN_DIRECTORY_MTIME = SOURCE_DATE_EPOCH - 125_000
XATTR_NAME = b"user.linux-fieldwork"
XATTR_VALUE = b"directory-mtime-control"
SPARSE_SIZE = 4 * 1024 * 1024
SPARSE_HEAD = b"sparse-head\n"
SPARSE_TAIL = b"sparse-tail\n"


def real_directories(
    root: Path,
    *,
    lstat: Callable[[os.PathLike[str] | str], os.stat_result] = os.lstat,
) -> list[Path]:
    """Return real directories on the root device without following symlinks."""

    root_info = lstat(root)
    if not stat.S_ISDIR(root_info.st_mode):
        raise ValueError(f"normalization root is not a directory: {root}")
    root_device = root_info.st_dev
    result = [root]

    for current_raw, dirnames, _filenames in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_raw)
        retained: list[str] = []
        for name in dirnames:
            candidate = current / name
            info = lstat(candidate)
            if not stat.S_ISDIR(info.st_mode):
                continue
            if info.st_dev != root_device:
                continue
            retained.append(name)
            result.append(candidate)
        dirnames[:] = retained

    return result


def make_tree(root: Path, directory_mtime: int) -> None:
    payload = root / "usr" / "share" / "demo" / "payload"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"same bytes\n")
    os.utime(payload, (PACKAGE_FILE_MTIME, PACKAGE_FILE_MTIME))

    for directory in sorted(
        real_directories(root), key=lambda path: len(path.parts), reverse=True
    ):
        os.utime(directory, (directory_mtime, directory_mtime), follow_symlinks=False)


def normalize_directory_mtimes(
    root: Path,
    timestamp: int,
    *,
    lstat: Callable[[os.PathLike[str] | str], os.stat_result] = os.lstat,
) -> None:
    for directory in real_directories(root, lstat=lstat):
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
        "--xattrs",
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


def archive_member(archive: Path, suffix: str) -> tarfile.TarInfo:
    with tarfile.open(archive, "r:*") as tar:
        matches = [member for member in tar if member.name.endswith(suffix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one archive member ending in {suffix!r}")
    return matches[0]


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

    def test_directory_normalization_preserves_symlink_hardlink_and_outside_target(self) -> None:
        outside = self.root / "outside-target"
        outside.mkdir()
        outside_payload = outside / "sentinel"
        outside_payload.write_bytes(b"outside bytes\n")
        os.utime(outside_payload, (PACKAGE_FILE_MTIME, PACKAGE_FILE_MTIME))
        os.utime(outside, (PACKAGE_FILE_MTIME, PACKAGE_FILE_MTIME))

        links: list[Path] = []
        for tree in (self.root_mode, self.chrootless):
            demo = tree / "usr" / "share" / "demo"
            payload = demo / "payload"
            hardlink = demo / "zz-payload-hardlink"
            os.link(payload, hardlink)
            link = demo / "external-directory-link"
            link.symlink_to(outside, target_is_directory=True)
            try:
                os.utime(
                    link,
                    (SYMLINK_MTIME, SYMLINK_MTIME),
                    follow_symlinks=False,
                )
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink timestamp control unavailable: {error}")
            links.append(link)

        outside_directory_before = int(outside.stat().st_mtime)
        outside_payload_before = int(outside_payload.stat().st_mtime)

        normalize_directory_mtimes(self.root_mode, SOURCE_DATE_EPOCH)
        normalize_directory_mtimes(self.chrootless, SOURCE_DATE_EPOCH)

        for tree, link in zip((self.root_mode, self.chrootless), links):
            demo = tree / "usr" / "share" / "demo"
            payload = demo / "payload"
            hardlink = demo / "zz-payload-hardlink"
            self.assertEqual(int(link.lstat().st_mtime), SYMLINK_MTIME)
            self.assertEqual(int(payload.stat().st_mtime), PACKAGE_FILE_MTIME)
            self.assertEqual(int(hardlink.stat().st_mtime), PACKAGE_FILE_MTIME)
            self.assertEqual(payload.stat().st_ino, hardlink.stat().st_ino)

        self.assertEqual(int(outside.stat().st_mtime), outside_directory_before)
        self.assertEqual(int(outside_payload.stat().st_mtime), outside_payload_before)

        root_archive, chrootless_archive = self.archive_pair("links", clamp=True)
        self.assertEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())
        manifest = archive_manifest(root_archive)
        symlink = next(
            row for row in manifest if str(row[0]).endswith("/external-directory-link")
        )
        hardlink = next(
            row for row in manifest if str(row[0]).endswith("/zz-payload-hardlink")
        )
        self.assertEqual(symlink[1], tarfile.SYMTYPE)
        self.assertEqual(symlink[6], SYMLINK_MTIME)
        self.assertEqual(symlink[7], str(outside))
        self.assertEqual(hardlink[1], tarfile.LNKTYPE)
        self.assertTrue(str(hardlink[7]).endswith("/payload"))

    def test_directory_normalization_prunes_foreign_device_before_descent(self) -> None:
        preserved: dict[Path, tuple[int, int]] = {}

        for tree in (self.root_mode, self.chrootless):
            foreign = tree / "usr" / "share" / "foreign-device"
            nested = foreign / "nested"
            sentinel = nested / "sentinel"
            nested.mkdir(parents=True)
            sentinel.write_bytes(b"foreign bytes\n")
            os.utime(sentinel, (PACKAGE_FILE_MTIME, PACKAGE_FILE_MTIME))
            os.utime(nested, (FOREIGN_DIRECTORY_MTIME, FOREIGN_DIRECTORY_MTIME))
            os.utime(foreign, (FOREIGN_DIRECTORY_MTIME, FOREIGN_DIRECTORY_MTIME))
            preserved[tree] = (
                int(foreign.stat().st_mtime),
                int(sentinel.stat().st_mtime),
            )

            root_device = os.lstat(tree).st_dev
            calls: list[Path] = []

            def fake_lstat(path: os.PathLike[str] | str) -> os.stat_result:
                candidate = Path(path)
                calls.append(candidate)
                info = os.lstat(candidate)
                if candidate == foreign:
                    return SimpleNamespace(
                        st_mode=info.st_mode,
                        st_dev=root_device + 1,
                    )
                return info

            normalize_directory_mtimes(
                tree,
                SOURCE_DATE_EPOCH,
                lstat=fake_lstat,
            )

            self.assertEqual(int(foreign.stat().st_mtime), preserved[tree][0])
            self.assertEqual(int(nested.stat().st_mtime), FOREIGN_DIRECTORY_MTIME)
            self.assertEqual(int(sentinel.stat().st_mtime), preserved[tree][1])
            self.assertNotIn(nested, calls)
            self.assertNotIn(sentinel, calls)

            ordinary = tree / "usr" / "share" / "demo"
            self.assertEqual(int(ordinary.stat().st_mtime), SOURCE_DATE_EPOCH)

        root_archive, chrootless_archive = self.archive_pair("device", clamp=True)
        self.assertEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())

    def test_directory_normalization_preserves_user_xattrs(self) -> None:
        if not hasattr(os, "setxattr"):
            self.skipTest("Python xattr APIs are unavailable")

        controlled: list[tuple[Path, Path]] = []
        try:
            for tree in (self.root_mode, self.chrootless):
                directory = tree / "usr" / "share" / "demo"
                payload = directory / "payload"
                os.setxattr(directory, XATTR_NAME, XATTR_VALUE)
                os.setxattr(payload, XATTR_NAME, XATTR_VALUE)
                controlled.append((directory, payload))
        except OSError as error:
            if error.errno in {
                errno.ENOTSUP,
                getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
                errno.EPERM,
            }:
                self.skipTest(f"user xattrs unavailable: {error}")
            raise

        normalize_directory_mtimes(self.root_mode, SOURCE_DATE_EPOCH)
        normalize_directory_mtimes(self.chrootless, SOURCE_DATE_EPOCH)

        for directory, payload in controlled:
            self.assertEqual(os.getxattr(directory, XATTR_NAME), XATTR_VALUE)
            self.assertEqual(os.getxattr(payload, XATTR_NAME), XATTR_VALUE)
            self.assertEqual(int(payload.stat().st_mtime), PACKAGE_FILE_MTIME)

        root_archive, chrootless_archive = self.archive_pair("xattrs", clamp=True)
        self.assertEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())
        key = "SCHILY.xattr." + XATTR_NAME.decode()
        for suffix in ("/usr/share/demo", "/usr/share/demo/payload"):
            member = archive_member(root_archive, suffix)
            self.assertEqual(member.pax_headers.get(key), XATTR_VALUE.decode())

    def test_directory_normalization_preserves_sparse_source_file(self) -> None:
        expected_hash: str | None = None
        expected_blocks: int | None = None

        for tree in (self.root_mode, self.chrootless):
            sparse = tree / "usr" / "share" / "demo" / "sparse-payload"
            with sparse.open("wb") as stream:
                stream.write(SPARSE_HEAD)
                stream.seek(SPARSE_SIZE - len(SPARSE_TAIL))
                stream.write(SPARSE_TAIL)
            os.utime(sparse, (PACKAGE_FILE_MTIME, PACKAGE_FILE_MTIME))
            info = sparse.stat()
            if info.st_blocks * 512 >= info.st_size:
                self.skipTest("fixture filesystem did not retain sparse allocation")
            digest = hashlib.sha256(sparse.read_bytes()).hexdigest()
            if expected_hash is None:
                expected_hash = digest
                expected_blocks = info.st_blocks
            else:
                self.assertEqual(digest, expected_hash)
                self.assertEqual(info.st_blocks, expected_blocks)

        normalize_directory_mtimes(self.root_mode, SOURCE_DATE_EPOCH)
        normalize_directory_mtimes(self.chrootless, SOURCE_DATE_EPOCH)

        for tree in (self.root_mode, self.chrootless):
            sparse = tree / "usr" / "share" / "demo" / "sparse-payload"
            info = sparse.stat()
            self.assertEqual(info.st_size, SPARSE_SIZE)
            self.assertEqual(info.st_blocks, expected_blocks)
            self.assertEqual(int(info.st_mtime), PACKAGE_FILE_MTIME)
            self.assertEqual(hashlib.sha256(sparse.read_bytes()).hexdigest(), expected_hash)

        root_archive, chrootless_archive = self.archive_pair("sparse", clamp=True)
        self.assertEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())
        sparse_member = next(
            row
            for row in archive_manifest(root_archive)
            if str(row[0]).endswith("/sparse-payload")
        )
        self.assertEqual(sparse_member[5], SPARSE_SIZE)
        self.assertEqual(sparse_member[6], PACKAGE_FILE_MTIME)
        self.assertEqual(sparse_member[8], expected_hash)

    def test_comparison_only_normalization_explains_but_does_not_fix_output(self) -> None:
        root_archive, chrootless_archive = self.archive_pair("comparison", clamp=True)

        self.assertEqual(
            normalize_directory_manifest(archive_manifest(root_archive)),
            normalize_directory_manifest(archive_manifest(chrootless_archive)),
        )
        self.assertNotEqual(root_archive.read_bytes(), chrootless_archive.read_bytes())


if __name__ == "__main__":
    unittest.main()
