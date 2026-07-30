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
            "installed-command-wrapper.patch"
        )
        cls.runner = cls.repo / (
            "scripts/reproduce-mmdebstrap-autopkgtest-style-gate-control.sh"
        )

    def test_wrapper_patch_applies_to_exact_imported_testsuite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mmdebstrap-style-gate-") as td:
            candidate = pathlib.Path(td) / "candidate"
            testsuite = candidate / "debian/tests/testsuite"
            testsuite.parent.mkdir(parents=True)
            shutil.copy2(
                self.repo / "upstream/mmdebstrap/debian/tests/testsuite",
                testsuite,
            )
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate), "-i", str(self.patch)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            text = testsuite.read_text()
            self.assertIn('exec /usr/bin/mmdebstrap "$@"', text)
            self.assertIn('CMD="./mmdebstrap-under-test ', text)
            self.assertNotIn('CMD="mmdebstrap --setup-hook=', text)

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
