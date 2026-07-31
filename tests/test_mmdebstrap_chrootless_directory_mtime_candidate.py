from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY_ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime"
    / "0001-normalize-root-chrootless-directory-mtimes.patch"
)
SOURCE_DATE_EPOCH = 1_700_000_000
OLD_MTIME = SOURCE_DATE_EPOCH - 100_000
FILE_MTIME = SOURCE_DATE_EPOCH - 50_000
SYMLINK_MTIME = SOURCE_DATE_EPOCH - 75_000


class MmdebstrapChrootlessDirectoryMtimeCandidateTest(unittest.TestCase):
    def apply_candidate(self, root: pathlib.Path) -> pathlib.Path:
        destination = root / "upstream/mmdebstrap/mmdebstrap"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)
        completed = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(PATCH),
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertNotIn("fuzz", output.lower())
        self.assertNotIn("offset", output.lower())

        syntax = subprocess.run(
            ["perl", "-c", str(destination)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return destination

    @staticmethod
    def function(source: str, name: str, next_name: str) -> str:
        start = source.index(f"sub {name}")
        end = source.index(f"sub {next_name}", start)
        return source[start:end]

    def test_exact_patch_applies_and_product_scope_is_archive_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mtime-candidate-") as temporary:
            candidate = self.apply_candidate(pathlib.Path(temporary))
            source = candidate.read_text(encoding="utf-8")

        helper = self.function(
            source,
            "normalize_archive_directory_mtimes",
            "main",
        )
        required = (
            'lstat $root or error "cannot stat archive root $root: $!";',
            "if (!-d _ || -l _)",
            'error "archive root is not a real directory: $root";',
            "my $root_dev = (lstat _)[0];",
            'lstat or error "cannot stat $File::Find::name: $!";',
            "my $device = (lstat _)[0];",
            "$File::Find::prune = 1;",
            "1 == utime($mtime, $mtime, $File::Find::name)",
            "find({ wanted => $normalize, no_chdir => 1 }, $root);",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, helper)
        self.assertNotIn("system(", helper)
        self.assertNotIn("'touch'", helper)
        self.assertNotIn("'-xdev'", helper)

        self.assertEqual(
            source.count(
                "normalize_archive_directory_mtimes($options->{root}, $mtime);"
            ),
            1,
        )
        gate = (
            "if (!$options->{dryrun}\n"
            "            && exists $ENV{SOURCE_DATE_EPOCH}\n"
            "            && $options->{format} eq 'tar'\n"
            "            && any { $_ eq $options->{mode} } ('root', 'chrootless'))"
        )
        self.assertIn(gate, source)
        self.assertNotIn("cannot find touch", source)

        worker_start = source.index("my $worker = sub")
        setup = source.index("setup($options);", worker_start)
        normalize = source.index(
            "normalize_archive_directory_mtimes($options->{root}, $mtime);",
            setup,
        )
        adios = source.index("pack('n', 0) . 'adios'", normalize)
        tar_output = source.index("open(STDOUT, '>&', $wfh)", adios)
        self.assertLess(setup, normalize)
        self.assertLess(normalize, adios)
        self.assertLess(adios, tar_output)

    def write_helper_harness(
        self,
        root: pathlib.Path,
        helper: str,
        *,
        prelude: str = "",
    ) -> pathlib.Path:
        harness = root / "normalize.pl"
        harness.write_text(
            "use strict;\nuse warnings;\nuse File::Find;\n"
            + prelude
            + "sub error { die $_[0] . \"\\n\"; }\n"
            + helper
            + "normalize_archive_directory_mtimes($ARGV[0], $ARGV[1]);\n",
            encoding="utf-8",
        )
        return harness

    @staticmethod
    def set_mtime(path: pathlib.Path, timestamp: int) -> None:
        os.utime(path, (timestamp, timestamp), follow_symlinks=False)

    def test_exact_helper_changes_only_real_same_device_directories_and_reruns(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="mtime-helper-") as temporary:
            root = pathlib.Path(temporary)
            candidate = self.apply_candidate(root / "candidate")
            source = candidate.read_text(encoding="utf-8")
            helper = self.function(
                source,
                "normalize_archive_directory_mtimes",
                "main",
            )
            harness = self.write_helper_harness(root, helper)

            tree = root / "tree"
            directory = tree / "usr/share/demo"
            directory.mkdir(parents=True)
            payload = directory / "payload"
            payload.write_bytes(b"package bytes\n")
            hardlink = directory / "payload-hardlink"
            os.link(payload, hardlink)
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel"
            sentinel.write_bytes(b"outside bytes\n")
            link = directory / "outside-link"
            link.symlink_to(outside, target_is_directory=True)

            for candidate_path in (tree, tree / "usr", tree / "usr/share", directory):
                self.set_mtime(candidate_path, OLD_MTIME)
            self.set_mtime(payload, FILE_MTIME)
            self.set_mtime(link, SYMLINK_MTIME)
            self.set_mtime(outside, OLD_MTIME)
            self.set_mtime(sentinel, FILE_MTIME)

            before = {
                "payload_mtime": int(payload.stat().st_mtime),
                "payload_inode": payload.stat().st_ino,
                "hardlink_inode": hardlink.stat().st_ino,
                "link_mtime": int(link.lstat().st_mtime),
                "outside_mtime": int(outside.stat().st_mtime),
                "sentinel_mtime": int(sentinel.stat().st_mtime),
                "sentinel_bytes": sentinel.read_bytes(),
            }

            for _ in range(2):
                completed = subprocess.run(
                    ["perl", str(harness), str(tree), str(SOURCE_DATE_EPOCH)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(
                    completed.returncode,
                    0,
                    completed.stdout + completed.stderr,
                )

            for candidate_path in (tree, tree / "usr", tree / "usr/share", directory):
                self.assertEqual(
                    int(candidate_path.stat().st_mtime),
                    SOURCE_DATE_EPOCH,
                )
            self.assertEqual(int(payload.stat().st_mtime), before["payload_mtime"])
            self.assertEqual(payload.stat().st_ino, before["payload_inode"])
            self.assertEqual(hardlink.stat().st_ino, before["hardlink_inode"])
            self.assertEqual(int(link.lstat().st_mtime), before["link_mtime"])
            self.assertEqual(int(outside.stat().st_mtime), before["outside_mtime"])
            self.assertEqual(int(sentinel.stat().st_mtime), before["sentinel_mtime"])
            self.assertEqual(sentinel.read_bytes(), before["sentinel_bytes"])

    def test_exact_helper_fails_closed_for_invalid_root_and_utime_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mtime-failure-") as temporary:
            root = pathlib.Path(temporary)
            candidate = self.apply_candidate(root / "candidate")
            source = candidate.read_text(encoding="utf-8")
            helper = self.function(
                source,
                "normalize_archive_directory_mtimes",
                "main",
            )
            harness = self.write_helper_harness(root, helper)

            missing = root / "missing"
            missing_result = subprocess.run(
                ["perl", str(harness), str(missing), str(SOURCE_DATE_EPOCH)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(missing_result.returncode, 0)
            self.assertIn("cannot stat archive root", missing_result.stderr)

            target = root / "target"
            target.mkdir()
            self.set_mtime(target, OLD_MTIME)
            symlink = root / "root-link"
            symlink.symlink_to(target, target_is_directory=True)
            symlink_result = subprocess.run(
                ["perl", str(harness), str(symlink), str(SOURCE_DATE_EPOCH)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(symlink_result.returncode, 0)
            self.assertIn("archive root is not a real directory", symlink_result.stderr)
            self.assertEqual(int(target.stat().st_mtime), OLD_MTIME)

            tree = root / "tree"
            directory = tree / "directory"
            directory.mkdir(parents=True)
            self.set_mtime(tree, OLD_MTIME)
            self.set_mtime(directory, OLD_MTIME)
            failing_harness = self.write_helper_harness(
                root,
                helper,
                prelude=(
                    "BEGIN { *CORE::GLOBAL::utime = sub { "
                    "$! = 13; return 0; }; }\n"
                ),
            )
            failed_utime = subprocess.run(
                ["perl", str(failing_harness), str(tree), str(SOURCE_DATE_EPOCH)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(failed_utime.returncode, 0)
            self.assertIn("cannot normalize directory mtime", failed_utime.stderr)
            self.assertEqual(int(tree.stat().st_mtime), OLD_MTIME)
            self.assertEqual(int(directory.stat().st_mtime), OLD_MTIME)

    @unittest.skipUnless(shutil.which("perltidy"), "perltidy is unavailable")
    def test_current_sid_formatting_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mtime-format-") as temporary:
            candidate = self.apply_candidate(pathlib.Path(temporary))
            formatted = subprocess.run(
                ["perltidy"],
                input=candidate.read_text(encoding="utf-8"),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                formatted.returncode,
                0,
                formatted.stdout + formatted.stderr,
            )
            self.assertEqual(
                formatted.stdout,
                candidate.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
