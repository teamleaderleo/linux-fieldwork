from __future__ import annotations

import errno
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

from tests import test_mmdebstrap_coverage_parent_sigint as status_only


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/coverage.py"
RUN_NULL = ROOT / "upstream/mmdebstrap/run_null.sh"
STATUS_PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-coverage-process-group"
    / "0000-materialize-status-only.patch"
)
GROUP_PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-coverage-process-group"
    / "0001-own-backend-process-group.patch"
)

STATUS_ONLY_OLD = """        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            break
"""
STATUS_ONLY_NEW = """        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            print(\"interrupted by SIGINT\", file=sys.stderr)
            raise SystemExit(130)
"""


def materialize_status_only(destination: pathlib.Path) -> None:
    source = destination.read_text(encoding="utf-8")
    count = source.count(STATUS_ONLY_OLD)
    if count != 1:
        raise AssertionError(
            f"expected one imported KeyboardInterrupt block, found {count}"
        )
    destination.write_text(
        source.replace(STATUS_ONLY_OLD, STATUS_ONLY_NEW),
        encoding="utf-8",
    )


@unittest.skipUnless(
    pathlib.Path("/proc").is_dir() and hasattr(os, "killpg"),
    "requires Linux /proc and POSIX process groups",
)
class MmdebstrapCoverageProcessGroupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.work = tempfile.TemporaryDirectory(prefix="coverage-process-group-")
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
            shutil.copy2(SOURCE, destination)

        materialize_status_only(cls.status_candidate)
        cls.apply_patch(cls.group_root, GROUP_PATCH)
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
            "printf '%s\\n' \"$$\" >\"$MARKER_DIR/test.pid\"\n"
            "printf ready >\"$MARKER_DIR/test.ready\"\n"
            "IFS= read -r token <\"$MARKER_DIR/release.fifo\"\n"
            "printf later >\"$MARKER_DIR/later\"\n",
            encoding="utf-8",
        )
        (suite / "coverage.txt").write_text(
            "Test: interrupt\n",
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

        run_qemu = suite / "run_qemu.sh"
        run_qemu.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        run_qemu.chmod(0o755)

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
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{suite / 'fake-bin'}:{env['PATH']}",
                "PYTHONPATH": str(suite),
                "SOURCE_DATE_EPOCH": "0",
                "HAVE_QEMU": "no",
                "HAVE_BINFMT": "no",
                "MARKER_DIR": str(suite),
            }
        )
        return env

    @staticmethod
    def wait_for_file(path: pathlib.Path, process: subprocess.Popen[bytes]) -> None:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                raise AssertionError(
                    f"coverage exited before {path.name}: {process.returncode}"
                )
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {path}")

    @staticmethod
    def group_members(pgid: int) -> list[dict[str, int | str]]:
        members: list[dict[str, int | str]] = []
        for entry in pathlib.Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                stat_text = (entry / "stat").read_text(encoding="utf-8")
                right = stat_text.rfind(")")
                fields = stat_text[right + 2 :].split()
                state = fields[0]
                ppid = int(fields[1])
                process_group = int(fields[2])
                session = int(fields[3])
                if process_group != pgid:
                    continue
                command = (
                    (entry / "cmdline")
                    .read_bytes()
                    .replace(b"\0", b" ")
                    .decode(errors="replace")
                )
                members.append(
                    {
                        "pid": int(entry.name),
                        "state": state,
                        "ppid": ppid,
                        "pgid": process_group,
                        "sid": session,
                        "command": command,
                    }
                )
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
        return sorted(members, key=lambda item: int(item["pid"]))

    @classmethod
    def live_group_members(cls, pgid: int) -> list[dict[str, int | str]]:
        return [member for member in cls.group_members(pgid) if member["state"] != "Z"]

    @classmethod
    def wait_for_no_live_group(cls, pgid: int, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not cls.live_group_members(pgid):
                return
            time.sleep(0.02)
        raise AssertionError(
            f"live process-group members survived: {cls.live_group_members(pgid)}"
        )

    @classmethod
    def terminate_group(cls, pgid: int) -> None:
        for group_signal in (signal.SIGTERM, signal.SIGKILL):
            if not cls.live_group_members(pgid):
                return
            try:
                os.killpg(pgid, group_signal)
            except ProcessLookupError:
                return
            try:
                cls.wait_for_no_live_group(pgid, timeout=2)
                return
            except AssertionError:
                if group_signal == signal.SIGKILL:
                    raise

    @staticmethod
    def stop_coverage(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            process.wait(timeout=2)

    @staticmethod
    def release_test(suite: pathlib.Path) -> None:
        fifo = suite / "release.fifo"
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                descriptor = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
            except OSError as error:
                if error.errno != errno.ENXIO:
                    raise
                time.sleep(0.02)
                continue
            try:
                os.write(descriptor, b"go\n")
            finally:
                os.close(descriptor)
            return
        raise AssertionError("no reader remained on release FIFO")

    @staticmethod
    def wait_for_later(suite: pathlib.Path) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if (suite / "later").exists():
                return
            time.sleep(0.02)
        raise AssertionError("orphaned test did not reach later-work marker")

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
        self.addCleanup(self.stop_coverage, process)
        return process, stdout, stderr

    def run_parent_only_sigint(
        self,
        label: str,
        source: pathlib.Path,
        *,
        expected_status: int,
        expect_survivors: bool,
    ) -> tuple[pathlib.Path, int, list[dict[str, int | str]]]:
        suite = self.make_suite(label, source)
        process, stdout, stderr = self.start_coverage(suite)
        self.wait_for_file(suite / "test.ready", process)
        test_pid = int((suite / "test.pid").read_text(encoding="ascii"))
        backend_pgid = os.getpgid(test_pid)
        self.addCleanup(self.terminate_group, backend_pgid)
        before = self.group_members(backend_pgid)
        self.assertGreaterEqual(len(before), 5)

        os.kill(process.pid, signal.SIGINT)
        status = process.wait(timeout=10)
        stdout.close()
        stderr.close()
        self.assertEqual(
            status,
            expected_status,
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

        live = self.live_group_members(backend_pgid)
        if expect_survivors:
            self.assertTrue(live, before)
            self.assertFalse((suite / "later").exists())
            self.release_test(suite)
            self.wait_for_later(suite)
        else:
            self.assertFalse(live, live)
            self.assertFalse((suite / "later").exists())
        self.wait_for_no_live_group(backend_pgid)
        return suite, backend_pgid, before

    def test_imported_baseline_reports_success_and_leaves_pipeline(self) -> None:
        suite, _pgid, before = self.run_parent_only_sigint(
            "baseline-parent-only",
            self.baseline,
            expected_status=0,
            expect_survivors=True,
        )
        self.assertGreaterEqual(len(before), 5)
        self.assertNotIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_status_only_repair_reports_130_but_leaves_pipeline(self) -> None:
        suite, _pgid, before = self.run_parent_only_sigint(
            "status-parent-only",
            self.status_candidate,
            expected_status=130,
            expect_survivors=True,
        )
        self.assertGreaterEqual(len(before), 5)
        self.assertIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_group_candidate_reports_130_and_stops_pipeline(self) -> None:
        suite, _pgid, before = self.run_parent_only_sigint(
            "group-parent-only",
            self.group_candidate,
            expected_status=130,
            expect_survivors=False,
        )
        self.assertGreaterEqual(len(before), 5)
        self.assertIn(
            "interrupted by SIGINT",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_imported_foreground_group_sigint_is_already_clean(self) -> None:
        suite = self.make_suite("baseline-group-sigint", self.baseline)
        process, stdout, stderr = self.start_coverage(suite)
        self.wait_for_file(suite / "test.ready", process)
        test_pid = int((suite / "test.pid").read_text(encoding="ascii"))
        backend_pgid = os.getpgid(test_pid)
        self.addCleanup(self.terminate_group, backend_pgid)
        self.assertEqual(backend_pgid, process.pid)

        os.killpg(process.pid, signal.SIGINT)
        status = process.wait(timeout=10)
        stdout.close()
        stderr.close()
        self.assertEqual(status, 0)
        self.wait_for_no_live_group(backend_pgid)
        self.assertFalse((suite / "later").exists())

    def test_group_candidate_unsignaled_run_still_succeeds(self) -> None:
        suite = self.make_suite("group-success", self.group_candidate)
        process, stdout, stderr = self.start_coverage(suite)
        self.wait_for_file(suite / "test.ready", process)
        test_pid = int((suite / "test.pid").read_text(encoding="ascii"))
        backend_pgid = os.getpgid(test_pid)
        self.addCleanup(self.terminate_group, backend_pgid)
        self.release_test(suite)
        status = process.wait(timeout=10)
        stdout.close()
        stderr.close()

        self.assertEqual(
            status,
            0,
            (suite / "coverage.stderr").read_text(errors="replace"),
        )
        self.assertTrue((suite / "later").exists())
        self.wait_for_no_live_group(backend_pgid)
        self.assertIn(
            "result: SUCCESS",
            (suite / "coverage.stderr").read_text(errors="replace"),
        )

    def test_source_contract_distinguishes_all_three_variants(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        status_candidate = self.status_candidate.read_text(encoding="utf-8")
        group_candidate = self.group_candidate.read_text(encoding="utf-8")

        self.assertNotIn("start_new_session=True", baseline)
        self.assertNotIn("raise SystemExit(130)", baseline)
        self.assertNotIn("os.killpg", baseline)

        self.assertNotIn("start_new_session=True", status_candidate)
        self.assertIn("raise SystemExit(130)", status_candidate)
        self.assertNotIn("os.killpg", status_candidate)

        self.assertIn("import signal", group_candidate)
        self.assertIn(
            "subprocess.Popen(argv, start_new_session=True)",
            group_candidate,
        )
        self.assertIn("os.killpg(proc.pid, signal.SIGTERM)", group_candidate)
        self.assertIn("except ProcessLookupError", group_candidate)
        self.assertIn("raise SystemExit(130)", group_candidate)


if __name__ == "__main__":
    unittest.main()
