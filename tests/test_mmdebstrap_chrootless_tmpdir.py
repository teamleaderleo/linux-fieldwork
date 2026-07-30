from __future__ import annotations

import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest


class MmdebstrapChrootlessTmpdirTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/mmdebstrap"
        cls.harness = cls.repo / "investigations/mmdebstrap-chrootless-env/run.sh"
        if shutil.which("perl") is None or shutil.which("env") is None:
            raise unittest.SkipTest("perl and env are required")

    @staticmethod
    def extract_helper(source_text: str) -> str:
        start_marker = "sub chrootless_dpkg_environment() {"
        end_marker = "\nsub chrootless_unsafe_environment() {"
        start = source_text.index(start_marker)
        end = source_text.index(end_marker, start)
        return source_text[start:end]

    def run_helper(
        self,
        source_text: str,
        target: pathlib.Path,
        caller_tmpdir: pathlib.Path,
    ) -> subprocess.CompletedProcess[bytes]:
        helper = self.extract_helper(source_text)
        program = (
            "use strict;\n"
            "use warnings;\n"
            "use File::Path qw(make_path);\n"
            "sub error { die $_[0] . qq{\\n}; }\n"
            f"{helper}\n"
            "print join(qq{\\0}, "
            "chrootless_dpkg_environment($ARGV[0])), qq{\\0};\n"
        )
        with tempfile.TemporaryDirectory(prefix="lf69-perl-helper-") as td:
            script = pathlib.Path(td) / "helper.pl"
            script.write_text(program)
            env = {
                "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                "TMPDIR": str(caller_tmpdir),
                "LC_ALL": "C.UTF-8",
            }
            return subprocess.run(
                ["perl", str(script), str(target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

    @staticmethod
    def parse_environment_args(output: bytes) -> list[str]:
        return [item.decode() for item in output.split(b"\0") if item]

    @staticmethod
    def run_mktemp(environment_args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "env",
                *environment_args,
                "/bin/sh",
                "-c",
                'base="${TMPDIR:-/tmp}"; '
                'created="$(mktemp -d "$base/lf-chrootless-tmp.XXXXXX")"; '
                'printf "%s\\n" "$created"; rmdir "$created"',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_helper_creates_and_assigns_target_tmpdir(self) -> None:
        source_text = self.source.read_text()
        with tempfile.TemporaryDirectory(prefix="lf69-positive-") as td:
            root = pathlib.Path(td)
            target = root / "target"
            caller_tmpdir = root / "caller-tmp"
            target.mkdir()
            caller_tmpdir.mkdir()

            completed = self.run_helper(source_text, target, caller_tmpdir)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            args = self.parse_environment_args(completed.stdout)

            self.assertEqual(args[0], "-i")
            self.assertIn(f"TMPDIR={target / 'tmp'}", args)
            self.assertNotIn(f"TMPDIR={caller_tmpdir}", args)
            self.assertTrue((target / "tmp").is_dir())
            self.assertEqual(
                stat.S_IMODE((target / "tmp").stat().st_mode),
                0o1777,
            )

            created = self.run_mktemp(args)
            self.assertEqual(created.returncode, 0, created.stderr)
            created_path = pathlib.Path(created.stdout.strip())
            self.assertEqual(created_path.parent, target / "tmp")
            self.assertFalse(created_path.exists())

    def test_assignment_is_required_to_avoid_host_tmp_fallback(self) -> None:
        source_text = self.source.read_text()
        assignment = "my @result = ('-i', \"TMPDIR=$tmpdir\");"
        self.assertEqual(source_text.count(assignment), 1)
        mutant = source_text.replace(assignment, "my @result = ('-i');", 1)

        with tempfile.TemporaryDirectory(prefix="lf69-negative-") as td:
            root = pathlib.Path(td)
            target = root / "target"
            caller_tmpdir = root / "caller-tmp"
            target.mkdir()
            caller_tmpdir.mkdir()

            completed = self.run_helper(mutant, target, caller_tmpdir)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            args = self.parse_environment_args(completed.stdout)
            self.assertFalse(any(item.startswith("TMPDIR=") for item in args))

            created = self.run_mktemp(args)
            self.assertEqual(created.returncode, 0, created.stderr)
            created_path = pathlib.Path(created.stdout.strip())
            self.assertEqual(created_path.parent, pathlib.Path("/tmp"))
            self.assertNotEqual(created_path.parent, target / "tmp")
            self.assertFalse(created_path.exists())

    def test_helper_refuses_symlink_and_non_directory_targets(self) -> None:
        source_text = self.source.read_text()
        with tempfile.TemporaryDirectory(prefix="lf69-invalid-") as td:
            root = pathlib.Path(td)
            caller_tmpdir = root / "caller-tmp"
            caller_tmpdir.mkdir()

            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel"
            sentinel.write_text("preserve me\n")
            symlink_target = root / "symlink-target"
            symlink_target.mkdir()
            (symlink_target / "tmp").symlink_to(outside, target_is_directory=True)
            symlink_result = self.run_helper(
                source_text,
                symlink_target,
                caller_tmpdir,
            )
            self.assertNotEqual(symlink_result.returncode, 0)
            self.assertIn(b"is a symlink", symlink_result.stderr)
            self.assertEqual(sentinel.read_text(), "preserve me\n")

            file_target = root / "file-target"
            file_target.mkdir()
            (file_target / "tmp").write_text("not a directory\n")
            file_result = self.run_helper(
                source_text,
                file_target,
                caller_tmpdir,
            )
            self.assertNotEqual(file_result.returncode, 0)
            self.assertIn(b"is not a directory", file_result.stderr)

    def test_both_chrootless_dpkg_paths_pass_the_selected_root(self) -> None:
        source_text = self.source.read_text()
        self.assertEqual(
            source_text.count(
                "chrootless_dpkg_environment($options->{root})"
            ),
            2,
        )
        self.assertNotIn("chrootless_dpkg_environment(),", source_text)

    def test_harness_refuses_root_as_runtime_parent(self) -> None:
        env = os.environ.copy()
        env["RUNNER_TEMP"] = "/"
        completed = subprocess.run(
            ["bash", str(self.harness)],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("unsafe runtime parent", completed.stderr)


if __name__ == "__main__":
    unittest.main()
