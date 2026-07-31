import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCH = (
    REPO_ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime"
    / "0002-normalize-directory-mtimes-by-descriptor.patch"
)
SOURCE_DATE_EPOCH = 1_700_000_000
PACKAGE_MTIME = SOURCE_DATE_EPOCH - 50_000
OUTSIDE_MTIME = SOURCE_DATE_EPOCH - 75_000
DIRECTORY_ATIME = SOURCE_DATE_EPOCH - 125_000


def apply_candidate(root: Path) -> Path:
    work = root / "source"
    work.mkdir()
    target = work / "mmdebstrap"
    shutil.copy2(SOURCE, target)
    result = subprocess.run(
        [
            "patch",
            "--batch",
            "--fuzz=0",
            "--no-backup-if-mismatch",
            "-p1",
            "-i",
            str(PATCH),
        ],
        cwd=work,
        check=True,
        capture_output=True,
        text=True,
    )
    self_report = result.stdout + result.stderr
    if "fuzz" in self_report.lower() or "offset" in self_report.lower():
        raise AssertionError(self_report)
    return target


def extract_helpers(source: str) -> str:
    match = re.search(
        r"(sub directory_mount_id \{.*?\n\})\n\nsub approx_disk_usage",
        source,
        re.S,
    )
    if match is None:
        raise AssertionError("descriptor helpers not found exactly once")
    return match.group(1)


def run_helpers(
    helpers: str, body: str, *args: object
) -> subprocess.CompletedProcess[str]:
    prefix = """use strict;
use warnings;
use Fcntl qw(O_RDONLY O_DIRECTORY);
sub error { die "@_\\n"; }
"""
    return subprocess.run(
        ["perl", "-e", prefix + helpers + "\n" + body, *map(str, args)],
        capture_output=True,
        text=True,
    )


def make_tree(root: Path, directory_mtime: int) -> None:
    payload = root / "usr" / "share" / "demo" / "payload"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"same bytes\n")
    os.utime(payload, (PACKAGE_MTIME, PACKAGE_MTIME))
    peer = payload.with_name("peer")
    os.link(payload, peer)

    directories = [root, *[path for path in root.rglob("*") if path.is_dir()]]
    for directory in sorted(
        directories, key=lambda path: len(path.parts), reverse=True
    ):
        os.utime(directory, (DIRECTORY_ATIME, directory_mtime))


def create_archive(root: Path, archive: Path) -> None:
    subprocess.run(
        [
            "tar",
            "--sort=name",
            f"--mtime=@{SOURCE_DATE_EPOCH}",
            "--clamp-mtime",
            "--numeric-owner",
            "--owner=0",
            "--group=0",
            "--one-file-system",
            "--format=pax",
            "--pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime",
            "-C",
            str(root),
            "-cf",
            str(archive),
            ".",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def archive_manifest(archive: Path) -> list[tuple[object, ...]]:
    result: list[tuple[object, ...]] = []
    with tarfile.open(archive, "r:*") as tar:
        for member in tar:
            digest = None
            if member.isfile():
                stream = tar.extractfile(member)
                if stream is None:
                    raise AssertionError(f"missing stream for {member.name}")
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


@unittest.skipUnless(shutil.which("tar"), "GNU tar is required")
@unittest.skipUnless(sys.platform.startswith("linux"), "Linux descriptor API required")
class DescriptorDirectoryMtimeCandidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = apply_candidate(self.root)
        self.text = self.source.read_text(encoding="utf-8")
        self.helpers = extract_helpers(self.text)

    def test_patch_applies_exactly_and_perl_compiles(self) -> None:
        subprocess.run(
            ["perl", "-c", str(self.source)],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_descriptor_walk_converges_and_preserves_non_directory_metadata(
        self,
    ) -> None:
        root_mode = self.root / "root-mode"
        chrootless = self.root / "chrootless"
        root_mode.mkdir()
        chrootless.mkdir()
        make_tree(root_mode, SOURCE_DATE_EPOCH + 100_000)
        make_tree(chrootless, SOURCE_DATE_EPOCH - 100_000)

        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"outside\n")
        os.utime(outside, (OUTSIDE_MTIME, OUTSIDE_MTIME))
        os.utime(sentinel, (OUTSIDE_MTIME, OUTSIDE_MTIME))

        links: list[Path] = []
        for tree in (root_mode, chrootless):
            link = tree / "usr" / "share" / "demo" / "outside-link"
            link.symlink_to(outside, target_is_directory=True)
            try:
                os.utime(
                    link,
                    (PACKAGE_MTIME, PACKAGE_MTIME),
                    follow_symlinks=False,
                )
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink timestamp control unavailable: {error}")
            links.append(link)

        body = """
sysopen(my $root, $ARGV[0], O_RDONLY | O_DIRECTORY) or die $!;
normalize_directory_mtimes($root, $ARGV[1]);
"""
        for tree in (root_mode, chrootless):
            result = run_helpers(
                self.helpers, body, tree, SOURCE_DATE_EPOCH
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rerun = run_helpers(
                self.helpers, body, tree, SOURCE_DATE_EPOCH
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr)

            for directory in (
                tree,
                tree / "usr",
                tree / "usr" / "share",
                tree / "usr" / "share" / "demo",
            ):
                state = directory.stat()
                self.assertEqual(int(state.st_atime), DIRECTORY_ATIME)
                self.assertEqual(int(state.st_mtime), SOURCE_DATE_EPOCH)

        self.assertEqual(int(outside.stat().st_mtime), OUTSIDE_MTIME)
        self.assertEqual(int(sentinel.stat().st_mtime), OUTSIDE_MTIME)

        for tree, link in zip((root_mode, chrootless), links):
            payload = tree / "usr" / "share" / "demo" / "payload"
            peer = payload.with_name("peer")
            self.assertEqual(int(payload.stat().st_mtime), PACKAGE_MTIME)
            self.assertEqual(int(peer.stat().st_mtime), PACKAGE_MTIME)
            self.assertEqual(payload.stat().st_ino, peer.stat().st_ino)
            self.assertEqual(int(link.lstat().st_mtime), PACKAGE_MTIME)
            self.assertEqual(link.resolve(), outside.resolve())

            if hasattr(os, "setxattr"):
                try:
                    os.setxattr(payload, b"user.lf380", b"preserve")
                    before = os.getxattr(payload, b"user.lf380")
                    rerun = run_helpers(
                        self.helpers, body, tree, SOURCE_DATE_EPOCH
                    )
                    self.assertEqual(rerun.returncode, 0, rerun.stderr)
                    self.assertEqual(os.getxattr(payload, b"user.lf380"), before)
                except OSError:
                    pass

        first = self.root / "root.tar"
        second = self.root / "chrootless.tar"
        create_archive(root_mode, first)
        create_archive(chrootless, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        payload = next(
            row
            for row in archive_manifest(first)
            if str(row[0]).endswith("/payload")
        )
        self.assertEqual(payload[6], PACKAGE_MTIME)

    def test_enumerated_child_replaced_before_open_is_rejected(self) -> None:
        parent = self.root / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()
        outside = self.root / "replacement-outside"
        outside.mkdir()
        os.utime(outside, (OUTSIDE_MTIME, OUTSIDE_MTIME))

        body = """
sysopen(my $parent, $ARGV[0], O_RDONLY | O_DIRECTORY) or die $!;
my $parent_fd = fileno $parent;
opendir(my $dh, "/dev/fd/$parent_fd") or die $!;
my @entries = grep { $_ ne '.' and $_ ne '..' } readdir $dh;
closedir $dh or die $!;
grep { $_ eq 'child' } @entries or die "child was not enumerated";
my $path = "$ARGV[0]/child";
rmdir($path) or die $!;
if ($ARGV[1] eq 'symlink') {
    symlink($ARGV[2], $path) or die $!;
} elsif ($ARGV[1] eq 'regular') {
    open my $replacement, '>', $path or die $!;
    print {$replacement} "regular\\n" or die $!;
    close $replacement or die $!;
    utime($ARGV[3], $ARGV[3], $path) == 1 or die $!;
} else {
    die "unknown replacement mode";
}
my $opened = open_child_directory($parent, 'child');
exit 9 if defined $opened;
"""

        result = run_helpers(
            self.helpers, body, parent, "symlink", outside, PACKAGE_MTIME
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(child.is_symlink())
        self.assertEqual(int(outside.stat().st_mtime), OUTSIDE_MTIME)

        child.unlink()
        child.mkdir()
        result = run_helpers(
            self.helpers, body, parent, "regular", outside, PACKAGE_MTIME
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(child.is_file())
        self.assertEqual(child.read_bytes(), b"regular\n")
        self.assertEqual(int(child.stat().st_mtime), PACKAGE_MTIME)
        self.assertEqual(int(outside.stat().st_mtime), OUTSIDE_MTIME)

    def test_open_descriptor_remains_authority_after_path_replacement(self) -> None:
        parent = self.root / "rename-parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()
        os.utime(child, (PACKAGE_MTIME, PACKAGE_MTIME))
        moved = self.root / "moved-child"
        outside = self.root / "rename-outside"
        outside.mkdir()
        os.utime(outside, (OUTSIDE_MTIME, OUTSIDE_MTIME))

        body = """
sysopen(my $parent, $ARGV[0], O_RDONLY | O_DIRECTORY) or die $!;
my $child = open_child_directory($parent, 'child');
defined $child or die "child not opened";
my @before = stat $child;
rename($ARGV[1], $ARGV[2]) or die $!;
symlink($ARGV[3], $ARGV[1]) or die $!;
utime($before[8], $ARGV[4], $child) == 1 or die $!;
"""
        result = run_helpers(
            self.helpers,
            body,
            parent,
            child,
            moved,
            outside,
            SOURCE_DATE_EPOCH,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(moved.stat().st_atime), PACKAGE_MTIME)
        self.assertEqual(int(moved.stat().st_mtime), SOURCE_DATE_EPOCH)
        self.assertEqual(int(outside.stat().st_mtime), OUTSIDE_MTIME)
        self.assertTrue(child.is_symlink())

    def test_missing_linux_mount_identity_fails_closed(self) -> None:
        mutated = self.helpers.replace(
            'my $fdinfo = "/proc/self/fdinfo/$fd";',
            'my $fdinfo = "/definitely-missing-fieldwork-fdinfo";',
        )
        self.assertNotEqual(mutated, self.helpers)
        body = """
sysopen(my $root, $ARGV[0], O_RDONLY | O_DIRECTORY) or die $!;
directory_mount_id($root);
"""
        result = run_helpers(mutated, body, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read mount identity", result.stderr)

    def test_source_uses_pinned_root_mount_boundary_and_handle_utime(self) -> None:
        call = "normalize_directory_mtimes($rootdir_handle, $mtime);"
        self.assertEqual(self.text.count(call), 1)
        self.assertIn("Fcntl::O_NOFOLLOW()", self.helpers)
        self.assertIn('"/dev/fd/$parent_fd/$entry"', self.helpers)
        self.assertIn(
            "utime($stat[8], $timestamp, $directory_handle)", self.helpers
        )
        self.assertNotIn(
            "utime($timestamp, $timestamp, $directory_handle)", self.helpers
        )
        self.assertNotIn(
            "utime($timestamp, $timestamp, $child_path)", self.helpers
        )
        self.assertIn('"/proc/self/fdinfo/$fd"', self.helpers)
        self.assertIn('-r $fdinfo or error "cannot read mount identity', self.helpers)
        self.assertNotIn("return undef if not -r $fdinfo", self.helpers)
        self.assertIn("next if $childstat[0] != $root_device;", self.helpers)
        self.assertIn(
            "next if $child_mount_id ne $root_mount_id;", self.helpers
        )
        self.assertIn("my %visited;", self.helpers)

        archive_start = self.text.index("('tar', 'squashfs', 'ext2', 'ext4'))")
        call_index = self.text.index(call)
        directory_branch = self.text.index("('directory', 'null'))", call_index)
        self.assertLess(archive_start, call_index)
        self.assertLess(call_index, directory_branch)
        scope = self.text[archive_start:call_index]
        self.assertIn("if (defined $ENV{SOURCE_DATE_EPOCH}", scope)
        self.assertIn("&& $^O eq 'linux'", scope)
        self.assertIn("&& $options->{format} eq 'tar')", scope)


if __name__ == "__main__":
    unittest.main(verbosity=2)
