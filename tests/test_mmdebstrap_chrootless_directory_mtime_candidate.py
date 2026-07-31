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
        expected = (
            "'find', $root, '-xdev', '-type', 'd', '-exec',\n"
            "        'touch', '--no-dereference', \"--date=\\@$mtime\", '--', '{}', '+'"
        )
        self.assertIn(expected, helper)
        self.assertIn(
            'or error "cannot normalize archive directory mtimes: $?";',
            helper,
        )

        global_tools_start = source.index("foreach my $tool (")
        global_tools_end = source.index("my $dpkgversion", global_tools_start)
        global_tools = source[global_tools_start:global_tools_end]
        self.assertNotIn("'touch'", global_tools)
        self.assertIn("if (!can_execute 'touch')", source)
        self.assertIn('error "cannot find touch";', source)
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

        worker_start = source.index("my $worker = sub")
        setup = source.index("setup($options);", worker_start)
        dependency = source.index("if (!can_execute 'touch')", setup)
        normalize = source.index(
            "normalize_archive_directory_mtimes($options->{root}, $mtime);",
            dependency,
        )
        adios = source.index("pack('n', 0) . 'adios'", normalize)
        tar_output = source.index("open(STDOUT, '>&', $wfh)", adios)
        self.assertLess(setup, dependency)
        self.assertLess(dependency, normalize)
        self.assertLess(normalize, adios)
        self.assertLess(adios, tar_output)

    def write_helper_harness(
        self,
        root: pathlib.Path,
        helper: str,
    ) -> pathlib.Path:
        harness = root / "normalize.pl"
        harness.write_text(
            "use strict;\nuse warnings;\n"
            "sub error { die $_[0] . \"\\n\"; }\n"
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

    def test_exact_helper_preserves_first_tool_failure(self) -> None:
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
            tree = root / "tree"
            directory = tree / "directory"
            directory.mkdir(parents=True)
            self.set_mtime(tree, OLD_MTIME)
            self.set_mtime(directory, OLD_MTIME)

            fakebin = root / "fakebin"
            fakebin.mkdir()
            fake_find = fakebin / "find"
            fake_find.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
            fake_find.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fakebin}:{environment['PATH']}"

            failed_find = subprocess.run(
                ["perl", str(harness), str(tree), str(SOURCE_DATE_EPOCH)],
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(failed_find.returncode, 0)
            self.assertIn("cannot normalize archive directory mtimes", failed_find.stderr)
            self.assertEqual(int(tree.stat().st_mtime), OLD_MTIME)
            self.assertEqual(int(directory.stat().st_mtime), OLD_MTIME)

            fake_find.unlink()
            fake_touch = fakebin / "touch"
            fake_touch.write_text("#!/bin/sh\nexit 43\n", encoding="utf-8")
            fake_touch.chmod(0o755)
            failed_touch = subprocess.run(
                ["perl", str(harness), str(tree), str(SOURCE_DATE_EPOCH)],
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(failed_touch.returncode, 0)
            self.assertIn("cannot normalize archive directory mtimes", failed_touch.stderr)

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
