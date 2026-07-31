from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
INVESTIGATION = ROOT / "investigations/mmdebstrap-unwritable-tmpdir"
GUARD = INVESTIGATION / "runtime_guard.sh"
SCRIPTS = (
    (INVESTIGATION / "run.sh", "linux-fieldwork-mmdebstrap-tmpdir"),
    (
        INVESTIGATION / "deep_review.sh",
        "linux-fieldwork-mmdebstrap-deep-review",
    ),
)


class UnwritableTmpdirRuntimeGuardTest(unittest.TestCase):
    def run_guard(
        self,
        repository: pathlib.Path | str,
        home: pathlib.Path | str,
        parent: pathlib.Path | str,
        leaf: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; validate_disposable_runtime "$2" "$3" "$4" "$5"',
                "runtime-guard-test",
                str(GUARD),
                str(repository),
                str(home),
                str(parent),
                leaf,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )

    def make_checkout(
        self,
        root: pathlib.Path,
        script: pathlib.Path,
        repository: pathlib.Path,
    ) -> pathlib.Path:
        target_dir = repository / "investigations/mmdebstrap-unwritable-tmpdir"
        target_dir.mkdir(parents=True)
        shutil.copy2(script, target_dir / script.name)
        shutil.copy2(GUARD, target_dir / GUARD.name)
        subprocess.run(
            ["git", "init", "-q", str(repository)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        sentinel = repository / "checkout-sentinel"
        sentinel.write_text("preserve\n", encoding="utf-8")
        return target_dir / script.name

    def run_check_mode(
        self,
        script: pathlib.Path,
        repository: pathlib.Path,
        parent: pathlib.Path,
        home: pathlib.Path,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        return subprocess.run(
            ["bash", str(script), "--check-runtime-parent", str(parent)],
            cwd=repository,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )

    def test_named_disposable_parent_families_are_accepted(self) -> None:
        leaf = "linux-fieldwork-mmdebstrap-tmpdir"
        cases = (
            "/tmp",
            "/tmp/linux-fieldwork-parent",
            "/var/tmp",
            "/var/tmp/linux-fieldwork-parent",
            "/home/runner/work/_temp",
            "/home/runner/work/_temp/nested",
        )
        for parent in cases:
            with self.subTest(parent=parent):
                result = self.run_guard(
                    "/opt/linux-fieldwork-repository",
                    "/home/runner" if parent.startswith("/home/runner") else "/home/tester",
                    parent,
                    leaf,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    result.stdout.strip(),
                    str(pathlib.Path(parent) / leaf),
                )

    def test_root_unlisted_parent_and_unsafe_leaf_are_rejected(self) -> None:
        cases = (
            ("/", "linux-fieldwork-mmdebstrap-tmpdir"),
            ("/opt/runtime", "linux-fieldwork-mmdebstrap-tmpdir"),
            ("/tmp", ""),
            ("/tmp", "."),
            ("/tmp", ".."),
            ("/tmp", "nested/leaf"),
        )
        for parent, leaf in cases:
            with self.subTest(parent=parent, leaf=leaf):
                result = self.run_guard(
                    "/opt/linux-fieldwork-repository",
                    "/home/tester",
                    parent,
                    leaf,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("refusing", result.stderr)

    def test_repository_overlap_is_rejected_in_both_directions(self) -> None:
        leaf = "linux-fieldwork-mmdebstrap-tmpdir"
        with tempfile.TemporaryDirectory(
            prefix="lf-tmpdir-overlap-", dir="/tmp"
        ) as td:
            root = pathlib.Path(td).resolve()
            parent = root / "parent"
            runtime = parent / leaf
            cases = (
                (runtime, parent, "runtime equals repository"),
                (runtime / "repository", parent, "runtime contains repository"),
                (root / "repository", root / "repository/runtime", "runtime inside repository"),
            )
            for repository, selected_parent, label in cases:
                with self.subTest(label=label):
                    result = self.run_guard(
                        repository,
                        root / "home",
                        selected_parent,
                        leaf,
                    )
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("repository", result.stderr)

    def test_existing_parent_symlink_is_canonicalized_before_overlap_checks(self) -> None:
        leaf = "linux-fieldwork-mmdebstrap-tmpdir"
        with tempfile.TemporaryDirectory(
            prefix="lf-tmpdir-symlink-", dir="/tmp"
        ) as td:
            root = pathlib.Path(td).resolve()
            repository = root / "repository"
            repository.mkdir()
            parent_link = root / "parent-link"
            parent_link.symlink_to(repository, target_is_directory=True)
            result = self.run_guard(
                repository,
                root / "home",
                parent_link,
                leaf,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("repository", result.stderr)

    def test_existing_runtime_leaf_symlink_is_rejected_and_target_preserved(self) -> None:
        leaf = "linux-fieldwork-mmdebstrap-tmpdir"
        with tempfile.TemporaryDirectory(
            prefix="lf-tmpdir-runtime-symlink-", dir="/tmp"
        ) as td:
            root = pathlib.Path(td).resolve()
            parent = root / "parent"
            target = parent / "victim"
            target.mkdir(parents=True)
            sentinel = target / "sentinel"
            sentinel.write_text("preserve\n", encoding="utf-8")
            runtime = parent / leaf
            runtime.symlink_to(target, target_is_directory=True)

            result = self.run_guard(
                root / "repository",
                root / "home",
                parent,
                leaf,
            )

            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("symlink runtime leaf", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue(runtime.is_symlink())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")

    def test_home_overlap_and_hosted_exception_are_explicit(self) -> None:
        leaf = "linux-fieldwork-mmdebstrap-tmpdir"
        with tempfile.TemporaryDirectory(
            prefix="lf-tmpdir-home-", dir="/tmp"
        ) as td:
            root = pathlib.Path(td).resolve()
            home = root / "home"
            generic_inside = self.run_guard(
                root / "repository",
                home,
                home,
                leaf,
            )
            self.assertEqual(generic_inside.returncode, 2)
            self.assertIn("home", generic_inside.stderr)

            parent = root / "parent"
            runtime = parent / leaf
            generic_contains = self.run_guard(
                root / "repository",
                runtime / "home",
                parent,
                leaf,
            )
            self.assertEqual(generic_contains.returncode, 2)
            self.assertIn("home", generic_contains.stderr)

        hosted_parent = pathlib.Path("/home/runner/work/_temp")
        hosted_runtime = hosted_parent / leaf
        hosted_normal = self.run_guard(
            "/home/runner/work/repository/repository",
            "/home/runner",
            hosted_parent,
            leaf,
        )
        self.assertEqual(hosted_normal.returncode, 0, hosted_normal.stderr)

        for hosted_home in (hosted_runtime, hosted_runtime / "home"):
            with self.subTest(hosted_home=hosted_home):
                rejected = self.run_guard(
                    "/home/runner/work/repository/repository",
                    hosted_home,
                    hosted_parent,
                    leaf,
                )
                self.assertEqual(rejected.returncode, 2)
                self.assertIn("home", rejected.stderr)

    def test_each_harness_refuses_runtime_containing_checkout_and_preserves_it(self) -> None:
        for source_script, leaf in SCRIPTS:
            with self.subTest(script=source_script.name):
                with tempfile.TemporaryDirectory(
                    prefix=f"lf-{source_script.stem}-contains-", dir="/tmp"
                ) as td:
                    root = pathlib.Path(td).resolve()
                    parent = root / "parent"
                    repository = parent / leaf / "repository"
                    copied_script = self.make_checkout(
                        root, source_script, repository
                    )
                    result = self.run_check_mode(
                        copied_script,
                        repository,
                        parent,
                        root / "home",
                    )
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("containing repository", result.stderr)
                    self.assertEqual(
                        (repository / "checkout-sentinel").read_text(
                            encoding="utf-8"
                        ),
                        "preserve\n",
                    )

    def test_each_harness_refuses_runtime_inside_checkout_and_preserves_it(self) -> None:
        for source_script, leaf in SCRIPTS:
            with self.subTest(script=source_script.name):
                with tempfile.TemporaryDirectory(
                    prefix=f"lf-{source_script.stem}-inside-", dir="/tmp"
                ) as td:
                    root = pathlib.Path(td).resolve()
                    repository = root / "repository"
                    copied_script = self.make_checkout(
                        root, source_script, repository
                    )
                    parent = repository / "runtime-parent"
                    result = self.run_check_mode(
                        copied_script,
                        repository,
                        parent,
                        root / "home",
                    )
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("inside repository", result.stderr)
                    self.assertEqual(
                        (repository / "checkout-sentinel").read_text(
                            encoding="utf-8"
                        ),
                        "preserve\n",
                    )

    def test_each_harness_refuses_runtime_leaf_symlink_and_preserves_target(self) -> None:
        for source_script, leaf in SCRIPTS:
            with self.subTest(script=source_script.name):
                with tempfile.TemporaryDirectory(
                    prefix=f"lf-{source_script.stem}-leaf-symlink-", dir="/tmp"
                ) as td:
                    root = pathlib.Path(td).resolve()
                    repository = root / "repository"
                    copied_script = self.make_checkout(
                        root, source_script, repository
                    )
                    parent = root / "parent"
                    target = parent / "victim"
                    target.mkdir(parents=True)
                    sentinel = target / "sentinel"
                    sentinel.write_text("preserve\n", encoding="utf-8")
                    runtime = parent / leaf
                    runtime.symlink_to(target, target_is_directory=True)

                    result = self.run_check_mode(
                        copied_script,
                        repository,
                        parent,
                        root / "home",
                    )

                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("symlink runtime leaf", result.stderr)
                    self.assertTrue(runtime.is_symlink())
                    self.assertEqual(
                        sentinel.read_text(encoding="utf-8"),
                        "preserve\n",
                    )

    def test_check_mode_is_side_effect_free_and_repeatable(self) -> None:
        for source_script, leaf in SCRIPTS:
            with self.subTest(script=source_script.name):
                with tempfile.TemporaryDirectory(
                    prefix=f"lf-{source_script.stem}-allowed-", dir="/tmp"
                ) as td:
                    root = pathlib.Path(td).resolve()
                    repository = root / "repository"
                    copied_script = self.make_checkout(
                        root, source_script, repository
                    )
                    parent = root / "parent"
                    runtime = parent / leaf
                    runtime.mkdir(parents=True)
                    sentinel = runtime / "runtime-sentinel"
                    sentinel.write_text("preserve\n", encoding="utf-8")
                    for attempt in range(2):
                        with self.subTest(attempt=attempt):
                            result = self.run_check_mode(
                                copied_script,
                                repository,
                                parent,
                                root / "home",
                            )
                            self.assertEqual(result.returncode, 0, result.stderr)
                            self.assertEqual(
                                sentinel.read_text(encoding="utf-8"),
                                "preserve\n",
                            )

    def test_harnesses_validate_before_recursive_cleanup_and_parse(self) -> None:
        for script, leaf in SCRIPTS:
            with self.subTest(script=script.name):
                source = script.read_text(encoding="utf-8")
                self.assertIn(f"runtime_leaf={leaf}", source)
                self.assertIn('source "$repo_root/investigations/', source)
                self.assertIn("--check-runtime-parent", source)
                self.assertNotIn(
                    f'${{RUNNER_TEMP:-/tmp}}/{leaf}',
                    source,
                )
                validation = source.index('runtime_root="$(validate_disposable_runtime')
                cleanup = source.index('rm -rf "$runtime_root"')
                self.assertLess(validation, cleanup)
                subprocess.run(
                    ["bash", "-n", str(script)],
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )

        guard_source = GUARD.read_text(encoding="utf-8")
        self.assertIn('if [[ -L "$runtime_path" ]]', guard_source)
        self.assertNotIn("rm -rf", guard_source)
        self.assertNotIn("chmod", guard_source)
        subprocess.run(
            ["bash", "-n", str(GUARD)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )


if __name__ == "__main__":
    unittest.main()
