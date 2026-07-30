from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


class HookFreeHardFailureGuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source_root = cls.repo / "upstream/mmdebstrap"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure/"
            "0001-run-hook-free-capability-case-as-hard-failure.patch"
        )

    def candidate_testsuite(self, root: pathlib.Path) -> str:
        tree = root / "candidate"
        for relative in ("coverage.txt", "coverage.py", "debian/tests/testsuite"):
            destination = tree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.source_root / relative, destination)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        return (tree / "debian/tests/testsuite").read_text(encoding="utf-8")

    @staticmethod
    def hard_block(testsuite: str) -> str:
        start = testsuite.index(
            "# run hook-free tests whose failures remain authoritative"
        )
        end = testsuite.index(
            "# subtract 10 seconds to account for the inaccuracy in measuring time",
            start,
        )
        return testsuite[start:end]

    @staticmethod
    def write_fake(path: pathlib.Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def execute(
        self,
        root: pathlib.Path,
        block: str,
        *,
        selection: str,
        timeout_value: int,
        timeout_status: int,
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
        fakebin = root / "fakebin"
        fakebin.mkdir(parents=True)
        call_log = root / "timeout-called"
        self.write_fake(
            fakebin / "grep-dctrl",
            "#!/bin/sh\nprintf '%s' \"$FAKE_SELECTION\"\n",
        )
        self.write_fake(
            fakebin / "timeout",
            "#!/bin/sh\nprintf 'called\\n' >\"$FAKE_TIMEOUT_LOG\"\n"
            "exit \"$FAKE_TIMEOUT_STATUS\"\n",
        )
        script = root / "phase.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"TIMEOUT={timeout_value}\n"
            "AUTOPKGTEST_NORMAL_USER=tester\n"
            "DEFAULT_DIST=testing\n"
            "RUN_MA_SAME_TESTS=no\n"
            "SRC=/source\n"
            ": > coverage.txt\n"
            + block
            + "exit 0\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fakebin}:/usr/bin:/bin",
                "FAKE_SELECTION": selection,
                "FAKE_TIMEOUT_LOG": str(call_log),
                "FAKE_TIMEOUT_STATUS": str(timeout_status),
            }
        )
        result = subprocess.run(
            ["/bin/sh", str(script)],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return result, call_log

    def test_empty_selection_fails_before_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hook-free-empty-") as tmp:
            root = pathlib.Path(tmp)
            block = self.hard_block(self.candidate_testsuite(root))
            result, call_log = self.execute(
                root / "run", block, selection="", timeout_value=100, timeout_status=0
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("no hook-free hard-failure tests", result.stderr)
            self.assertFalse(call_log.exists())

    def test_exhausted_time_is_neutral_before_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hook-free-time-") as tmp:
            root = pathlib.Path(tmp)
            block = self.hard_block(self.candidate_testsuite(root))
            result, call_log = self.execute(
                root / "run",
                block,
                selection="root-without-cap-sys-admin\n",
                timeout_value=0,
                timeout_status=0,
            )
            self.assertEqual(result.returncode, 77, result.stderr)
            self.assertIn("no time remains", result.stderr)
            self.assertFalse(call_log.exists())

    def test_selected_child_failure_remains_hard(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hook-free-status-") as tmp:
            root = pathlib.Path(tmp)
            block = self.hard_block(self.candidate_testsuite(root))
            result, call_log = self.execute(
                root / "run",
                block,
                selection="root-without-cap-sys-admin\n",
                timeout_value=100,
                timeout_status=2,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertTrue(call_log.exists())


if __name__ == "__main__":
    unittest.main()
