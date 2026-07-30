from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCH = ROOT / (
    "investigations/mmdebstrap-chrootless-env/"
    "0001-use-absolute-env-wrapper.patch"
)


class MmdebstrapChrootlessEnvWrapperPatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="mmdebstrap-absolute-env-wrapper-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.tree = pathlib.Path(self.temporary.name)
        shutil.copy2(SOURCE, self.tree / "mmdebstrap")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=self.tree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.candidate = (self.tree / "mmdebstrap").read_text(encoding="utf-8")

    def test_absolute_wrapper_is_validated(self) -> None:
        helper_start = self.candidate.index("sub chrootless_env_path")
        helper_end = self.candidate.index(
            "sub chrootless_dpkg_environment", helper_start
        )
        helper = self.candidate[helper_start:helper_end]
        self.assertIn("my $path = '/usr/bin/env';", helper)
        self.assertIn("if (!-e $path)", helper)
        self.assertIn("if (!-f $path)", helper)
        self.assertIn("if (!-x $path)", helper)
        self.assertIn('return $path;', helper)

    def test_both_chrootless_launch_paths_use_absolute_wrapper(self) -> None:
        direct_start = self.candidate.index("sub run_essential")
        direct_end = self.candidate.index("sub run_install", direct_start)
        direct = self.candidate[direct_start:direct_end]
        self.assertIn(
            "ARGV => [\n                    chrootless_env_path(),",
            direct,
        )
        self.assertNotIn("ARGV => [\n                    'env',", direct)

        install_start = direct_end
        install_end = self.candidate.index("sub run_cleanup", install_start)
        install = self.candidate[install_start:install_end]
        self.assertIn(
            "'-oDir::Bin::dpkg=' . chrootless_env_path(),",
            install,
        )
        self.assertEqual(install.count("Dir::Bin::dpkg=env"), 1)

    def test_candidate_retains_clean_inner_path(self) -> None:
        self.assertIn(
            "my @result = ('-i', \"PATH=$dpkgpath\", \"TMPDIR=$tmpdir\");",
            self.candidate,
        )

    def test_candidate_perl_syntax(self) -> None:
        completed = subprocess.run(
            ["perl", "-c", str(self.tree / "mmdebstrap")],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
