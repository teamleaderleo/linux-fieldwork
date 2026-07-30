from __future__ import annotations

import pathlib
import subprocess
import unittest


class LF12ProbeSafetyTest(unittest.TestCase):
    def test_runner_refuses_root_work_directory(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        runner = repo / (
            "programmes/debian-packages/lanes/"
            "LF-12-reproducible-package-variance/scouts/"
            "LF-SCOUT-DEB-02/artifacts/run-variance-probe.sh"
        )
        completed = subprocess.run(
            ["bash", str(runner), "/"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refusing unsafe run directory", completed.stderr)

    def test_runner_refuses_non_temporary_path(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        runner = repo / (
            "programmes/debian-packages/lanes/"
            "LF-12-reproducible-package-variance/scouts/"
            "LF-SCOUT-DEB-02/artifacts/run-variance-probe.sh"
        )
        completed = subprocess.run(
            ["bash", str(runner), str(repo / "unsafe-lf12-work")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("run directory must be beneath", completed.stderr)


if __name__ == "__main__":
    unittest.main()
