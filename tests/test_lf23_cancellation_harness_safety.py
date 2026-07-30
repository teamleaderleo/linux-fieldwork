from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


class LF23CancellationHarnessSafetyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.harness = cls.repo / (
            "programmes/services-resources/lanes/"
            "LF-23-cancellation-subprocess-fd-cleanup/scouts/"
            "LF-SCOUT-PROC-01/artifacts/cancellation_harness.py"
        )

    def run_with_output(
        self,
        output: pathlib.Path,
        *,
        tmpdir: pathlib.Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = None
        if tmpdir is not None:
            env = dict(os.environ, TMPDIR=str(tmpdir))
        return subprocess.run(
            [sys.executable, str(self.harness), "--output", str(output)],
            cwd=self.repo,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_refuses_filesystem_root(self) -> None:
        completed = self.run_with_output(pathlib.Path("/"))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("output must be a child", completed.stderr)

    def test_refuses_and_preserves_path_outside_disposable_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf23-unsafe-", dir=self.repo) as td:
            output = pathlib.Path(td)
            sentinel = output / "sentinel"
            sentinel.write_text("preserve me\n")

            completed = self.run_with_output(output, tmpdir=self.repo)

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("output must be a child", completed.stderr)
            self.assertEqual(sentinel.read_text(), "preserve me\n")


if __name__ == "__main__":
    unittest.main()
