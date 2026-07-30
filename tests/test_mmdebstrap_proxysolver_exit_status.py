from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


SUCCESS_OUTPUT = "Install: 1\nPackage: example\n"
FAILURE_OUTPUT = "Install: 1\n"


class MmdebstrapProxysolverExitStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/proxysolver"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-proxysolver-exit-status/"
            "0001-propagate-solver-status.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="proxysolver-status-")
        root = pathlib.Path(cls.work.name)
        cls.fake_solver = root / "fake-solver"
        cls.fake_solver.write_text(
            """#!/bin/sh
set -eu
cat >/dev/null
printf '%s' "$FAKE_SOLVER_OUTPUT"
exit "$FAKE_SOLVER_STATUS"
""",
            encoding="utf-8",
        )
        cls.fake_solver.chmod(0o755)

        cls.baseline = root / "baseline-proxysolver"
        cls.candidate_root = root / "candidate"
        cls.candidate = cls.candidate_root / "upstream/mmdebstrap/proxysolver"
        cls.candidate.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.baseline)
        shutil.copy2(cls.source, cls.candidate)

        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "-p1",
                "-i",
                str(cls.patch),
            ],
            cwd=cls.candidate_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)

        solver_literal = '"/usr/lib/apt/solvers/apt"'
        replacement = repr(str(cls.fake_solver))
        for path in (cls.baseline, cls.candidate):
            text = path.read_text(encoding="utf-8")
            if text.count(solver_literal) != 2:
                cls.work.cleanup()
                raise AssertionError("unexpected solver path occurrence count")
            path.write_text(
                text.replace(solver_literal, replacement), encoding="utf-8"
            )

        for path in (cls.baseline, cls.candidate):
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if compiled.returncode != 0:
                cls.work.cleanup()
                raise AssertionError(compiled.stdout + compiled.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def run_wrapper(
        self, script: pathlib.Path, label: str, status: int, output: str
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        dump = pathlib.Path(self.work.name) / f"{label}.dump"
        env = os.environ.copy()
        env.update(
            {
                "APT_EDSP_DUMP_FILENAME": str(dump),
                "FAKE_SOLVER_STATUS": str(status),
                "FAKE_SOLVER_OUTPUT": output,
            }
        )
        result = subprocess.run(
            [sys.executable, str(script)],
            input="Request: EDSP\n\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=10,
        )
        return result, dump.read_text(encoding="utf-8")

    def test_success_status_and_capture_remain_unchanged(self) -> None:
        baseline, baseline_dump = self.run_wrapper(
            self.baseline, "baseline-success", 0, SUCCESS_OUTPUT
        )
        candidate, candidate_dump = self.run_wrapper(
            self.candidate, "candidate-success", 0, SUCCESS_OUTPUT
        )
        for result, dump in (
            (baseline, baseline_dump),
            (candidate, candidate_dump),
        ):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, SUCCESS_OUTPUT)
            self.assertEqual(dump, SUCCESS_OUTPUT)

    def test_candidate_propagates_failing_solver_status(self) -> None:
        baseline, baseline_dump = self.run_wrapper(
            self.baseline, "baseline-failure", 7, FAILURE_OUTPUT
        )
        candidate, candidate_dump = self.run_wrapper(
            self.candidate, "candidate-failure", 7, FAILURE_OUTPUT
        )
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        self.assertEqual(candidate.returncode, 7, candidate.stderr)
        self.assertEqual(baseline.stdout, FAILURE_OUTPUT)
        self.assertEqual(candidate.stdout, FAILURE_OUTPUT)
        self.assertEqual(baseline_dump, FAILURE_OUTPUT)
        self.assertEqual(candidate_dump, FAILURE_OUTPUT)

    def test_candidate_source_checks_child_returncode(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertNotIn("if returncode != 0", baseline)
        self.assertIn("returncode = p.wait()", candidate)
        self.assertIn("raise SystemExit(returncode)", candidate)


if __name__ == "__main__":
    unittest.main()
