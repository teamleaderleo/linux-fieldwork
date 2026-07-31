from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


class MakeMirrorOutputCapturePipelineContractTest(unittest.TestCase):
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
    def wait_paths(
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

    def write_pipeline(
        self,
        runtime: pathlib.Path,
        body: str,
        name: str = "pipeline.sh",
    ) -> pathlib.Path:
        pipeline = runtime / name
        pipeline.write_text("#!/bin/sh\nset -u\n" + body, encoding="utf-8")
        pipeline.chmod(0o755)
        return pipeline

    def write_candidate_worker(
        self,
        runtime: pathlib.Path,
        pipeline: pathlib.Path,
        name: str = "worker.sh",
    ) -> pathlib.Path:
        worker = runtime / name
        worker.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"pipeline={self.quote(str(pipeline))}\n"
            'capture="$runtime/capture.tmp"\n'
            'result="$runtime/result"\n'
            "ACTIVE_PID=\n"
            "cleanup() {\n"
            '  if [ -n "${ACTIVE_PID:-}" ]; then\n'
            '    /bin/kill -TERM -- "-$ACTIVE_PID" 2>/dev/null || :\n'
            '    wait "$ACTIVE_PID" 2>/dev/null || :\n'
            "    ACTIVE_PID=\n"
            "  fi\n"
            '  rm -f "$capture"\n'
            "}\n"
            "on_term() {\n"
            "  trap - EXIT TERM\n"
            "  cleanup\n"
            "  exit 143\n"
            "}\n"
            "trap cleanup EXIT\n"
            "trap on_term TERM\n"
            'rm -f "$capture" "$result"\n'
            'setsid /bin/sh "$pipeline" >"$capture" &\n'
            "ACTIVE_PID=$!\n"
            'printf "%s\\n" "$$" >"$runtime/worker.pid"\n'
            'printf "%s\\n" "$ACTIVE_PID" >"$runtime/group.pid"\n'
            "set +e\n"
            'wait "$ACTIVE_PID"\n'
            "status=$?\n"
            "set -e\n"
            "ACTIVE_PID=\n"
            'printf "%s\\n" "$status" >"$runtime/pipeline.status"\n'
            'if [ "$status" -ne 0 ]; then\n'
            '  rm -f "$capture"\n'
            "  trap - EXIT TERM\n"
            '  exit "$status"\n'
            "fi\n"
            'CAPTURED=$(cat "$capture")\n'
            'rm -f "$capture"\n'
            'printf "%s" "$CAPTURED" >"$result"\n'
            "trap - EXIT TERM\n",
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def run_candidate(
        self,
        runtime: pathlib.Path,
        body: str,
        name: str = "worker.sh",
    ) -> subprocess.CompletedProcess[str]:
        pipeline = self.write_pipeline(runtime, body, name=f"{name}.pipeline")
        worker = self.write_candidate_worker(runtime, pipeline, name=name)
        return subprocess.run(
            ["/bin/sh", str(worker)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )

    def run_original(
        self,
        runtime: pathlib.Path,
        body: str,
    ) -> tuple[int, bytes]:
        pipeline = self.write_pipeline(runtime, body, name="original.pipeline")
        script = runtime / "original.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -u\n"
            f"pipeline={self.quote(str(pipeline))}\n"
            "set +e\n"
            'value=$(/bin/sh "$pipeline")\n'
            "status=$?\n"
            "set -e\n"
            'printf "%s" "$value" >original.result\n'
            'exit "$status"\n',
            encoding="utf-8",
        )
        completed = subprocess.run(
            ["/bin/sh", str(script)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        return completed.returncode, (runtime / "original.result").read_bytes()

    @unittest.skipUnless(
        shutil.which("setsid") and pathlib.Path("/bin/kill").exists(),
        "setsid or /bin/kill unavailable",
    )
    def test_exact_output_and_trailing_newline_semantics_match(self) -> None:
        payloads = (
            b"",
            b"alpha",
            b"alpha\n",
            b"alpha\nbeta",
            b"alpha\nbeta\n\n\n",
            b"\n\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory(
                prefix=f"capture-contract-{index}-"
            ) as temporary:
                runtime = pathlib.Path(temporary)
                (runtime / "payload").write_bytes(payload)
                body = 'cat "$PWD/payload" | cat | cat\n'
                original_status, original_result = self.run_original(runtime, body)
                candidate = self.run_candidate(
                    runtime,
                    body,
                    name=f"candidate-{index}.sh",
                )
                self.assertEqual(original_status, 0)
                self.assertEqual(candidate.returncode, 0, candidate.stderr)
                self.assertEqual(
                    (runtime / "result").read_bytes(),
                    original_result,
                )
                self.assertFalse((runtime / "capture.tmp").exists())

    @unittest.skipUnless(
        shutil.which("setsid") and pathlib.Path("/bin/kill").exists(),
        "setsid or /bin/kill unavailable",
    )
    def test_target_shell_upstream_failure_remains_masked_by_final_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="capture-upstream-") as temporary:
            runtime = pathlib.Path(temporary)
            body = "(printf 'packages\\n'; exit 9) | cat | cat\n"
            original_status, original_result = self.run_original(runtime, body)
            candidate = self.run_candidate(runtime, body)

            self.assertEqual(original_status, 0)
            self.assertEqual(candidate.returncode, 0, candidate.stderr)
            self.assertEqual(original_result, b"packages")
            self.assertEqual(
                (runtime / "result").read_bytes(),
                original_result,
            )
            self.assertEqual(
                (runtime / "pipeline.status").read_text().strip(),
                "0",
            )

    @unittest.skipUnless(
        shutil.which("setsid") and pathlib.Path("/bin/kill").exists(),
        "setsid or /bin/kill unavailable",
    )
    def test_final_failure_is_preserved_and_partial_capture_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="capture-final-") as temporary:
            runtime = pathlib.Path(temporary)
            body = "printf 'partial\\n' | cat | (cat; exit 7)\n"
            original_status, original_result = self.run_original(runtime, body)
            candidate = self.run_candidate(runtime, body)

            self.assertEqual(original_status, 7)
            self.assertEqual(original_result, b"partial")
            self.assertEqual(candidate.returncode, 7, candidate.stderr)
            self.assertEqual(
                (runtime / "pipeline.status").read_text().strip(),
                "7",
            )
            self.assertFalse((runtime / "result").exists())
            self.assertFalse((runtime / "capture.tmp").exists())

    def write_held_stage(
        self,
        runtime: pathlib.Path,
        name: str,
        mode: str,
    ) -> pathlib.Path:
        stage = runtime / f"{name}.sh"
        if mode == "producer":
            body = (
                "printf 'partial\\n'\n"
                f'printf "%s\\n" "$$" >"$runtime/{name}.pid"\n'
                f'printf ready >"$runtime/{name}.ready"\n'
                "exec sleep 60\n"
            )
        else:
            body = (
                "IFS= read -r line\n"
                'printf "%s\\n" "$line"\n'
                f'printf "%s\\n" "$$" >"$runtime/{name}.pid"\n'
                f'printf ready >"$runtime/{name}.ready"\n'
                "exec sleep 60\n"
            )
        stage.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            + body,
            encoding="utf-8",
        )
        stage.chmod(0o755)
        return stage

    @unittest.skipUnless(
        shutil.which("setsid") and pathlib.Path("/bin/kill").exists(),
        "setsid or /bin/kill unavailable",
    )
    def test_worker_term_stops_pipeline_group_and_discards_partial_capture(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="capture-term-") as temporary:
            runtime = pathlib.Path(temporary)
            stages = {
                "producer": self.write_held_stage(
                    runtime,
                    "producer",
                    "producer",
                ),
                "middle": self.write_held_stage(
                    runtime,
                    "middle",
                    "filter",
                ),
                "final": self.write_held_stage(
                    runtime,
                    "final",
                    "filter",
                ),
            }
            body = " | ".join(
                self.quote(str(stages[name])) for name in stages
            ) + "\n"
            pipeline = self.write_pipeline(runtime, body)
            worker = self.write_candidate_worker(runtime, pipeline)
            process = subprocess.Popen(
                ["/bin/sh", str(worker)],
                cwd=runtime,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            self.wait_paths(
                [runtime / f"{name}.ready" for name in stages]
                + [runtime / "worker.pid", runtime / "capture.tmp"],
                process,
            )
            pids = {
                name: int((runtime / f"{name}.pid").read_text())
                for name in stages
            }
            os.kill(
                int((runtime / "worker.pid").read_text()),
                signal.SIGTERM,
            )
            stdout, stderr = process.communicate(timeout=2)
            self.assertEqual(process.returncode, 143, stdout + stderr)
            self.assertFalse((runtime / "result").exists())
            self.assertFalse((runtime / "capture.tmp").exists())

            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and any(
                self.exists(pid) for pid in pids.values()
            ):
                time.sleep(0.01)
            self.assertFalse(any(self.exists(pid) for pid in pids.values()))

            rerun_body = "printf 'clean\\n' | cat | cat\n"
            rerun = self.run_candidate(
                runtime,
                rerun_body,
                name="rerun.sh",
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertEqual((runtime / "result").read_bytes(), b"clean")
            self.assertFalse((runtime / "capture.tmp").exists())


if __name__ == "__main__":
    unittest.main()
