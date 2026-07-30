from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


FAKE_DEB822 = '''
class Deb822:
    @classmethod
    def iter_paragraphs(cls, stream):
        paragraph = {}
        for raw in stream:
            line = raw.rstrip("\\n")
            if not line:
                if paragraph:
                    yield paragraph
                    paragraph = {}
                continue
            key, value = line.split(":", 1)
            paragraph[key] = value.strip()
        if paragraph:
            yield paragraph


class Release(dict):
    def __init__(self, _stream):
        super().__init__({"Date": "Thu, 01 Jan 1970 00:00:00 +0000"})
'''

WORKER = '''
import os
import pathlib
import signal
import sys
import time

root = pathlib.Path(os.environ["MARKER_DIR"])
(root / "child.pid").write_text(str(os.getpid()), encoding="ascii")

def stop(_signal, _frame):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
time.sleep(float(os.environ["WORKER_SECONDS"]))
(root / "success").write_text("completed\\n", encoding="ascii")
'''


class MmdebstrapCoverageParentSigintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/coverage.py"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-coverage-parent-sigint/"
            "0001-fail-after-parent-sigint.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="coverage-parent-sigint-")
        root = pathlib.Path(cls.work.name)
        cls.baseline = root / "baseline-coverage.py"
        cls.candidate_root = root / "candidate"
        cls.candidate = cls.candidate_root / "upstream/mmdebstrap/coverage.py"
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
        for source in (cls.baseline, cls.candidate):
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", str(source)],
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

    def make_suite(self, label: str, coverage_source: pathlib.Path) -> pathlib.Path:
        suite = pathlib.Path(self.work.name) / label
        suite.mkdir()
        shutil.copy2(coverage_source, suite / "coverage.py")
        (suite / "shared/cache/debian/dists/unstable").mkdir(parents=True)
        (suite / "shared/cache/debian/dists/unstable/InRelease").write_text(
            "Date: Thu, 01 Jan 1970 00:00:00 +0000\n", encoding="utf-8"
        )
        (suite / "tests").mkdir()
        (suite / "tests/interrupt").write_text(
            "#!/bin/sh\nset -eu\nexec python3 \"$MARKER_DIR/worker.py\"\n",
            encoding="utf-8",
        )
        (suite / "coverage.txt").write_text("Test: interrupt\n", encoding="utf-8")
        (suite / "hooks").mkdir()
        for name in ("mmdebstrap", "tarfilter", "proxysolver", "ldconfig.fakechroot"):
            (suite / name).write_text("placeholder\n", encoding="utf-8")
        run_null = suite / "run_null.sh"
        run_null.write_text(
            "#!/bin/sh\nset -eu\nexec /bin/sh shared/test.sh\n", encoding="utf-8"
        )
        run_null.chmod(0o755)
        run_qemu = suite / "run_qemu.sh"
        run_qemu.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        run_qemu.chmod(0o755)

        fake_debian = suite / "debian"
        fake_debian.mkdir()
        (fake_debian / "__init__.py").write_text("", encoding="utf-8")
        (fake_debian / "deb822.py").write_text(FAKE_DEB822, encoding="utf-8")

        fake_bin = suite / "fake-bin"
        fake_bin.mkdir()
        for command in ("shellcheck", "shfmt"):
            path = fake_bin / command
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(0o755)
        return suite

    def environment(self, suite: pathlib.Path, seconds: float) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{suite / 'fake-bin'}:{env['PATH']}",
                "PYTHONPATH": str(suite),
                "SOURCE_DATE_EPOCH": "0",
                "HAVE_QEMU": "no",
                "HAVE_BINFMT": "no",
                "MARKER_DIR": str(suite),
                "WORKER_SECONDS": str(seconds),
            }
        )
        return env

    @staticmethod
    def wait_for_file(path: pathlib.Path, process: subprocess.Popen[str]) -> None:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"coverage exited before child start: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {path}")

    @staticmethod
    def wait_for_pid_exit(pid: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.02)
        raise AssertionError(f"child pid {pid} survived")

    def run_interrupted(
        self, label: str, source: pathlib.Path
    ) -> tuple[int, str, str, pathlib.Path]:
        suite = self.make_suite(label, source)
        process = subprocess.Popen(
            [sys.executable, "coverage.py"],
            cwd=suite,
            env=self.environment(suite, 30),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        child_pid_path = suite / "child.pid"
        self.wait_for_file(child_pid_path, process)
        child_pid = int(child_pid_path.read_text(encoding="ascii"))
        os.kill(process.pid, signal.SIGINT)
        stdout, stderr = process.communicate(timeout=10)
        self.wait_for_pid_exit(child_pid)
        self.assertFalse((suite / "success").exists())
        return process.returncode, stdout, stderr, suite

    def test_baseline_reports_parent_only_sigint_as_success(self) -> None:
        status, _stdout, stderr, _suite = self.run_interrupted(
            "baseline-interrupted", self.baseline
        )
        self.assertEqual(status, 0, stderr)
        self.assertNotIn("interrupted by SIGINT", stderr)

    def test_candidate_reports_parent_only_sigint_as_failure(self) -> None:
        status, _stdout, stderr, _suite = self.run_interrupted(
            "candidate-interrupted", self.candidate
        )
        self.assertEqual(status, 130, stderr)
        self.assertIn("interrupted by SIGINT", stderr)

    def test_candidate_unsignaled_run_still_succeeds(self) -> None:
        suite = self.make_suite("candidate-success", self.candidate)
        result = subprocess.run(
            [sys.executable, "coverage.py"],
            cwd=suite,
            env=self.environment(suite, 0.05),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((suite / "success").exists())
        child_pid = int((suite / "child.pid").read_text(encoding="ascii"))
        self.wait_for_pid_exit(child_pid)
        self.assertIn("result: SUCCESS", result.stderr)

    def test_candidate_source_has_explicit_sigint_exit(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertIn("except KeyboardInterrupt", baseline)
        self.assertIn("            break\n", baseline)
        self.assertNotIn("raise SystemExit(130)", baseline)
        self.assertIn("raise SystemExit(130)", candidate)


if __name__ == "__main__":
    unittest.main()
