from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCHES = (
    ROOT
    / "investigations/mmdebstrap-chrootless-env/"
    / "0001-use-configured-dpkg-path.patch",
    ROOT
    / "investigations/mmdebstrap-chrootless-env/"
    / "0002-use-absolute-env-wrapper.patch",
)


class MmdebstrapChrootlessEnvAuthorityCompositionTest(unittest.TestCase):
    def prepare_candidate(self, root: pathlib.Path) -> pathlib.Path:
        destination = root / "upstream/mmdebstrap/mmdebstrap"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)

        for patch in PATCHES:
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(patch),
                ],
                cwd=root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            output = applied.stdout + applied.stderr
            self.assertEqual(applied.returncode, 0, output)
            self.assertNotIn("fuzz", output.lower())

        checked = subprocess.run(
            ["perl", "-c", str(destination)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination

    @staticmethod
    def function(source: str, name: str, next_name: str) -> str:
        start = source.index(f"sub {name}")
        end = source.index(f"sub {next_name}", start)
        return source[start:end]

    def test_exact_composition_owns_outer_and_inner_lookup(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-chrootless-env-authority-"
        ) as temporary:
            candidate_path = self.prepare_candidate(pathlib.Path(temporary))
            candidate = candidate_path.read_text(encoding="utf-8")

        helper = self.function(
            candidate, "chrootless_env_path", "chrootless_dpkg_environment"
        )
        environment = self.function(
            candidate, "chrootless_dpkg_environment", "chrootless_unsafe_environment"
        )
        essential = self.function(candidate, "run_essential", "run_install")
        install = self.function(candidate, "run_install", "run_cleanup")

        self.assertIn("my $path = '/usr/bin/env';", helper)
        self.assertIn("if (!-e $path)", helper)
        self.assertIn("if (!-f $path)", helper)
        self.assertIn("if (!-x $path)", helper)
        self.assertIn("return $path;", helper)

        self.assertIn("my $dpkgpath = shift;", environment)
        self.assertIn(
            'error "cannot determine chrootless maintainer-script PATH";',
            environment,
        )
        self.assertNotIn("\n      PATH\n", environment)
        self.assertIn(
            "my @result = ('-i', \"PATH=$dpkgpath\", \"TMPDIR=$tmpdir\");",
            environment,
        )

        self.assertIn("chrootless_env_path(),", essential)
        self.assertNotIn("ARGV => [\n                    'env',", essential)
        self.assertIn("$options->{root}, $options->{dpkgpath}", essential)

        self.assertIn(
            "'-oDir::Bin::dpkg=' . chrootless_env_path(),",
            install,
        )
        self.assertIn("$options->{dpkgpath}", install)
        self.assertNotIn("'-oDir::Bin::dpkg=env',", install)
        self.assertIn("$options->{dpkgpath} = $defaultpath;", candidate)

    @staticmethod
    def write_executable(path: pathlib.Path, body: str) -> None:
        path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8")
        path.chmod(0o755)

    def test_absolute_outer_wrapper_bypasses_caller_path(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-outer-env-bootstrap-"
        ) as temporary:
            root = pathlib.Path(temporary)
            fakebin = root / "fakebin"
            fakebin.mkdir()
            marker = root / "fake-env-ran"
            fake_env = fakebin / "env"
            self.write_executable(
                fake_env,
                'printf "ran\\n" >"$OUTER_ENV_MARKER"\nexec /usr/bin/env "$@"\n',
            )
            inherited = os.environ.copy()
            inherited["PATH"] = f"{fakebin}:/usr/bin:/bin"
            inherited["OUTER_ENV_MARKER"] = str(marker)

            baseline = subprocess.run(
                ["env", "-i", "PATH=/usr/bin:/bin", "/bin/true"],
                env=inherited,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(
                baseline.returncode, 0, baseline.stdout + baseline.stderr
            )
            self.assertTrue(marker.exists())

            marker.unlink()
            candidate = subprocess.run(
                ["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "/bin/true"],
                env=inherited,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(
                candidate.returncode, 0, candidate.stdout + candidate.stderr
            )
            self.assertFalse(marker.exists())

    def test_configured_inner_path_replaces_caller_path(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-inner-path-authority-"
        ) as temporary:
            root = pathlib.Path(temporary)
            caller_bin = root / "caller-bin"
            configured_bin = root / "configured-bin"
            caller_bin.mkdir()
            configured_bin.mkdir()
            caller_marker = root / "caller-helper-ran"
            configured_marker = root / "configured-helper-ran"
            helper_name = "fieldwork-maintainer-helper"
            self.write_executable(
                caller_bin / helper_name,
                f'printf "caller\\n" >{shlex_quote(str(caller_marker))}\n',
            )
            self.write_executable(
                configured_bin / helper_name,
                f'printf "configured\\n" >{shlex_quote(str(configured_marker))}\n',
            )

            baseline = subprocess.run(
                [
                    "/usr/bin/env",
                    "-i",
                    f"PATH={caller_bin}",
                    helper_name,
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(
                baseline.returncode, 0, baseline.stdout + baseline.stderr
            )
            self.assertTrue(caller_marker.exists())
            self.assertFalse(configured_marker.exists())

            caller_marker.unlink()
            candidate = subprocess.run(
                [
                    "/usr/bin/env",
                    "-i",
                    f"PATH={configured_bin}",
                    helper_name,
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(
                candidate.returncode, 0, candidate.stdout + candidate.stderr
            )
            self.assertFalse(caller_marker.exists())
            self.assertTrue(configured_marker.exists())

    def test_exact_wrapper_validator_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-env-validator-"
        ) as temporary:
            root = pathlib.Path(temporary)
            candidate_path = self.prepare_candidate(root / "candidate")
            source = candidate_path.read_text(encoding="utf-8")
            helper = self.function(
                source, "chrootless_env_path", "chrootless_dpkg_environment"
            )

            missing = root / "missing-env"
            directory = root / "directory-env"
            directory.mkdir()
            nonexec = root / "nonexec-env"
            nonexec.write_text("not executable\n", encoding="utf-8")
            executable = root / "executable-env"
            self.write_executable(executable, "exit 0\n")

            cases = (
                (missing, "does not exist", False),
                (directory, "not a regular file", False),
                (nonexec, "not executable", False),
                (executable, str(executable), True),
            )
            for index, (path, expected, succeeds) in enumerate(cases):
                with self.subTest(path=path.name):
                    mutated = helper.replace(
                        "my $path = '/usr/bin/env';",
                        f"my $path = {perl_quote(str(path))};",
                    )
                    harness = root / f"helper-{index}.pl"
                    harness.write_text(
                        "use strict;\nuse warnings;\n"
                        "sub error { die $_[0] . \"\\n\"; }\n"
                        + mutated
                        + "print chrootless_env_path();\n",
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        ["perl", str(harness)],
                        check=False,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10,
                    )
                    if succeeds:
                        self.assertEqual(
                            result.returncode, 0, result.stdout + result.stderr
                        )
                        self.assertEqual(result.stdout, expected)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(expected, result.stderr)


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def perl_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


if __name__ == "__main__":
    unittest.main()
