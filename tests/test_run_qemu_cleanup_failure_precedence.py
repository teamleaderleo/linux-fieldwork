from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from tests import test_run_qemu_result_precedence as result_precedence


class RunQemuCleanupFailurePrecedenceTest(unittest.TestCase):
    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def run_case(self, root: pathlib.Path, host_status: int) -> tuple[int, list[str]]:
        helper = result_precedence.RunQemuResultPrecedenceTest(methodName="runTest")
        candidate = helper.prepare_candidate(root)
        functions, traps = helper.candidate_blocks(candidate)

        runtime = root / f"host-{host_status}"
        runtime.mkdir()
        shared = runtime / "shared"
        shared.mkdir()
        (shared / "output.txt").touch()
        (shared / "exitstatus.txt").write_text("0\n", encoding="utf-8")
        tmpdir = runtime / "tmp"
        tmpdir.mkdir()
        (tmpdir / "log").touch()

        script = runtime / "case.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"tmpdir={self.quote(str(tmpdir))}\n"
            "rm() {\n"
            "  printf 'rm\\n' >>\"$runtime/cleanup.log\"\n"
            "  return 74\n"
            "}\n"
            "rmdir() {\n"
            "  printf 'rmdir\\n' >>\"$runtime/cleanup.log\"\n"
            "  return 75\n"
            "}\n"
            + functions
            + "\n"
            + traps
            + f"exit {host_status}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        completed = subprocess.run(
            ["/bin/sh", str(script)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        return completed.returncode, (runtime / "cleanup.log").read_text().splitlines()

    def test_first_cleanup_failure_wins_after_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-cleanup-first-") as td:
            status, log = self.run_case(pathlib.Path(td), 0)
        self.assertEqual(status, 74)
        self.assertEqual(log, ["rm", "rmdir"])

    def test_primary_host_failure_wins_over_all_cleanup_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="run-qemu-cleanup-host-") as td:
            status, log = self.run_case(pathlib.Path(td), 42)
        self.assertEqual(status, 42)
        self.assertEqual(log, ["rm", "rmdir"])


if __name__ == "__main__":
    unittest.main()
