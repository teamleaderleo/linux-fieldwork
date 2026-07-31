from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(
    shutil.which("setsid") and pathlib.Path("/bin/kill").exists(),
    "setsid or /bin/kill unavailable",
)
class MakeMirrorFallbackChildOwnershipTest(unittest.TestCase):
    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    @staticmethod
    def exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def wait_path(
        path: pathlib.Path,
        process: subprocess.Popen[str],
        timeout: float = 3.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"worker exited early: {process.returncode}: {stdout}{stderr}"
                )
            time.sleep(0.01)
        raise AssertionError(f"timed out waiting for {path}")

    def write_attempt(
        self,
        runtime: pathlib.Path,
        name: str,
        status: int,
        *,
        hold: bool = False,
    ) -> pathlib.Path:
        path = runtime / f"{name}.sh"
        body = (
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f'printf called >"$runtime/{name}.called"\n'
            f'printf \'%s\\n\' "$$" >"$runtime/{name}.pid"\n'
        )
        if hold:
            body += (
                f'printf ready >"$runtime/{name}.ready"\n'
                "exec sleep 60\n"
            )
        else:
            body += f"exit {status}\n"
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def write_worker(
        self,
        runtime: pathlib.Path,
        first: pathlib.Path,
        second: pathlib.Path,
        *,
        cleanup_status: int = 0,
        name: str = "worker.sh",
        mutate_errexit: bool = False,
    ) -> pathlib.Path:
        if mutate_errexit:
            wait_block = (
                "  set +e\n"
                '  wait "$ACTIVE_PID"\n'
                "  child_status=$?\n"
                "  set -e\n"
            )
        else:
            wait_block = (
                "  child_status=0\n"
                '  wait "$ACTIVE_PID" || child_status=$?\n'
            )

        worker = runtime / name
        worker.write_text(
            "#!/bin/sh\n"
            "set -u\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"first={self.quote(str(first))}\n"
            f"second={self.quote(str(second))}\n"
            f"cleanup_status={cleanup_status}\n"
            "ACTIVE_PID=\n"
            "stop_active() {\n"
            '  if [ -n "${ACTIVE_PID:-}" ]; then\n'
            '    /bin/kill -TERM -- "-$ACTIVE_PID" 2>/dev/null || :\n'
            '    wait "$ACTIVE_PID" 2>/dev/null || :\n'
            "    ACTIVE_PID=\n"
            "  fi\n"
            "}\n"
            "finish() {\n"
            "  status=$?\n"
            "  trap - EXIT INT QUIT TERM\n"
            "  stop_active\n"
            '  printf cleanup >>"$runtime/cleanup.log"\n'
            '  if [ "$status" -ne 0 ]; then\n'
            '    exit "$status"\n'
            "  fi\n"
            '  exit "$cleanup_status"\n'
            "}\n"
            "on_signal() {\n"
            "  signal_status=$1\n"
            "  trap - EXIT INT QUIT TERM\n"
            "  stop_active\n"
            '  printf cleanup >>"$runtime/cleanup.log"\n'
            '  exit "$signal_status"\n'
            "}\n"
            "trap finish EXIT\n"
            "trap 'on_signal 130' INT\n"
            "trap 'on_signal 131' QUIT\n"
            "trap 'on_signal 143' TERM\n"
            "run_child() {\n"
            "  command=$1\n"
            '  setsid /bin/sh "$command" &\n'
            "  ACTIVE_PID=$!\n"
            '  printf \'%s\\n\' "$ACTIVE_PID" >"$runtime/active.pid"\n'
            + wait_block
            + "  ACTIVE_PID=\n"
            '  return "$child_status"\n'
            "}\n"
            "set +e\n"
            'run_child "$first" || run_child "$second"\n'
            "result=$?\n"
            "set -e\n"
            'printf \'%s\\n\' "$result" >"$runtime/result.status"\n'
            'exit "$result"\n',
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def run_case(
        self,
        first_status: int,
        second_status: int,
        *,
        cleanup_status: int = 0,
        mutate_errexit: bool = False,
    ) -> tuple[
        subprocess.CompletedProcess[str],
        pathlib.Path,
        tempfile.TemporaryDirectory[str],
    ]:
        temporary = tempfile.TemporaryDirectory(prefix="fallback-owner-")
        runtime = pathlib.Path(temporary.name)
        first = self.write_attempt(runtime, "first", first_status)
        second = self.write_attempt(runtime, "second", second_status)
        worker = self.write_worker(
            runtime,
            first,
            second,
            cleanup_status=cleanup_status,
            mutate_errexit=mutate_errexit,
        )
        result = subprocess.run(
            ["/bin/sh", str(worker)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        return result, runtime, temporary

    def test_success_omits_fallback(self) -> None:
        result, runtime, temporary = self.run_case(0, 7)
        try:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((runtime / "first.called").exists())
            self.assertFalse((runtime / "second.called").exists())
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")
        finally:
            temporary.cleanup()

    def test_ordinary_failure_runs_fallback_and_second_status_wins(self) -> None:
        result, runtime, temporary = self.run_case(5, 7)
        try:
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertTrue((runtime / "first.called").exists())
            self.assertTrue((runtime / "second.called").exists())
            self.assertEqual((runtime / "result.status").read_text(), "7\n")
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")
        finally:
            temporary.cleanup()

    def test_fallback_success_returns_success(self) -> None:
        result, runtime, temporary = self.run_case(5, 0)
        try:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((runtime / "second.called").exists())
            self.assertEqual((runtime / "result.status").read_text(), "0\n")
        finally:
            temporary.cleanup()

    def test_ordinary_failure_beats_cleanup_failure(self) -> None:
        result, runtime, temporary = self.run_case(
            5,
            7,
            cleanup_status=74,
        )
        try:
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")
        finally:
            temporary.cleanup()

    def test_cleanup_failure_after_success_is_authoritative(self) -> None:
        result, runtime, temporary = self.run_case(
            0,
            9,
            cleanup_status=74,
        )
        try:
            self.assertEqual(result.returncode, 74, result.stderr)
            self.assertFalse((runtime / "second.called").exists())
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")
        finally:
            temporary.cleanup()

    def test_helper_must_not_toggle_errexit_inside_fallback_chain(self) -> None:
        result, runtime, temporary = self.run_case(
            5,
            7,
            mutate_errexit=True,
        )
        try:
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertTrue((runtime / "first.called").exists())
            self.assertTrue((runtime / "second.called").exists())
            self.assertFalse((runtime / "result.status").exists())
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")
        finally:
            temporary.cleanup()

    def test_cancelled_first_attempt_omits_fallback_and_reruns_cleanly(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="fallback-term-") as temporary:
            runtime = pathlib.Path(temporary)
            first = self.write_attempt(runtime, "first", 0, hold=True)
            second = self.write_attempt(runtime, "second", 0)
            worker = self.write_worker(
                runtime,
                first,
                second,
                cleanup_status=74,
            )
            process = subprocess.Popen(
                ["/bin/sh", str(worker)],
                cwd=runtime,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            self.wait_path(runtime / "first.ready", process)
            first_pid = int((runtime / "first.pid").read_text())
            os.kill(process.pid, signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=2)
            self.assertEqual(process.returncode, 143, stdout + stderr)
            self.assertFalse((runtime / "second.called").exists())
            self.assertFalse((runtime / "result.status").exists())
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")

            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and self.exists(first_pid):
                time.sleep(0.01)
            self.assertFalse(self.exists(first_pid))

            for path in runtime.glob("*.called"):
                path.unlink()
            (runtime / "cleanup.log").unlink()
            first_ok = self.write_attempt(runtime, "first-rerun", 0)
            second_bad = self.write_attempt(runtime, "second-rerun", 9)
            rerun_worker = self.write_worker(
                runtime,
                first_ok,
                second_bad,
                name="rerun.sh",
            )
            rerun = subprocess.run(
                ["/bin/sh", str(rerun_worker)],
                cwd=runtime,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=5,
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertTrue((runtime / "first-rerun.called").exists())
            self.assertFalse((runtime / "second-rerun.called").exists())
            self.assertEqual((runtime / "cleanup.log").read_text(), "cleanup")


if __name__ == "__main__":
    unittest.main()
