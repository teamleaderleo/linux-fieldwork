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
class MakeMirrorFallbackCommandOwnershipTest(unittest.TestCase):
    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    @staticmethod
    def wait_path(path: pathlib.Path, process: subprocess.Popen[str]) -> None:
        deadline = time.monotonic() + 3
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
        hold: bool = False,
    ) -> pathlib.Path:
        path = runtime / f"{name}.sh"
        body = (
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"printf run >\"$runtime/{name}.ran\"\n"
        )
        if hold:
            body += (
                f"printf ready >\"$runtime/{name}.ready\"\n"
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
        fallback: pathlib.Path,
    ) -> pathlib.Path:
        worker = runtime / "worker.sh"
        worker.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"first={self.quote(str(first))}\n"
            f"fallback={self.quote(str(fallback))}\n"
            "ACTIVE_PID=\n"
            "cleanup_active() {\n"
            '  if [ -n "${ACTIVE_PID:-}" ]; then\n'
            '    /bin/kill -TERM -- "-$ACTIVE_PID" 2>/dev/null || :\n'
            '    wait "$ACTIVE_PID" 2>/dev/null || :\n'
            "    ACTIVE_PID=\n"
            "  fi\n"
            "}\n"
            "on_term() {\n"
            "  trap - EXIT TERM\n"
            "  cleanup_active\n"
            "  exit 143\n"
            "}\n"
            "trap cleanup_active EXIT\n"
            "trap on_term TERM\n"
            "run_owned() {\n"
            "  setsid /bin/sh \"$1\" &\n"
            "  ACTIVE_PID=$!\n"
            "  set +e\n"
            '  wait "$ACTIVE_PID"\n'
            "  status=$?\n"
            "  set -e\n"
            "  ACTIVE_PID=\n"
            '  return "$status"\n'
            "}\n"
            "status=0\n"
            'run_owned "$first" || status=$?\n'
            'if [ "$status" -ne 0 ]; then\n'
            "  status=0\n"
            '  run_owned "$fallback" || status=$?\n'
            "fi\n"
            'printf "%s\\n" "$status" >"$runtime/status"\n'
            "trap - EXIT TERM\n"
            'exit "$status"\n',
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def run_case(
        self,
        first_status: int,
        second_status: int,
    ) -> tuple[
        tempfile.TemporaryDirectory[str],
        pathlib.Path,
        subprocess.CompletedProcess[str],
    ]:
        td = tempfile.TemporaryDirectory(prefix="fallback-")
        runtime = pathlib.Path(td.name)
        first = self.write_attempt(runtime, "first", first_status)
        fallback = self.write_attempt(runtime, "fallback", second_status)
        worker = self.write_worker(runtime, first, fallback)
        completed = subprocess.run(
            ["/bin/sh", str(worker)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        return td, runtime, completed

    def test_first_success_omits_fallback(self) -> None:
        td, runtime, completed = self.run_case(0, 9)
        try:
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((runtime / "first.ran").exists())
            self.assertFalse((runtime / "fallback.ran").exists())
            self.assertEqual((runtime / "status").read_text(), "0\n")
        finally:
            td.cleanup()

    def test_first_failure_runs_fallback_and_second_status_wins(self) -> None:
        td, runtime, completed = self.run_case(7, 8)
        try:
            self.assertEqual(completed.returncode, 8)
            self.assertTrue((runtime / "first.ran").exists())
            self.assertTrue((runtime / "fallback.ran").exists())
            self.assertEqual((runtime / "status").read_text(), "8\n")
        finally:
            td.cleanup()

    def test_first_failure_then_success_returns_zero(self) -> None:
        td, runtime, completed = self.run_case(7, 0)
        try:
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((runtime / "fallback.ran").exists())
            self.assertEqual((runtime / "status").read_text(), "0\n")
        finally:
            td.cleanup()

    def test_term_during_first_attempt_omits_fallback_and_reruns(self) -> None:
        td = tempfile.TemporaryDirectory(prefix="fallback-term-")
        runtime = pathlib.Path(td.name)
        try:
            first = self.write_attempt(runtime, "first", 0, hold=True)
            fallback = self.write_attempt(runtime, "fallback", 0)
            worker = self.write_worker(runtime, first, fallback)
            process = subprocess.Popen(
                ["/bin/sh", str(worker)],
                cwd=runtime,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            self.wait_path(runtime / "first.ready", process)
            os.kill(process.pid, signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=2)
            self.assertEqual(process.returncode, 143, stdout + stderr)
            self.assertFalse((runtime / "fallback.ran").exists())

            rerun_first = self.write_attempt(runtime, "first2", 0)
            rerun_fallback = self.write_attempt(runtime, "fallback2", 0)
            rerun_worker = self.write_worker(
                runtime,
                rerun_first,
                rerun_fallback,
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
            self.assertFalse((runtime / "fallback2.ran").exists())
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
