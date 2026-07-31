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
from typing import BinaryIO

from tests import test_mmdebstrap_coverage_process_group as process_group
from tests import test_mmdebstrap_coverage_parent_sigint as status_only


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN_NULL = ROOT / "upstream/mmdebstrap/run_null.sh"


def passwordless_sudo_available() -> bool:
    if shutil.which("sudo") is None:
        return False
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@unittest.skipUnless(
    pathlib.Path("/proc").is_dir()
    and hasattr(os, "killpg")
    and passwordless_sudo_available(),
    "requires Linux /proc, POSIX process groups, and passwordless sudo",
)
class MmdebstrapCoverageSudoProcessGroupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.work = tempfile.TemporaryDirectory(prefix="coverage-sudo-group-")
        root = pathlib.Path(cls.work.name)
        cls.baseline = root / "baseline-coverage.py"
        cls.status_root = root / "status-only"
        cls.status_candidate = cls.status_root / "upstream/mmdebstrap/coverage.py"
        cls.group_root = root / "group-owned"
        cls.group_candidate = cls.group_root / "upstream/mmdebstrap/coverage.py"

        for destination in (
            cls.baseline,
            cls.status_candidate,
            cls.group_candidate,
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(process_group.SOURCE, destination)

        cls.apply_patch(cls.status_root, process_group.STATUS_PATCH)
        cls.apply_patch(cls.group_root, process_group.GROUP_PATCH)
        for source in (cls.baseline, cls.status_candidate, cls.group_candidate):
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", str(source)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            if compiled.returncode != 0:
                cls.work.cleanup()
                raise AssertionError(compiled.stdout + compiled.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    @classmethod
    def apply_patch(cls, tree: pathlib.Path, patch: pathlib.Path) -> None:
        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(patch),
            ],
            cwd=tree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)

    def make_suite(self, label: str, coverage_source: pathlib.Path) -> pathlib.Path:
        suite = pathlib.Path(self.work.name) / label
        suite.mkdir()
        shutil.copy2(coverage_source, suite / "coverage.py")
        shutil.copy2(RUN_NULL, suite / "run_null.sh")
        (suite / "run_null.sh").chmod(0o755)
        (suite / "run_qemu.sh").write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        (suite / "run_qemu.sh").chmod(0o755)

        (suite / "shared/cache/debian/dists/unstable").mkdir(parents=True)
        (suite / "shared/cache/debian/dists/unstable/InRelease").write_text(
            "Date: Thu, 01 Jan 1970 00:00:00 +0000\n",
            encoding="utf-8",
        )
        os.mkfifo(suite / "release.fifo")

        (suite / "tests").mkdir()
        (suite / "tests/interrupt").write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "printf '%s\\n' \"$$\" >sudo-worker.pid\n"
            "ps -o pgid= -p \"$$\" | tr -d ' ' >sudo-worker.pgid\n"
            "id -u >sudo-worker.uid\n"
            "printf ready >sudo-worker.ready\n"
            "IFS= read -r token <../release.fifo\n"
            "printf later >sudo-later\n",
            encoding="utf-8",
        )
        (suite / "coverage.txt").write_text(
            "Test: interrupt\nNeeds-Root: true\n",
            encoding="utf-8",
        )
        (suite / "hooks").mkdir()
        for name in (
            "mmdebstrap",
            "tarfilter",
            "proxysolver",
            "ldconfig.fakechroot",
        ):
            (suite / name).write_text("placeholder\n", encoding="utf-8")

        fake_debian = suite / "debian"
        fake_debian.mkdir()
        (fake_debian / "__init__.py").write_text("", encoding="utf-8")
        (fake_debian / "deb822.py").write_text(
            status_only.FAKE_DEB822,
            encoding="utf-8",
        )

        fake_bin = suite / "fake-bin"
        fake_bin.mkdir()
        for command in ("shellcheck", "shfmt"):
            path = fake_bin / command
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(0o755)
        return suite

    @staticmethod
    def environment(suite: pathlib.Path) -> dict[str, str]:
        return process_group.MmdebstrapCoverageProcessGroupTest.environment(suite)

    @staticmethod
    def wait_for_sudo_later(suite: pathlib.Path) -> None:
        marker = suite / "shared/sudo-later"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if marker.exists():
                return
            time.sleep(0.02)
        raise AssertionError("orphaned sudo worker did not continue")

    def start_coverage(
        self,
        suite: pathlib.Path,
    ) -> tuple[subprocess.Popen[bytes], BinaryIO, BinaryIO]:
        stdout = open(suite / "coverage.stdout", "wb")
        stderr = open(suite / "coverage.stderr", "wb")
        process = subprocess.Popen(
            [sys.executable, "coverage.py"],
            cwd=suite,
            env=self.environment(suite),
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        self.addCleanup(stdout.close)
        self.addCleanup(stderr.close)
        self.addCleanup(
            process_group.MmdebstrapCoverageProcessGroupTest.stop_coverage,
            process,
        )
        return process, stdout, stderr

    def worker_identity(
        self,
        suite: pathlib.Path,
        process: subprocess.Popen[bytes],
    ) -> tuple[int, int, list[dict[str, int | str]]]:
        shared = suite / "shared"
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_file(
            shared / "sudo-worker.ready",
            process,
        )
        worker_pid = int(
            (shared / "sudo-worker.pid").read_text(encoding="ascii")
        )
        worker_pgid = int(
            (shared / "sudo-worker.pgid").read_text(encoding="ascii")
        )
        worker_uid = int(
            (shared / "sudo-worker.uid").read_text(encoding="ascii")
        )
        self.assertEqual(worker_uid, 0)
        self.assertEqual(worker_pgid, os.getpgid(worker_pid))
        self.addCleanup(
            process_group.MmdebstrapCoverageProcessGroupTest.terminate_group,
            worker_pgid,
        )
        before = process_group.MmdebstrapCoverageProcessGroupTest.group_members(
            worker_pgid
        )
        commands = [str(member["command"]) for member in before]
        self.assertTrue(
            any("run_null.sh SUDO" in command for command in commands),
            commands,
        )
        self.assertTrue(any("sudo --preserve-env" in command for command in commands))
        return worker_pid, worker_pgid, before

    def run_parent_only_sigint(
        self,
        label: str,
        source: pathlib.Path,
        *,
        expected_status: int,
        expect_survivors: bool,
    ) -> tuple[pathlib.Path, list[dict[str, int | str]]]:
        suite = self.make_suite(label, source)
        process, stdout, stderr = self.start_coverage(suite)
        _worker_pid, worker_pgid, before = self.worker_identity(suite, process)

        os.kill(process.pid, signal.SIGINT)
        status = process.wait(timeout=10)
        stdout.close()
        stderr.close()
        self.assertEqual(
            status,
            expected_status,
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

        live = (
            process_group.MmdebstrapCoverageProcessGroupTest.live_group_members(
                worker_pgid
            )
        )
        if expect_survivors:
            self.assertTrue(live, before)
            self.assertFalse((suite / "shared/sudo-later").exists())
            process_group.MmdebstrapCoverageProcessGroupTest.release_test(suite)
            self.wait_for_sudo_later(suite)
        else:
            self.assertFalse(live, live)
            self.assertFalse((suite / "shared/sudo-later").exists())
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_no_live_group(
            worker_pgid
        )
        return suite, before

    def test_imported_sudo_wrapper_leaves_root_worker(self) -> None:
        suite, before = self.run_parent_only_sigint(
            "sudo-baseline",
            self.baseline,
            expected_status=0,
            expect_survivors=True,
        )
        self.assertGreaterEqual(len(before), 3)
        self.assertNotIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_status_only_sudo_wrapper_still_leaves_root_worker(self) -> None:
        suite, before = self.run_parent_only_sigint(
            "sudo-status-only",
            self.status_candidate,
            expected_status=130,
            expect_survivors=True,
        )
        self.assertGreaterEqual(len(before), 3)
        self.assertIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_group_candidate_stops_sudo_wrapper_operation(self) -> None:
        suite, before = self.run_parent_only_sigint(
            "sudo-group-owned",
            self.group_candidate,
            expected_status=130,
            expect_survivors=False,
        )
        self.assertGreaterEqual(len(before), 3)
        self.assertIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_group_candidate_sudo_unsignaled_run_succeeds(self) -> None:
        suite = self.make_suite("sudo-success", self.group_candidate)
        process, stdout, stderr = self.start_coverage(suite)
        _worker_pid, worker_pgid, _before = self.worker_identity(suite, process)
        process_group.MmdebstrapCoverageProcessGroupTest.release_test(suite)
        status = process.wait(timeout=10)
        stdout.close()
        stderr.close()

        self.assertEqual(
            status,
            0,
            (suite / "coverage.stderr").read_text(errors="replace"),
        )
        self.assertTrue((suite / "shared/sudo-later").exists())
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_no_live_group(
            worker_pgid
        )
        self.assertIn(
            "result: SUCCESS",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )


if __name__ == "__main__":
    unittest.main()
