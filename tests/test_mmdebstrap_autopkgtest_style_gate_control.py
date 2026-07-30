from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


class MmdebstrapAutopkgtestStyleGateControlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-autopkgtest-1141078/"
            "installed-command-style-gate-control.patch"
        )
        cls.runner = cls.repo / (
            "scripts/reproduce-mmdebstrap-autopkgtest-style-gate-control.sh"
        )

    def test_control_patch_applies_to_exact_imported_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mmdebstrap-style-gate-") as td:
            candidate = pathlib.Path(td) / "candidate"
            testsuite = candidate / "debian/tests/testsuite"
            coverage = candidate / "coverage.sh"
            testsuite.parent.mkdir(parents=True)
            shutil.copy2(
                self.repo / "upstream/mmdebstrap/debian/tests/testsuite",
                testsuite,
            )
            shutil.copy2(self.repo / "upstream/mmdebstrap/coverage.sh", coverage)
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate), "-i", str(self.patch)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            testsuite_text = testsuite.read_text()
            coverage_text = coverage.read_text()
            self.assertIn(
                'SKIP_MMSCRIPT_CHECKS=yes CMD="mmdebstrap --setup-hook=',
                testsuite_text,
            )
            self.assertIn(
                'if [ "${SKIP_MMSCRIPT_CHECKS-}" != yes ] && [ -e "$MMSCRIPT" ]; then',
                coverage_text,
            )
            self.assertNotIn("mmdebstrap-under-test", testsuite_text)
            self.assertNotIn("exec /usr/bin/mmdebstrap", testsuite_text)

    def test_control_skips_only_mmdebstrap_script_checks(self) -> None:
        patch_text = self.patch.read_text()
        self.assertIn("SKIP_MMSCRIPT_CHECKS", patch_text)
        self.assertNotIn("black --check", patch_text)
        self.assertNotIn("shellcheck", patch_text)
        self.assertNotIn("shfmt", patch_text)

    def test_runner_refuses_root_output_before_execution(self) -> None:
        completed = subprocess.run(
            ["bash", str(self.runner), "/"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refusing unsafe output directory", completed.stderr)

    def test_runner_refuses_repository_path_outside_runs(self) -> None:
        completed = subprocess.run(
            ["bash", str(self.runner), str(self.repo / "unsafe-output")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("output must be a child", completed.stderr)


if __name__ == "__main__":
    unittest.main()
