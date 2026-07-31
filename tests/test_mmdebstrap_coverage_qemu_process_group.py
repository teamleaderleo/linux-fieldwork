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
RUN_QEMU = ROOT / "upstream/mmdebstrap/run_qemu.sh"

QEMU_WORKER = r"""
import os
import pathlib

root = pathlib.Path(os.environ["MARKER_DIR"])
(root / "qemu-worker.pid").write_text(str(os.getpid()), encoding="ascii")
(root / "qemu-worker.pgid").write_text(str(os.getpgrp()), encoding="ascii")
(root / "qemu-worker.ready").write_text("ready\n", encoding="ascii")
with (root / "release.fifo").open("r", encoding="ascii") as release:
    release.readline()
(root / "shared/exitstatus.txt").write_text("0\n", encoding="ascii")
(root / "qemu-later").write_text("later\n", encoding="ascii")
"""

FAKE_TIMEOUT = r"""#!/bin/sh
set -eu
while [ "$#" -gt 0 ]; do
  shift
done
exec python3 "$MARKER_DIR/qemu-worker.py"
"""

FAKE_LSCPU = r"""#!/bin/sh
cat <<'EOF'
Model name: Generic CPU
Core(s) per socket: 1
EOF
"""


@unittest.skipUnless(
    pathlib.Path("/proc").is_dir() and hasattr(os, "killpg"),
    "requires Linux /proc and POSIX process groups",
)
class MmdebstrapCoverageQemuProcessGroupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.work = tempfile.TemporaryDirectory(prefix="coverage-qemu-group-")
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
        shutil.copy2(RUN_QEMU, suite / "run_qemu.sh")
        (suite / "run_qemu.sh").chmod(0o755)
        (suite / "run_null.sh").write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        (suite / "run_null.sh").chmod(0o755)

        (suite / "shared/cache/debian/dists/unstable").mkdir(parents=True)
        (suite / "shared/cache/debian/dists/unstable/InRelease").write_text(
            "Date: Thu, 01 Jan 1970 00:00:00 +0000\n",
            encoding="utf-8",
        )
        (suite / "shared/cache/debian-unstable.ext4").write_bytes(b"image\n")
        (suite / "shared/exitstatus.txt").write_text("1\n", encoding="ascii")
        os.mkfifo(suite / "release.fifo")
        (suite / "qemu-worker.py").write_text(QEMU_WORKER, encoding="utf-8")

        (suite / "tests").mkdir()
        (suite / "tests/interrupt").write_text(
            "#!/bin/sh\nexit 0\n",
            encoding="utf-8",
        )
        (suite / "coverage.txt").write_text(
            "Test: interrupt\nNeeds-QEMU: true\n",
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
        commands = {
            "shellcheck": "#!/bin/sh\nexit 0\n",
            "shfmt": "#!/bin/sh\nexit 0\n",
            "timeout": FAKE_TIMEOUT,
            "lscpu": FAKE_LSCPU,
        }
        for command, content in commands.items():
            path = fake_bin / command
            path.write_text(content, encoding="utf-8")
            path.chmod(0o755)
        return suite

    @staticmethod
    def environment(suite: pathlib.Path) -> dict[str, str]:
        env = process_group.MmdebstrapCoverageProcessGroupTest.environment(suite)
        env["HAVE_QEMU"] = "yes"
        env["MMDEBSTRAP_TESTS_DEBUG"] = "no"
        return env

    @staticmethod
    def wait_for_qemu_later(suite: pathlib.Path) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if (suite / "qemu-later").exists():
                return
            time.sleep(0.02)
        raise AssertionError("orphaned QEMU-like worker did not continue")

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
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_file(
            suite / "qemu-worker.ready",
            process,
        )
        worker_pid = int(
            (suite / "qemu-worker.pid").read_text(encoding="ascii")
        )
        worker_pgid = int(
            (suite / "qemu-worker.pgid").read_text(encoding="ascii")
        )
        self.assertEqual(worker_pgid, os.getpgid(worker_pid))
        self.addCleanup(
            process_group.MmdebstrapCoverageProcessGroupTest.terminate_group,
            worker_pgid,
        )
        before = process_group.MmdebstrapCoverageProcessGroupTest.group_members(
            worker_pgid
        )
        self.assertGreaterEqual(len(before), 2)

        os.kill(process.pid, signal.SIGINT)
        if expect_survivors:
            with self.assertRaises(subprocess.TimeoutExpired):
                process.wait(timeout=0.5)
            live = (
                process_group.MmdebstrapCoverageProcessGroupTest.live_group_members(
                    worker_pgid
                )
            )
            self.assertTrue(live, before)
            self.assertFalse((suite / "qemu-later").exists())
            process_group.MmdebstrapCoverageProcessGroupTest.release_test(suite)
            self.wait_for_qemu_later(suite)
            status = process.wait(timeout=10)
        else:
            status = process.wait(timeout=10)
            live = (
                process_group.MmdebstrapCoverageProcessGroupTest.live_group_members(
                    worker_pgid
                )
            )
            self.assertFalse(live, live)
            self.assertFalse((suite / "qemu-later").exists())

        stdout.close()
        stderr.close()
        self.assertEqual(
            status,
            expected_status,
            (suite / "coverage.stderr").read_text(errors="replace"),
        )
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_no_live_group(
            worker_pgid
        )
        return suite, before

    def test_imported_qemu_wrapper_leaves_foreground_operation(self) -> None:
        suite, before = self.run_parent_only_sigint(
            "qemu-baseline",
            self.baseline,
            expected_status=0,
            expect_survivors=True,
        )
        self.assertGreaterEqual(len(before), 2)
        self.assertNotIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_status_only_qemu_wrapper_still_leaves_foreground_operation(
        self,
    ) -> None:
        suite, before = self.run_parent_only_sigint(
            "qemu-status-only",
            self.status_candidate,
            expected_status=130,
            expect_survivors=True,
        )
        self.assertGreaterEqual(len(before), 2)
        self.assertIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_group_candidate_stops_qemu_wrapper_operation(self) -> None:
        suite, before = self.run_parent_only_sigint(
            "qemu-group-owned",
            self.group_candidate,
            expected_status=130,
            expect_survivors=False,
        )
        self.assertGreaterEqual(len(before), 2)
        self.assertIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_group_candidate_qemu_unsignaled_run_succeeds(self) -> None:
        suite = self.make_suite("qemu-success", self.group_candidate)
        process, stdout, stderr = self.start_coverage(suite)
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_file(
            suite / "qemu-worker.ready",
            process,
        )
        worker_pid = int(
            (suite / "qemu-worker.pid").read_text(encoding="ascii")
        )
        worker_pgid = os.getpgid(worker_pid)
        self.addCleanup(
            process_group.MmdebstrapCoverageProcessGroupTest.terminate_group,
            worker_pgid,
        )
        process_group.MmdebstrapCoverageProcessGroupTest.release_test(suite)
        status = process.wait(timeout=10)
        stdout.close()
        stderr.close()

        self.assertEqual(
            status,
            0,
            (suite / "coverage.stderr").read_text(errors="replace"),
        )
        self.assertTrue((suite / "qemu-later").exists())
        process_group.MmdebstrapCoverageProcessGroupTest.wait_for_no_live_group(
            worker_pgid
        )
        self.assertIn(
            "result: SUCCESS",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )


if __name__ == "__main__":
    unittest.main()
