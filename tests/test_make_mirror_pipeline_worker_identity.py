from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest


class MakeMirrorPipelineWorkerIdentityTest(unittest.TestCase):
    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def write_worker(self, runtime: pathlib.Path) -> pathlib.Path:
        worker = runtime / "worker.sh"
        worker.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "runtime=$1\n"
            "status=$2\n"
            "printf '%s\\n' \"$$\" >\"$runtime/worker.pid\"\n"
            "cat >\"$runtime/input\"\n"
            "exit \"$status\"\n",
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def write_owner(
        self,
        runtime: pathlib.Path,
        *,
        producer: str,
        status: int,
    ) -> pathlib.Path:
        worker = self.write_worker(runtime)
        if producer == "line":
            pipeline = (
                'printf "alpha\\n" | "$worker" "$runtime" "$worker_status" &\n'
            )
        elif producer == "heredoc":
            pipeline = (
                'cat <<END | "$worker" "$runtime" "$worker_status" &\n'
                "alpha\n"
                "beta\n"
                "END\n"
            )
        else:
            raise ValueError(producer)
        owner = runtime / "owner.sh"
        owner.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"worker={self.quote(str(worker))}\n"
            f"worker_status={status}\n"
            + pipeline
            + "WORKERPID=$!\n"
            "printf '%s\\n' \"$WORKERPID\" >\"$runtime/tracked.pid\"\n"
            "result=0\n"
            'wait "$WORKERPID" || result=$?\n'
            "printf '%s\\n' \"$result\" >\"$runtime/status\"\n",
            encoding="utf-8",
        )
        owner.chmod(0o755)
        return owner

    def exercise(self, producer: str, expected_input: str) -> None:
        with tempfile.TemporaryDirectory(prefix=f"pipeline-{producer}-") as td:
            runtime = pathlib.Path(td)
            owner = self.write_owner(runtime, producer=producer, status=7)
            completed = subprocess.run(
                ["/bin/sh", str(owner)],
                cwd=runtime,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=5,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "")
            self.assertEqual(completed.stderr, "")
            self.assertEqual(
                (runtime / "tracked.pid").read_text(),
                (runtime / "worker.pid").read_text(),
            )
            self.assertEqual((runtime / "input").read_text(), expected_input)
            self.assertEqual((runtime / "status").read_text(), "7\n")

    def test_one_line_pipeline_tracks_final_worker_and_status(self) -> None:
        self.exercise("line", "alpha\n")

    def test_heredoc_pipeline_tracks_final_worker_input_and_status(self) -> None:
        self.exercise("heredoc", "alpha\nbeta\n")


if __name__ == "__main__":
    unittest.main()
