from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/make_mirror.sh"
PARENT_PATCH = (
    ROOT
    / "investigations"
    / "make-mirror-signal-exit"
    / "0001-preserve-signal-exit-status.patch"
)
WORKER_PATCH = (
    ROOT
    / "investigations"
    / "make-mirror-update-cache-subshell"
    / "0001-confine-update-cache-signal-cleanup.patch"
)


class MakeMirrorForegroundSignalTopologiesTest(unittest.TestCase):
    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def wait_for_files(
        paths: list[pathlib.Path],
        process: subprocess.Popen[str],
        timeout: float = 3.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if all(path.exists() for path in paths):
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"owner exited before ready: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        missing = [str(path) for path in paths if not path.exists()]
        raise AssertionError(f"timed out waiting for {missing}")

    def write_helper(self, runtime: pathlib.Path) -> pathlib.Path:
        helper = runtime / "foreground.sh"
        helper.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            "printf '%s\\n' \"$$\" >\"$runtime/child.pid\"\n"
            "printf 'ready\\n' >\"$runtime/child-ready\"\n"
            "while [ ! -e \"$runtime/release-child\" ]; do\n"
            "  sleep 0.02\n"
            "done\n"
            "printf 'after\\n' >\"$runtime/child-after\"\n",
            encoding="utf-8",
        )
        helper.chmod(0o755)
        return helper

    def write_worker(
        self,
        runtime: pathlib.Path,
        *,
        own_foreground_child: bool,
    ) -> pathlib.Path:
        helper = self.write_helper(runtime)
        cleanup_child = (
            '  if [ -n "${WORKER_CHILD_PID:-}" ]; then\n'
            '    if kill -0 "$WORKER_CHILD_PID" 2>/dev/null; then\n'
            '      kill "$WORKER_CHILD_PID" 2>/dev/null || :\n'
            "    fi\n"
            '    wait "$WORKER_CHILD_PID" 2>/dev/null || :\n'
            "    WORKER_CHILD_PID=\n"
            "  fi\n"
            if own_foreground_child
            else "  :\n"
        )
        launch = (
            "sleep 60 &\n"
            "WORKER_CHILD_PID=$!\n"
            "printf '%s\\n' \"$WORKER_CHILD_PID\" >\"$runtime/child.pid\"\n"
            "printf 'ready\\n' >\"$runtime/child-ready\"\n"
            'wait "$WORKER_CHILD_PID"\n'
            "WORKER_CHILD_PID=\n"
            if own_foreground_child
            else f"{self.quote(str(helper))}\n"
        )
        worker = runtime / "worker.sh"
        worker.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            "WORKER_CHILD_PID=\n"
            "cleanupapt() {\n"
            "  printf 'worker-cleanup\\n' >>\"$runtime/worker-cleanup.log\"\n"
            "}\n"
            "cleanup_worker_child() {\n"
            + cleanup_child
            + "}\n"
            "update_cache_exit_cleanup() {\n"
            "  status=$?\n"
            "  trap - EXIT INT QUIT TERM\n"
            "  cleanup_worker_child\n"
            "  cleanupapt || :\n"
            "  exit \"$status\"\n"
            "}\n"
            "update_cache_signal_exit() {\n"
            "  status=$1\n"
            "  trap - EXIT INT QUIT TERM\n"
            "  cleanup_worker_child\n"
            "  cleanupapt || :\n"
            "  exit \"$status\"\n"
            "}\n"
            "trap 'update_cache_exit_cleanup' EXIT\n"
            "trap 'update_cache_signal_exit 130' INT\n"
            "trap 'update_cache_signal_exit 131' QUIT\n"
            "trap 'update_cache_signal_exit 143' TERM\n"
            "printf '%s\\n' \"$$\" >\"$runtime/worker.pid\"\n"
            + launch
            + "printf 'worker-after\\n' >\"$runtime/worker-after\"\n"
            "cleanupapt\n"
            "trap - EXIT INT QUIT TERM\n",
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def write_owner(
        self,
        runtime: pathlib.Path,
        *,
        own_worker: bool,
        own_foreground_child: bool,
    ) -> pathlib.Path:
        worker = self.write_worker(
            runtime, own_foreground_child=own_foreground_child
        )
        cleanup_worker = (
            '  if [ -n "${PIPELINE_WORKER_PID:-}" ]; then\n'
            '    if kill -0 "$PIPELINE_WORKER_PID" 2>/dev/null; then\n'
            '      kill "$PIPELINE_WORKER_PID" 2>/dev/null || :\n'
            "    fi\n"
            '    wait "$PIPELINE_WORKER_PID" 2>/dev/null || :\n'
            "    PIPELINE_WORKER_PID=\n"
            "  fi\n"
            if own_worker
            else "  :\n"
        )
        launch_worker = (
            'printf "input\\n" | "$worker" &\n'
            "PIPELINE_WORKER_PID=$!\n"
            'wait "$PIPELINE_WORKER_PID"\n'
            "PIPELINE_WORKER_PID=\n"
            if own_worker
            else 'printf "input\\n" | "$worker"\n'
        )
        owner = runtime / "owner.sh"
        owner.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"worker={self.quote(str(worker))}\n"
            "PIPELINE_WORKER_PID=\n"
            "sleep 60 &\n"
            "PROXYPID=$!\n"
            "printf '%s\\n' \"$PROXYPID\" >\"$runtime/proxy.pid\"\n"
            "cleanup_owner() {\n"
            "  printf 'owner-cleanup\\n' >>\"$runtime/owner-cleanup.log\"\n"
            + cleanup_worker
            + '  if kill -0 "$PROXYPID" 2>/dev/null; then\n'
            '    kill "$PROXYPID" 2>/dev/null || :\n'
            "  fi\n"
            '  wait "$PROXYPID" 2>/dev/null || :\n'
            "}\n"
            "signal_exit() {\n"
            "  status=$1\n"
            "  trap - EXIT INT QUIT TERM\n"
            "  cleanup_owner\n"
            "  exit \"$status\"\n"
            "}\n"
            "trap 'cleanup_owner' EXIT\n"
            "trap 'signal_exit 130' INT\n"
            "trap 'signal_exit 131' QUIT\n"
            "trap 'signal_exit 143' TERM\n"
            "printf '%s\\n' \"$$\" >\"$runtime/owner.pid\"\n"
            + launch_worker
            + "printf 'owner-after\\n' >\"$runtime/owner-after\"\n",
            encoding="utf-8",
        )
        owner.chmod(0o755)
        return owner

    def start_case(
        self,
        root: pathlib.Path,
        label: str,
        *,
        own_worker: bool = False,
        own_foreground_child: bool = False,
    ) -> tuple[subprocess.Popen[str], pathlib.Path, dict[str, int]]:
        runtime = root / label
        runtime.mkdir()
        owner = self.write_owner(
            runtime,
            own_worker=own_worker,
            own_foreground_child=own_foreground_child,
        )
        process = subprocess.Popen(
            ["/bin/sh", str(owner)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        def cleanup_process() -> None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)

        self.addCleanup(cleanup_process)
        self.wait_for_files(
            [
                runtime / "owner.pid",
                runtime / "worker.pid",
                runtime / "child.pid",
                runtime / "child-ready",
                runtime / "proxy.pid",
            ],
            process,
        )
        pids = {
            name: int((runtime / f"{name}.pid").read_text().strip())
            for name in ("owner", "worker", "child", "proxy")
        }
        return process, runtime, pids

    def assert_clean_finish(
        self,
        process: subprocess.Popen[str],
        runtime: pathlib.Path,
        pids: dict[str, int],
        *,
        expected_status: int = 143,
        expect_child_after: bool,
        expect_worker_after: bool,
        expect_owner_after: bool = False,
        timeout: float = 2.0,
    ) -> None:
        stdout, stderr = process.communicate(timeout=timeout)
        self.assertEqual(process.returncode, expected_status, stdout + stderr)
        self.assertEqual(stdout, "")
        self.assertEqual((runtime / "child-after").exists(), expect_child_after)
        self.assertEqual((runtime / "worker-after").exists(), expect_worker_after)
        self.assertEqual((runtime / "owner-after").exists(), expect_owner_after)
        self.assertEqual(
            (runtime / "worker-cleanup.log").read_text().splitlines(),
            ["worker-cleanup"],
        )
        self.assertEqual(
            (runtime / "owner-cleanup.log").read_text().splitlines(),
            ["owner-cleanup"],
        )
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and self.process_exists(pids["proxy"]):
            time.sleep(0.01)
        self.assertFalse(self.process_exists(pids["proxy"]))

    def test_source_keeps_foreground_commands_and_synchronous_worker_pipeline(
        self,
    ) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        update_start = source.index("update_cache() (\n")
        update_end = source.index("\n)\n", update_start)
        update_block = source[update_start:update_end]
        self.assertIn(
            'APT_CONFIG="$rootdir/etc/apt/apt.conf" apt-get update --error-on=any',
            update_block,
        )
        self.assertIn(
            'APT_CONFIG="$rootdir/etc/apt/apt.conf" apt-get --yes install $pkgs',
            update_block,
        )
        self.assertGreaterEqual(source.count("| update_cache"), 2)
        self.assertNotIn("WORKER_CHILD_PID", WORKER_PATCH.read_text(encoding="utf-8"))
        self.assertNotIn("PIPELINE_WORKER_PID", PARENT_PATCH.read_text(encoding="utf-8"))

    def test_current_worker_signal_waits_for_foreground_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="foreground-worker-current-") as td:
            root = pathlib.Path(td)
            process, runtime, pids = self.start_case(root, "case")
            os.kill(pids["worker"], signal.SIGTERM)
            time.sleep(0.1)
            self.assertIsNone(process.poll())
            self.assertTrue(self.process_exists(pids["child"]))
            (runtime / "release-child").touch()
            self.assert_clean_finish(
                process,
                runtime,
                pids,
                expect_child_after=True,
                expect_worker_after=False,
            )

    def test_current_owner_signal_allows_worker_later_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="foreground-owner-current-") as td:
            root = pathlib.Path(td)
            process, runtime, pids = self.start_case(root, "case")
            os.kill(pids["owner"], signal.SIGTERM)
            time.sleep(0.1)
            self.assertIsNone(process.poll())
            self.assertTrue(self.process_exists(pids["child"]))
            (runtime / "release-child").touch()
            self.assert_clean_finish(
                process,
                runtime,
                pids,
                expect_child_after=True,
                expect_worker_after=True,
            )

    def test_process_group_delivery_is_prompt_without_source_ownership(self) -> None:
        with tempfile.TemporaryDirectory(prefix="foreground-group-current-") as td:
            root = pathlib.Path(td)
            process, runtime, pids = self.start_case(root, "case")
            os.killpg(process.pid, signal.SIGTERM)
            self.assert_clean_finish(
                process,
                runtime,
                pids,
                expect_child_after=False,
                expect_worker_after=False,
                timeout=1.0,
            )

    def test_worker_child_ownership_makes_worker_signal_prompt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="foreground-worker-owned-") as td:
            root = pathlib.Path(td)
            process, runtime, pids = self.start_case(
                root, "case", own_foreground_child=True
            )
            os.kill(pids["worker"], signal.SIGTERM)
            self.assert_clean_finish(
                process,
                runtime,
                pids,
                expect_child_after=False,
                expect_worker_after=False,
                timeout=1.0,
            )

    def test_composed_parent_and_worker_ownership_makes_owner_signal_prompt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="foreground-composed-owned-") as td:
            root = pathlib.Path(td)
            process, runtime, pids = self.start_case(
                root,
                "case",
                own_worker=True,
                own_foreground_child=True,
            )
            os.kill(pids["owner"], signal.SIGTERM)
            self.assert_clean_finish(
                process,
                runtime,
                pids,
                expect_child_after=False,
                expect_worker_after=False,
                timeout=1.0,
            )


if __name__ == "__main__":
    unittest.main()
