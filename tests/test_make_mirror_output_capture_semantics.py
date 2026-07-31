from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(
    shutil.which("setsid") and shutil.which("kill"),
    "setsid or external kill unavailable",
)
class MakeMirrorOutputCaptureSemanticsTest(unittest.TestCase):
    @staticmethod
    def run_script(
        runtime: pathlib.Path,
        content: str,
    ) -> subprocess.CompletedProcess[str]:
        script = runtime / "case.sh"
        script.write_text("#!/bin/sh\nset -u\n" + content, encoding="utf-8")
        script.chmod(0o755)
        return subprocess.run(
            ["/bin/sh", str(script)],
            cwd=runtime,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )

    def test_group_capture_preserves_command_substitution_newline_semantics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="capture-output-") as td:
            runtime = pathlib.Path(td)
            result = self.run_script(
                runtime,
                "original=$(printf 'alpha\\nbeta\\n\\n' | cat | cat)\n"
                "printf '%s' \"$original\" >original\n"
                "capture=group.capture\n"
                "setsid /bin/sh -c \"printf 'alpha\\\\nbeta\\\\n\\\\n' | "
                "cat | cat\" >\"$capture\" &\n"
                "pid=$!\n"
                "status=0\n"
                "wait \"$pid\" || status=$?\n"
                "[ \"$status\" -eq 0 ]\n"
                "grouped=$(cat \"$capture\")\n"
                "rm \"$capture\"\n"
                "printf '%s' \"$grouped\" >grouped\n",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((runtime / "original").read_bytes(), b"alpha\nbeta")
            self.assertEqual(
                (runtime / "grouped").read_bytes(),
                (runtime / "original").read_bytes(),
            )

    def test_group_capture_preserves_final_stage_failure_and_discards_partial(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="capture-failure-") as td:
            runtime = pathlib.Path(td)
            result = self.run_script(
                runtime,
                "capture=group.capture\n"
                "setsid /bin/sh -c \"printf 'partial\\\\n' | cat | "
                "/bin/sh -c 'cat; exit 7'\" >\"$capture\" &\n"
                "pid=$!\n"
                "status=0\n"
                "wait \"$pid\" || status=$?\n"
                "printf '%s\\n' \"$status\" >status\n"
                "if [ \"$status\" -ne 0 ]; then\n"
                "  rm \"$capture\"\n"
                "else\n"
                "  value=$(cat \"$capture\")\n"
                "  printf '%s' \"$value\" >value\n"
                "fi\n",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((runtime / "status").read_text(), "7\n")
            self.assertFalse((runtime / "group.capture").exists())
            self.assertFalse((runtime / "value").exists())

    def test_group_capture_preserves_last_stage_pipeline_status_rule(self) -> None:
        with tempfile.TemporaryDirectory(prefix="capture-upstream-status-") as td:
            runtime = pathlib.Path(td)
            result = self.run_script(
                runtime,
                "original_status=0\n"
                "original=$(/bin/sh -c 'exit 9' | cat | cat) "
                "|| original_status=$?\n"
                "capture=group.capture\n"
                "setsid /bin/sh -c \"/bin/sh -c 'exit 9' | cat | cat\" "
                ">\"$capture\" &\n"
                "pid=$!\n"
                "group_status=0\n"
                "wait \"$pid\" || group_status=$?\n"
                "grouped=$(cat \"$capture\")\n"
                "rm \"$capture\"\n"
                "printf '%s %s\\n' \"$original_status\" \"$group_status\" "
                ">status\n"
                "printf '%s' \"$original\" >original\n"
                "printf '%s' \"$grouped\" >grouped\n",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((runtime / "status").read_text(), "0 0\n")
            self.assertEqual((runtime / "original").read_bytes(), b"")
            self.assertEqual((runtime / "grouped").read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
