from __future__ import annotations

import os
import pathlib
import subprocess
import unittest


class ChrootlessTargetTmpdirSafetyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.runner = cls.repo / (
            "investigations/mmdebstrap-chrootless-env/"
            "run-target-tmpdir-regression.sh"
        )

    def run_with_temp_root(self, value: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["RUNNER_TEMP"] = value
        return subprocess.run(
            ["bash", str(self.runner)],
            cwd=self.repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_refuses_root_temporary_directory(self) -> None:
        completed = self.run_with_temp_root("/")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refusing unsafe temporary root", completed.stderr)

    def test_resolves_parent_components_before_validation(self) -> None:
        completed = self.run_with_temp_root("/tmp/lf70/../..")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refusing unsafe temporary root", completed.stderr)

    def test_refuses_non_disposable_temporary_directory(self) -> None:
        completed = self.run_with_temp_root(str(self.repo))
        self.assertEqual(completed.returncode, 2)
        self.assertIn("temporary root must be disposable", completed.stderr)


if __name__ == "__main__":
    unittest.main()
