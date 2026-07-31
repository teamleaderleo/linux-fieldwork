from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


class MakeMirrorOutputCapturePipelineOwnershipTest(unittest.TestCase):
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
    def wait_files(
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
                    f"worker exited early: {process.returncode}: {stdout}{stderr}"
                )
            time.sleep(0.01)
        missing = [str(path) for path in paths if not path.exists()]
        raise AssertionError(f"timed out waiting for {missing}")

    def write_stage(
        self,
        runtime: pathlib.Path,
        name: str,
        behavior: str,
    ) -> pathlib.Path:
        path = runtime / f"{name}.sh"
        if behavior == "producer":
            body = (
                f"printf '%s\\n' \"$$\" >\"$runtime/{name}.pid\"\n"
                "printf 'line\\n'\n"
                f"printf ready >\"$runtime/{name}.ready\"\n"
                "exec sleep 60\n"
            )
        else:
            body = (
                f"printf '%s\\n' \"$$\" >\"$runtime/{name}.pid\"\n"
                "IFS= read -r line\n"
                "printf '%s\\n' \"$line\"\n"
                f"printf ready >\"$runtime/{name}.ready\"\n"
                "exec sleep 60\n"
            )
        prefix = (
            "#!/bin/sh\n"
            "set -eu\n"
            "runtime="
            + self.quote(str(runtime))
            + "\n"
        )
        path.write_text(prefix + body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def write_worker(
        self,
        runtime: pathlib.Path,
        use_group: bool,
    ) -> pathlib.Path:
        producer = self.write_stage(runtime, "producer", "producer")
        middle = self.write_stage(runtime, "middle", "filter")
        final = self.write_stage(runtime, "final", "filter")
        capture = runtime / "capture"
        worker = runtime / "worker.sh"
        pipeline = (
            f"{self.quote(str(producer))} | "
            f"{self.quote(str(middle))} | "
            f"{self.quote(str(final))} > {self.quote(str(capture))}"
        )
        if use_group:
            launch = (
                f"setsid /bin/sh -c {self.quote(pipeline)} &\n"
                "PIPEPID=$!\n"
            )
            kill = '/bin/kill -TERM -- "-$PIPEPID" 2>/dev/null || :\n'
        else:
            launch = pipeline + " &\nPIPEPID=$!\n"
            kill = 'kill "$PIPEPID" 2>/dev/null || :\n'
        worker.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            "PIPEPID=\n"
            "cleanup() {\n"
            '  if [ -n "${PIPEPID:-}" ]; then\n'
            f"    {kill}"
            '    wait "$PIPEPID" 2>/dev/null || :\n'
            "    PIPEPID=\n"
            "  fi\n"
            '  rm -f "$runtime/capture"\n'
            "}\n"
            "on_term() {\n"
            "  trap - EXIT TERM\n"
            "  cleanup\n"
            "  exit 143\n"
            "}\n"
            "trap cleanup EXIT\n"
            "trap on_term TERM\n"
            + launch
            + 'printf \'%s\\n\' "$$" >"$runtime/worker.pid"\n'
            'wait "$PIPEPID"\n'
            "PIPEPID=\n"
            "trap - EXIT TERM\n",
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def run_cancel(
        self,
        use_group: bool,
    ) -> tuple[
        tempfile.TemporaryDirectory[str],
        pathlib.Path,
        subprocess.Popen[str],
        dict[str, int],
    ]:
        td = tempfile.TemporaryDirectory(prefix="capture-pipe-")
        runtime = pathlib.Path(td.name)
        worker = self.write_worker(runtime, use_group)
        process = subprocess.Popen(
            ["/bin/sh", str(worker)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.wait_files(
            [
                runtime / f"{name}.ready"
                for name in ("producer", "middle", "final")
            ]
            + [runtime / "worker.pid"],
            process,
        )
        pids = {
            name: int((runtime / f"{name}.pid").read_text())
            for name in ("producer", "middle", "final")
        }
        os.kill(int((runtime / "worker.pid").read_text()), signal.SIGTERM)
        return td, runtime, process, pids

    def test_final_pid_only_wait_remains_blocked_on_upstream_stages(self) -> None:
        td, runtime, process, pids = self.run_cancel(False)
        try:
            time.sleep(0.1)
            self.assertIsNone(process.poll())
            self.assertFalse(self.exists(pids["final"]))
            self.assertTrue(self.exists(pids["producer"]))
            self.assertTrue(self.exists(pids["middle"]))
            for name in ("producer", "middle"):
                os.kill(pids[name], signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=2)
            self.assertEqual(process.returncode, 143, stdout + stderr)
            self.assertFalse((runtime / "capture").exists())
        finally:
            for pid in pids.values():
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            td.cleanup()

    @unittest.skipUnless(
        shutil.which("setsid") and pathlib.Path("/bin/kill").exists(),
        "setsid or /bin/kill unavailable",
    )
    def test_isolated_pipeline_group_stops_all_stages(self) -> None:
        td, runtime, process, pids = self.run_cancel(True)
        try:
            stdout, stderr = process.communicate(timeout=2)
            self.assertEqual(process.returncode, 143, stdout + stderr)
            self.assertFalse((runtime / "capture").exists())
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and any(
                self.exists(pid) for pid in pids.values()
            ):
                time.sleep(0.01)
            self.assertFalse(any(self.exists(pid) for pid in pids.values()))
        finally:
            for pid in pids.values():
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
