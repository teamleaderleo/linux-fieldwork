import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_SOURCE = REPO_ROOT / 'upstream/mmdebstrap/mmdebstrap'
PATCH = (
    REPO_ROOT
    / 'investigations/mmdebstrap-chrootless-directory-mtime/0001-normalize-directory-mtimes.patch'
)
EPOCH = 1_700_000_000
FILE_TIME = EPOCH - 50_000
OUTSIDE_TIME = EPOCH - 75_000


def apply_candidate(directory: Path) -> Path:
    source = directory / 'mmdebstrap'
    shutil.copy2(REPO_SOURCE, source)
    subprocess.run(
        ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-i', str(PATCH)],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return source


def extract_helper(source: str) -> str:
    match = re.search(
        r'(sub normalize_directory_mtimes \{.*?\n\})\n\nsub approx_disk_usage',
        source,
        re.S,
    )
    if match is None:
        raise AssertionError('candidate helper not found exactly once')
    return match.group(1)


def run_helper(helper: str, root: Path, timestamp: int) -> None:
    script = f'''use strict;
use warnings;
use File::Find;
sub error {{ die "@_\\n"; }}
{helper}
normalize_directory_mtimes($ARGV[0], $ARGV[1]);
'''
    subprocess.run(
        ['perl', '-e', script, str(root), str(timestamp)],
        check=True,
        capture_output=True,
        text=True,
    )


class CandidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def test_patch_applies_without_fuzz_and_perl_compiles(self) -> None:
        source = apply_candidate(self.base)
        subprocess.run(['perl', '-c', str(source)], check=True, capture_output=True, text=True)

    def test_helper_changes_only_in_tree_directories_and_is_repeatable(self) -> None:
        source = apply_candidate(self.base)
        helper = extract_helper(source.read_text())

        root = self.base / 'root'
        nested = root / 'usr' / 'share' / 'demo'
        nested.mkdir(parents=True)
        payload = nested / 'payload'
        payload.write_bytes(b'payload\n')
        peer = nested / 'peer'
        os.link(payload, peer)
        os.utime(payload, (FILE_TIME, FILE_TIME))

        outside = self.base / 'outside'
        outside.mkdir()
        os.utime(outside, (OUTSIDE_TIME, OUTSIDE_TIME))
        (nested / 'outside-link').symlink_to(outside, target_is_directory=True)

        xattr_supported = hasattr(os, 'setxattr')
        if xattr_supported:
            try:
                os.setxattr(payload, b'user.lf380', b'preserve')
            except OSError:
                xattr_supported = False

        before_inode = payload.stat().st_ino
        before_nlink = payload.stat().st_nlink
        for directory in [root, root / 'usr', root / 'usr/share', nested]:
            os.utime(directory, (EPOCH - 100_000, EPOCH - 100_000))

        run_helper(helper, root, EPOCH)
        run_helper(helper, root, EPOCH)

        self.assertEqual(outside.stat().st_mtime_ns, OUTSIDE_TIME * 1_000_000_000)
        self.assertTrue((nested / 'outside-link').is_symlink())
        self.assertEqual(payload.stat().st_mtime_ns, FILE_TIME * 1_000_000_000)
        self.assertEqual(peer.stat().st_mtime_ns, FILE_TIME * 1_000_000_000)
        self.assertEqual(payload.stat().st_ino, before_inode)
        self.assertEqual(payload.stat().st_nlink, before_nlink)
        self.assertEqual(payload.read_bytes(), b'payload\n')
        if xattr_supported:
            self.assertEqual(os.getxattr(payload, b'user.lf380'), b'preserve')
        for directory in [root, root / 'usr', root / 'usr/share', nested]:
            self.assertEqual(directory.stat().st_mtime_ns, EPOCH * 1_000_000_000)

    def test_call_is_limited_to_source_date_epoch_and_archive_backed_formats(self) -> None:
        source = apply_candidate(self.base).read_text()
        archive_branch = re.search(
            r"elsif \(any \{ \$_ eq \$options->\{format\} \}\n"
            r"\s*\('tar', 'squashfs', 'ext2', 'ext4'\)\) \{"
            r".*?normalize_directory_mtimes\(\$options->\{root\}, \$mtime\);"
            r".*?elsif \(any \{ \$_ eq \$options->\{format\} \} \('directory', 'null'\)\)",
            source,
            re.S,
        )
        self.assertIsNotNone(archive_branch)
        self.assertIn('if (defined $ENV{SOURCE_DATE_EPOCH})', archive_branch.group(0))
        self.assertEqual(source.count('normalize_directory_mtimes($options->{root}, $mtime);'), 1)

    def test_helper_prunes_foreign_devices_before_utime(self) -> None:
        source = apply_candidate(self.base).read_text()
        helper = extract_helper(source)
        self.assertIn('if ($stat[0] != $rootdev)', helper)
        self.assertIn('$File::Find::prune = 1;', helper)
        self.assertLess(helper.index('$File::Find::prune = 1;'), helper.index('utime('))
        self.assertIn('no_chdir => 1', helper)


if __name__ == '__main__':
    unittest.main(verbosity=2)
