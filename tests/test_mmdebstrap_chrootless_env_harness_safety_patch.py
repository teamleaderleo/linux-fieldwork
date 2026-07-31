from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = (
    REPOSITORY_ROOT / "investigations/mmdebstrap-chrootless-env/run.sh"
)
PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-env"
    / "0002-guard-runtime-and-source-copy.patch"
)


class ChrootlessEnvironmentHarnessSafetyPatchTests(unittest.TestCase):
    def apply_patch(self, root: pathlib.Path) -> pathlib.Path:
        destination = root / "investigations/mmdebstrap-chrootless-env"
        destination.mkdir(parents=True)
        script = destination / "run.sh"
        shutil.copy2(SOURCE_SCRIPT, script)
        completed = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-d",
                str(root),
                "-i",
                str(PATCH),
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertNotIn("fuzz", output.lower())
        return script

    def check_parent(
        self,
        script: pathlib.Path,
        path: pathlib.Path | str,
        *,
        cwd: pathlib.Path = REPOSITORY_ROOT,
        home: pathlib.Path | None = None,
        extra_environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if home is not None:
            environment["HOME"] = str(home)
        if extra_environment is not None:
            environment.update(extra_environment)
        return subprocess.run(
            ["bash", str(script), "--check-runtime-parent", str(path)],
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_patch_applies_and_shell_syntax_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = self.apply_patch(pathlib.Path(temporary))
            completed = subprocess.run(
                ["bash", "-n", str(script)],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_accepts_only_named_disposable_parent_families(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = self.apply_patch(pathlib.Path(temporary))
            for path in (
                "/tmp",
                "/tmp/linux-fieldwork-probe",
                "/var/tmp",
                "/var/tmp/linux-fieldwork-probe",
                "/home/runner/work/_temp",
                "/home/runner/work/_temp/linux-fieldwork-probe",
            ):
                with self.subTest(path=path):
                    completed = self.check_parent(script, path)
                    self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_rejects_root_repository_home_and_parent_collapse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = self.apply_patch(pathlib.Path(temporary))
            for path in (
                "/",
                REPOSITORY_ROOT,
                pathlib.Path.home(),
                "/tmp/../etc",
            ):
                with self.subTest(path=path):
                    completed = self.check_parent(script, path)
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn("refusing", completed.stderr)

    def test_rejects_canonical_repository_root_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-fake-root-git-") as temporary:
            root = pathlib.Path(temporary)
            script = self.apply_patch(root / "patch-tree")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_git = fake_bin / "git"
            fake_git.write_text(
                "#!/bin/sh\n"
                "if [ \"${1:-}\" = rev-parse ] "
                "&& [ \"${2:-}\" = --show-toplevel ]; then\n"
                "  printf '%s\\n' \"${LF_FAKE_REPO_ROOT:?}\"\n"
                "  exit 0\n"
                "fi\n"
                "exit 97\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            for repository_identity in ("/", "/./", "/tmp/.."):
                with self.subTest(repository_identity=repository_identity):
                    completed = self.check_parent(
                        script,
                        "/tmp",
                        home=pathlib.Path("/home/tester"),
                        extra_environment={
                            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
                            "LF_FAKE_REPO_ROOT": repository_identity,
                        },
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertIn("repository root", completed.stderr)
                    self.assertEqual(completed.stdout, "")

    def test_rejects_home_root_identity_for_generic_and_hosted_parents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = self.apply_patch(pathlib.Path(temporary))
            for parent in ("/tmp", "/home/runner/work/_temp"):
                with self.subTest(parent=parent):
                    completed = self.check_parent(
                        script,
                        parent,
                        home=pathlib.Path("/"),
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertIn("home root", completed.stderr)
                    self.assertEqual(completed.stdout, "")

    def test_rejects_runtime_that_contains_or_is_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-runtime-overlap-") as temporary:
            root = pathlib.Path(temporary)
            script = self.apply_patch(root / "patch-tree")

            for relation in ("runtime-contains-repository", "runtime-inside-repository"):
                with self.subTest(relation=relation):
                    parent = root / relation
                    runtime = parent / "mmdebstrap-chrootless-env"
                    if relation == "runtime-contains-repository":
                        repository = runtime / "checkout"
                    else:
                        repository = parent
                    repository.mkdir(parents=True)
                    initialized = subprocess.run(
                        ["git", "init", "-q"],
                        cwd=repository,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(
                        initialized.returncode,
                        0,
                        initialized.stdout + initialized.stderr,
                    )
                    completed = self.check_parent(
                        script,
                        parent,
                        cwd=repository,
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertIn("repository", completed.stderr)

    def test_rejects_runtime_that_contains_or_is_inside_home(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-home-overlap-") as temporary:
            root = pathlib.Path(temporary)
            script = self.apply_patch(root / "patch-tree")
            parent = root / "runtime-parent"
            runtime = parent / "mmdebstrap-chrootless-env"

            for home in (runtime / "home", runtime):
                with self.subTest(home=home):
                    home.mkdir(parents=True, exist_ok=True)
                    completed = self.check_parent(script, parent, home=home)
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertIn("home", completed.stderr)

    def test_hosted_temp_allows_normal_home_but_protects_home_below_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-hosted-home-overlap-") as temporary:
            script = self.apply_patch(pathlib.Path(temporary))
            parent = pathlib.Path("/home/runner/work/_temp")
            runtime = parent / "mmdebstrap-chrootless-env"

            normal = self.check_parent(script, parent, home=pathlib.Path("/home/runner"))
            self.assertEqual(normal.returncode, 0, normal.stderr)

            for home in (runtime, runtime / "home"):
                with self.subTest(home=home):
                    completed = self.check_parent(script, parent, home=home)
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertIn("hosted runtime containing home", completed.stderr)

    def test_check_mode_works_from_repository_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-chrootless-subdir-") as temporary:
            root = pathlib.Path(temporary)
            script = self.apply_patch(root / "patch-tree")
            repository = root / "repository"
            nested = repository / "nested" / "review"
            nested.mkdir(parents=True)
            initialized = subprocess.run(
                ["git", "init", "-q"],
                cwd=repository,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            completed = self.check_parent(
                script,
                root / "runtime-parent",
                cwd=nested,
                home=root / "home",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_candidate_executes_a_preserved_runtime_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = self.apply_patch(pathlib.Path(temporary))
            source = script.read_text(encoding="utf-8")

        self.assertIn(
            'repo_root="$(realpath -m "$(git rev-parse --show-toplevel)")"',
            source,
        )
        self.assertIn(
            'source_copy="$runtime/source/mmdebstrap"',
            source,
        )
        self.assertIn(
            'cp --preserve=mode "$source_root/mmdebstrap" "$source_copy"',
            source,
        )
        self.assertIn('chmod 0755 "$source_copy"', source)
        self.assertIn('    "$source_copy"\n    --mode=chrootless', source)
        self.assertNotIn('chmod 0755 "$source_root/mmdebstrap"', source)

        for before in (
            'source_mode_before="$(stat -c %a "$source_root/mmdebstrap")"',
            'source_hash_before="$(git hash-object "$source_root/mmdebstrap")"',
            'source_status_before="$(git -C "$repo_root" status --short -- '
            'upstream/mmdebstrap/mmdebstrap)"',
        ):
            self.assertIn(before, source)

        self.assertIn(
            '[[ "$(stat -c %a "$source_root/mmdebstrap")" '
            '== "$source_mode_before" ]]',
            source,
        )
        self.assertIn(
            '[[ "$(git hash-object "$source_root/mmdebstrap")" '
            '== "$source_hash_before" ]]',
            source,
        )
        self.assertIn(
            '[[ "$(git -C "$repo_root" status --short -- '
            'upstream/mmdebstrap/mmdebstrap)" == "$source_status_before" ]]',
            source,
        )
        self.assertNotIn(
            'source_status_before="$(git status --short -- ',
            source,
        )
        self.assertNotIn("git diff --exit-code -- upstream/mmdebstrap/mmdebstrap", source)
        self.assertIn("source_git_state_preserved=yes", source)

    def test_baseline_contains_both_confirmed_harness_defects(self) -> None:
        baseline = SOURCE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('if [[ "$runtime_parent" == / ]]', baseline)
        self.assertIn('rm -rf "$runtime"', baseline)
        self.assertIn('chmod 0755 "$source_root/mmdebstrap"', baseline)
        self.assertNotIn("--check-runtime-parent", baseline)


if __name__ == "__main__":
    unittest.main()
