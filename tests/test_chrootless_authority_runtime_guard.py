from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GUARD = (
    ROOT
    / "investigations"
    / "mmdebstrap-unwritable-tmpdir"
    / "runtime_guard.sh"
)
SCRIPTS = (
    (
        ROOT
        / "investigations"
        / "mmdebstrap-chrootless-env"
        / "direct_authority_transaction.sh",
        "mmdebstrap-chrootless-direct-authority",
    ),
    (
        ROOT
        / "investigations"
        / "mmdebstrap-chrootless-env"
        / "apt_authority_transaction.sh",
        "mmdebstrap-chrootless-apt-authority",
    ),
)


class ChrootlessAuthorityRuntimeGuardTest(unittest.TestCase):
    def prepare_fake_repository(
        self, root: pathlib.Path, repository: pathlib.Path
    ) -> pathlib.Path:
        guard = (
            repository
            / "investigations"
            / "mmdebstrap-unwritable-tmpdir"
            / "runtime_guard.sh"
        )
        guard.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GUARD, guard)

        fakebin = root / "fake-bin"
        fakebin.mkdir(exist_ok=True)
        fake_git = fakebin / "git"
        fake_git.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "if [ \"${1-}\" = rev-parse ] && "
            "[ \"${2-}\" = --show-toplevel ]; then\n"
            "  printf '%s\\n' \"$FAKE_REPO_ROOT\"\n"
            "  exit 0\n"
            "fi\n"
            "exit 2\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o755)
        return fakebin

    def run_check(
        self,
        script: pathlib.Path,
        parent: pathlib.Path,
        repository: pathlib.Path,
        home: pathlib.Path,
    ) -> subprocess.CompletedProcess[str]:
        fakebin = self.prepare_fake_repository(parent, repository)
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_REPO_ROOT": str(repository),
                "HOME": str(home),
                "PATH": f"{fakebin}:/usr/bin:/bin",
            }
        )
        return subprocess.run(
            ["bash", str(script), "--check-runtime-parent", str(parent)],
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    def test_repository_equal_to_runtime_is_rejected(self) -> None:
        for script, leaf in SCRIPTS:
            with self.subTest(script=script.name), tempfile.TemporaryDirectory(
                prefix="authority-runtime-repo-equal-", dir="/tmp"
            ) as temporary:
                parent = pathlib.Path(temporary)
                repository = parent / leaf
                home = parent / "home"
                home.mkdir()
                result = self.run_check(script, parent, repository, home)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("refusing runtime inside repository", result.stderr)

    def test_runtime_containing_repository_is_rejected(self) -> None:
        for script, leaf in SCRIPTS:
            with self.subTest(script=script.name), tempfile.TemporaryDirectory(
                prefix="authority-runtime-repo-child-", dir="/tmp"
            ) as temporary:
                parent = pathlib.Path(temporary)
                repository = parent / leaf / "checkout"
                home = parent / "home"
                home.mkdir()
                result = self.run_check(script, parent, repository, home)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("refusing runtime containing repository", result.stderr)

    def test_runtime_equal_to_home_is_rejected(self) -> None:
        for script, leaf in SCRIPTS:
            with self.subTest(script=script.name), tempfile.TemporaryDirectory(
                prefix="authority-runtime-home-equal-", dir="/tmp"
            ) as temporary:
                parent = pathlib.Path(temporary)
                repository = parent / "checkout"
                home = parent / leaf
                result = self.run_check(script, parent, repository, home)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("refusing runtime inside home", result.stderr)

    def test_symlink_runtime_leaf_is_rejected(self) -> None:
        for script, leaf in SCRIPTS:
            with self.subTest(script=script.name), tempfile.TemporaryDirectory(
                prefix="authority-runtime-symlink-", dir="/tmp"
            ) as temporary:
                parent = pathlib.Path(temporary)
                repository = parent / "checkout"
                home = parent / "home"
                home.mkdir()
                target = parent / "elsewhere"
                target.mkdir()
                (parent / leaf).symlink_to(target, target_is_directory=True)
                result = self.run_check(script, parent, repository, home)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("refusing symlink runtime leaf", result.stderr)

    def test_sibling_runtime_is_accepted(self) -> None:
        for script, _leaf in SCRIPTS:
            with self.subTest(script=script.name), tempfile.TemporaryDirectory(
                prefix="authority-runtime-control-", dir="/tmp"
            ) as temporary:
                parent = pathlib.Path(temporary)
                repository = parent / "checkout"
                home = parent / "home"
                home.mkdir()
                result = self.run_check(script, parent, repository, home)
                self.assertEqual(
                    result.returncode, 0, result.stdout + result.stderr
                )
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
