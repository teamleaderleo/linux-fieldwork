from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


class MakeMirrorUpdateCacheCleanupFailureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repository / "upstream/mmdebstrap/make_mirror.sh"
        cls.patch = cls.repository / (
            "investigations/make-mirror-update-cache-subshell/"
            "0001-confine-update-cache-signal-cleanup.patch"
        )

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    @staticmethod
    def extract_nested_function(source: str, name: str) -> str:
        start = source.index(f"  {name}() {{\n")
        end = source.index("\n  }\n", start) + len("\n  }\n")
        return source[start:end]

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate-tree"
        destination = tree / "upstream/mmdebstrap/make_mirror.sh"
        destination.parent.mkdir(parents=True)
        shutil.copy2(self.source, destination)
        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(self.patch),
            ],
            cwd=tree,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        checked = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination.read_text(encoding="utf-8")

    def candidate_functions(self, source: str) -> str:
        return "\n".join(
            self.extract_nested_function(source, name)
            for name in (
                "update_cache_finish",
                "update_cache_exit_cleanup",
                "update_cache_signal_exit",
            )
        )

    def write_case(
        self,
        runtime: pathlib.Path,
        functions: str,
        *,
        cleanup_status: int,
    ) -> pathlib.Path:
        runtime.mkdir(parents=True)
        script = runtime / "case.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.shell_quote(str(runtime))}\n"
            f"injected_cleanup_status={cleanup_status}\n"
            "cleanupapt() {\n"
            "  printf 'cleanup\\n' >>\"$runtime/cleanup.log\"\n"
            "  rm -f \"$runtime/apt-state\"\n"
            "  return \"$injected_cleanup_status\"\n"
            "}\n"
            + functions
            + "\n"
            "trap 'update_cache_exit_cleanup' EXIT\n"
            "trap 'update_cache_signal_exit 130' INT\n"
            "trap 'update_cache_signal_exit 131' QUIT\n"
            "trap 'update_cache_signal_exit 143' TERM\n"
            "touch \"$runtime/apt-state\"\n"
            "printf 'completed\\n' >\"$runtime/work-completed\"\n"
            "update_cache_finish 0\n"
            "printf 'later\\n' >\"$runtime/later\"\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    @staticmethod
    def run_case(script: pathlib.Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/sh", str(script)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    def test_successful_work_reports_cleanup_failure_once_and_reruns(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="update-cache-cleanup-failure-"
        ) as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            functions = self.candidate_functions(candidate)

            update_start = candidate.index("update_cache() (\n")
            update_end = candidate.index("\n)\n", update_start)
            update_block = candidate[update_start:update_end]
            self.assertIn("update_cache_finish 0", update_block)
            self.assertNotIn(
                'cleanupapt\n\n  # this function is run in its own process',
                update_block,
            )

            failed_runtime = root / "cleanup-failed"
            failed = self.run_case(
                self.write_case(failed_runtime, functions, cleanup_status=74)
            )
            self.assertEqual(failed.returncode, 74, failed.stdout + failed.stderr)
            self.assertTrue((failed_runtime / "work-completed").exists())
            self.assertFalse((failed_runtime / "later").exists())
            self.assertFalse((failed_runtime / "apt-state").exists())
            self.assertEqual(
                (failed_runtime / "cleanup.log").read_text().splitlines(),
                ["cleanup"],
            )

            rerun_runtime = root / "rerun"
            rerun = self.run_case(
                self.write_case(rerun_runtime, functions, cleanup_status=0)
            )
            self.assertEqual(rerun.returncode, 0, rerun.stdout + rerun.stderr)
            self.assertTrue((rerun_runtime / "work-completed").exists())
            self.assertFalse((rerun_runtime / "later").exists())
            self.assertFalse((rerun_runtime / "apt-state").exists())
            self.assertEqual(
                (rerun_runtime / "cleanup.log").read_text().splitlines(),
                ["cleanup"],
            )


if __name__ == "__main__":
    unittest.main()
