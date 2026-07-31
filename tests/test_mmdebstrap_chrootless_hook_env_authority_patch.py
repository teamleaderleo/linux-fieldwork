from __future__ import annotations

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
    / "0002-use-absolute-env-wrapper.patch",
    ROOT
    / "investigations/mmdebstrap-chrootless-env/"
    / "0003-use-absolute-env-for-chrootless-hooks.patch",
)


class MmdebstrapChrootlessHookEnvAuthorityPatchTest(unittest.TestCase):
    def prepare_candidate(self, root: pathlib.Path) -> str:
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
        return destination.read_text(encoding="utf-8")

    @staticmethod
    def function(source: str, name: str, next_name: str) -> str:
        start = source.index(f"sub {name}")
        end = source.index(f"sub {next_name}", start)
        return source[start:end]

    def test_chrootless_hooks_use_validated_absolute_env(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-chrootless-hook-env-authority-"
        ) as temporary:
            candidate = self.prepare_candidate(pathlib.Path(temporary))

        hooks = self.function(candidate, "run_hooks", "setup")
        helper = self.function(
            candidate, "chrootless_env_path", "chrootless_dpkg_environment"
        )

        self.assertIn("my $path = '/usr/bin/env';", helper)
        self.assertIn(
            "my $env_path = $options->{mode} eq 'chrootless'\n"
            "      ? chrootless_env_path()\n"
            "      : 'env';",
            hooks,
        )
        self.assertIn(
            "system(@cmdprefix, $env_path, @env_opts, 'sh', '-c'", hooks
        )
        self.assertIn(
            "system($env_path, @env_opts, $script, $options->{root})", hooks
        )
        self.assertIn(
            "system($env_path, @env_opts,\n"
            "                    'sh', '-c', $script, 'exec', $options->{root})",
            hooks,
        )
        self.assertNotIn("system(@cmdprefix, 'env', @env_opts", hooks)
        self.assertNotIn("system('env', @env_opts", hooks)

    def test_hook_only_losing_mutation_is_exactly_constructible(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mmdebstrap-chrootless-hook-env-mutation-"
        ) as temporary:
            candidate = self.prepare_candidate(pathlib.Path(temporary))

        marker = (
            "    my $env_path = $options->{mode} eq 'chrootless'\n"
            "      ? chrootless_env_path()\n"
            "      : 'env';\n"
        )
        self.assertEqual(candidate.count(marker), 1)
        mutation = candidate.replace(marker, "    my $env_path = 'env';\n")
        hooks = self.function(mutation, "run_hooks", "setup")

        self.assertIn("my $env_path = 'env';", hooks)
        self.assertNotIn("? chrootless_env_path()", hooks)
        self.assertEqual(hooks.count("system($env_path"), 2)
        self.assertEqual(hooks.count("system(@cmdprefix, $env_path"), 1)


if __name__ == "__main__":
    unittest.main()
