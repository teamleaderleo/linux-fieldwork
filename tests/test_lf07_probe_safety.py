from __future__ import annotations

import pathlib
import subprocess
import unittest


class LF07ProbeSafetyTest(unittest.TestCase):
    def test_runner_refuses_root_work_directory(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        runner = repo / (
            "programmes/debian-packages/lanes/"
            "LF-07-maintainer-script-interruption-idempotency/scouts/"
            "LF-SCOUT-DEB-01/artifacts/run-probe.sh"
        )
        completed = subprocess.run(
            ["sh", str(runner), "/"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refusing unsafe work directory", completed.stderr)

    def test_runner_refuses_path_outside_temporary_roots(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        runner = repo / (
            "programmes/debian-packages/lanes/"
            "LF-07-maintainer-script-interruption-idempotency/scouts/"
            "LF-SCOUT-DEB-01/artifacts/run-probe.sh"
        )
        completed = subprocess.run(
            ["sh", str(runner), str(repo / "unsafe-lf07-work")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("work directory must be a child", completed.stderr)


if __name__ == "__main__":
    unittest.main()
