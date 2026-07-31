from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class MmdebstrapProcessGroupKillCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.source_root = self.root / "upstream/mmdebstrap"
        self.source = self.source_root / "tests/sigint-during-customize-hook"
        self.patch = (
            self.root
            / "investigations/mmdebstrap-autopkgtest-1141078"
            / "sigint-process-group-kill-sid.patch"
        )
        self.wrapper_patch = (
            self.root
            / "investigations/mmdebstrap-autopkgtest-1141078"
            / "installed-command-wrapper.patch"
        )
        self.sourcesfilter_patch = (
            self.root
            / "investigations/mmdebstrap-autopkgtest-1141078"
            / "sourcesfilter-deb822.patch"
        )
        self.capability_patch = (
            self.root
            / "investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure"
            / "0001-run-hook-free-capability-case-as-hard-failure.patch"
        )
        self.phase_order_tool = (
            self.root / "tools/reorder_mmdebstrap_hook_free_phase.py"
        )
        self.harness = self.root / "scripts/reproduce-mmdebstrap-autopkgtest.sh"
        self.original = '/bin/kill --signal INT -- "$pgid"'
        self.replacement = "/bin/dash -c 'kill -s INT -- \"$1\"' dash \"$pgid\""

    def apply_patch(
        self,
        tree: Path,
        patch_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-d",
                str(tree),
                "-i",
                str(patch_path),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def assert_exact_application(
        self,
        completed: subprocess.CompletedProcess[str],
    ) -> None:
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        combined = (completed.stdout + completed.stderr).lower()
        self.assertNotIn("fuzz", combined)
        self.assertNotIn("offset", combined)

    def apply_patch_to_signal_source(
        self,
        source_text: str,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as temporary:
            tree = Path(temporary) / "source"
            test_path = tree / "tests" / self.source.name
            test_path.parent.mkdir(parents=True)
            test_path.write_text(source_text, encoding="utf-8")
            completed = self.apply_patch(tree, self.patch)
            return completed, test_path.read_text(encoding="utf-8")

    def test_patch_is_one_exact_replacement(self) -> None:
        patch_text = self.patch.read_text(encoding="utf-8")
        self.assertEqual(patch_text.count("diff --git "), 1)
        self.assertEqual(patch_text.count("@@ "), 1)
        self.assertEqual(patch_text.count("-" + self.original), 1)
        self.assertEqual(patch_text.count("+" + self.replacement), 1)
        self.assertIn("@@ -7,6 +7,6 @@", patch_text)

    def test_zero_fuzz_application_preserves_complete_shell_and_source(self) -> None:
        source_text = self.source.read_text(encoding="utf-8")
        self.assertEqual(source_text.count(self.original), 1)
        self.assertNotIn(self.replacement, source_text)

        completed, candidate = self.apply_patch_to_signal_source(source_text)
        self.assert_exact_application(completed)
        self.assertNotIn(self.original, candidate)
        self.assertEqual(candidate.count(self.replacement), 1)
        self.assertEqual(self.source.read_text(encoding="utf-8"), source_text)

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(candidate)
            candidate_path = Path(handle.name)
        try:
            syntax = subprocess.run(
                ["/bin/sh", "-n", str(candidate_path)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
        finally:
            candidate_path.unlink()
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_source_drift_and_second_application_fail_closed(self) -> None:
        source_text = self.source.read_text(encoding="utf-8")
        drifted = source_text.replace(self.original, "/bin/kill -INT -- \"$pgid\"")
        drift_result, drift_candidate = self.apply_patch_to_signal_source(drifted)
        self.assertNotEqual(drift_result.returncode, 0)
        self.assertEqual(drift_candidate, drifted)

        first_result, first_candidate = self.apply_patch_to_signal_source(source_text)
        self.assert_exact_application(first_result)
        second_result, second_candidate = self.apply_patch_to_signal_source(first_candidate)
        self.assertNotEqual(second_result.returncode, 0)
        self.assertEqual(second_candidate, first_candidate)

    def copy_composition_surface(self, tree: Path) -> None:
        paths = (
            "debian/tests/testsuite",
            "debian/tests/sourcesfilter",
            "coverage.py",
            "coverage.txt",
            "tests/sigint-during-customize-hook",
        )
        for relative in paths:
            source = self.source_root / relative
            destination = tree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def test_all_four_patches_compose_without_fuzz_or_offset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tree = Path(temporary) / "source"
            self.copy_composition_surface(tree)
            original_hash_inputs = {
                relative: (self.source_root / relative).read_bytes()
                for relative in (
                    "debian/tests/testsuite",
                    "debian/tests/sourcesfilter",
                    "coverage.py",
                    "coverage.txt",
                    "tests/sigint-during-customize-hook",
                )
            }
            ordered_patches = (
                self.sourcesfilter_patch,
                self.capability_patch,
                self.wrapper_patch,
                self.patch,
            )
            for patch_path in ordered_patches:
                with self.subTest(patch=patch_path.name):
                    completed = self.apply_patch(tree, patch_path)
                    self.assert_exact_application(completed)

            reordered = subprocess.run(
                [
                    "python3",
                    str(self.phase_order_tool),
                    str(tree / "debian/tests/testsuite"),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(reordered.returncode, 0, reordered.stderr)

            shell_syntax = subprocess.run(
                [
                    "/bin/sh",
                    "-n",
                    str(tree / "debian/tests/testsuite"),
                    str(tree / "tests/sigint-during-customize-hook"),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(shell_syntax.returncode, 0, shell_syntax.stderr)

            python_syntax = subprocess.run(
                [
                    "python3",
                    "-m",
                    "py_compile",
                    str(tree / "coverage.py"),
                    str(tree / "debian/tests/sourcesfilter"),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(python_syntax.returncode, 0, python_syntax.stderr)

            transformed_signal = (
                tree / "tests/sigint-during-customize-hook"
            ).read_text(encoding="utf-8")
            transformed_testsuite = (tree / "debian/tests/testsuite").read_text(
                encoding="utf-8"
            )
            self.assertEqual(transformed_signal.count(self.replacement), 1)
            self.assertIn("Needs-Hook-Free-APT-Config", transformed_testsuite)
            self.assertIn("$AUTOPKGTEST_TMP/mmdebstrap", transformed_testsuite)

            for relative, original_bytes in original_hash_inputs.items():
                self.assertEqual((self.source_root / relative).read_bytes(), original_bytes)

    def test_reproduction_harness_applies_and_records_exact_override(self) -> None:
        script = self.harness.read_text(encoding="utf-8")
        self.assertIn(
            'signal_patch="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/sigint-process-group-kill-sid.patch"',
            script,
        )
        self.assertIn('if [[ ! -f $signal_patch ]]; then', script)
        self.assertIn('apply_exact_patch signal "$signal_patch"', script)
        self.assertIn('"$source_tree/tests/sigint-during-customize-hook"', script)
        self.assertIn("Integration signal override", script)
        self.assertIn("zero fuzz and zero offset", script)
        self.assertEqual(script.count("apply_exact_patch "), 4)


if __name__ == "__main__":
    unittest.main()
