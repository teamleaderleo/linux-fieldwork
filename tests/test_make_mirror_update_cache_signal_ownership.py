from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


class MakeMirrorUpdateCacheSignalOwnershipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/make_mirror.sh"
        cls.patch = cls.repo / (
            "investigations/make-mirror-update-cache-subshell/"
            "0001-confine-update-cache-signal-cleanup.patch"
        )

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate-tree"
        destination = tree / "upstream/mmdebstrap/make_mirror.sh"
        destination.parent.mkdir(parents=True)
        shutil.copy2(self.source, destination)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
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

    @staticmethod
    def extract_nested_function(source: str, name: str) -> str:
        start = source.index(f"  {name}() {{\n")
        end = source.index("\n  }\n", start) + len("\n  }\n")
        return source[start:end]

    def candidate_blocks(self, source: str) -> tuple[str, str]:
        functions = "\n".join(
            self.extract_nested_function(source, name)
            for name in ("update_cache_exit_cleanup", "update_cache_signal_exit")
        )
        traps = (
            "  trap 'update_cache_exit_cleanup' EXIT\n"
            "  trap 'update_cache_signal_exit 130' INT\n"
            "  trap 'update_cache_signal_exit 131' QUIT\n"
            "  trap 'update_cache_signal_exit 143' TERM\n"
        )
        for line in traps.splitlines():
            if line not in source:
                raise AssertionError(f"candidate trap missing: {line}")
        return functions, traps

    @staticmethod
    def baseline_blocks(source: str) -> tuple[str, str]:
        trap = '  trap \'kill "$PROXYPID" || :;cleanupapt\' EXIT INT TERM\n'
        if source.count(trap) != 1:
            raise AssertionError("baseline update_cache trap changed")
        return "", trap

    @staticmethod
    def shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def write_scripts(
        self,
        runtime: pathlib.Path,
        blocks: tuple[str, str],
        *,
        mode: str,
        cleanup_failure: bool = False,
    ) -> pathlib.Path:
        functions, traps = blocks
        runtime.mkdir(parents=True, exist_ok=True)
        worker = runtime / "worker.sh"
        worker.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.shell_quote(str(runtime))}\n"
            f"mode={self.shell_quote(mode)}\n"
            f"cleanup_failure={'yes' if cleanup_failure else 'no'}\n"
            "cleanupapt() {\n"
            "  printf 'subshell-cleanup\\n' >>\"$runtime/cleanup.log\"\n"
            "  rm -f \"$runtime/apt-state\"\n"
            "  if [ \"$cleanup_failure\" = yes ]; then return 74; fi\n"
            "}\n"
            + functions
            + "\n"
            + traps
            + "printf '%s\\n' \"$$\" >\"$runtime/worker.pid\"\n"
            "touch \"$runtime/apt-state\"\n"
            "printf 'ready\\n' >\"$runtime/ready\"\n"
            "case \"$mode\" in\n"
            "  signal) sleep 0.5 ;;\n"
            "  failure) exit 42 ;;\n"
            "  success) : ;;\n"
            "  *) exit 98 ;;\n"
            "esac\n"
            "printf 'worker-after\\n' >\"$runtime/worker-after\"\n"
            "cleanupapt\n"
            "trap - EXIT INT QUIT TERM\n",
            encoding="utf-8",
        )
        worker.chmod(0o755)

        owner = runtime / "owner.sh"
        owner.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.shell_quote(str(runtime))}\n"
            f"worker={self.shell_quote(str(worker))}\n"
            "sleep 60 &\n"
            "PROXYPID=$!\n"
            "export PROXYPID\n"
            "printf '%s\\n' \"$PROXYPID\" >\"$runtime/proxy.pid\"\n"
            "cleanup_owner() {\n"
            "  printf 'owner-cleanup\\n' >>\"$runtime/owner-cleanup.log\"\n"
            "  if kill -0 \"$PROXYPID\" 2>/dev/null; then\n"
            "    kill \"$PROXYPID\" 2>/dev/null || :\n"
            "  fi\n"
            "  wait \"$PROXYPID\" 2>/dev/null || :\n"
            "}\n"
            "trap cleanup_owner EXIT\n"
            "printf 'input\\n' | /bin/sh \"$worker\"\n"
            "printf 'owner-after\\n' >\"$runtime/owner-after\"\n",
            encoding="utf-8",
        )
        owner.chmod(0o755)
        return owner

    @staticmethod
    def wait_for_file(path: pathlib.Path, process: subprocess.Popen[str]) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"owner exited before {path.name}: {process.returncode}\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        raise AssertionError(f"timed out waiting for {path}")

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def run_owner(
        self,
        owner: pathlib.Path,
        *,
        signaled: bool,
    ) -> tuple[subprocess.Popen[str], pathlib.Path, int]:
        runtime = owner.parent
        process = subprocess.Popen(
            ["/bin/sh", str(owner)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.wait_for_file(runtime / "ready", process)
        worker_pid = int((runtime / "worker.pid").read_text().strip())
        proxy_pid = int((runtime / "proxy.pid").read_text().strip())
        if signaled:
            os.kill(worker_pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and self.process_exists(proxy_pid):
            time.sleep(0.01)
        self.assertFalse(self.process_exists(proxy_pid), f"proxy {proxy_pid} survived")
        return process, runtime, worker_pid

    def test_baseline_subshell_term_resumes_and_kills_parent_proxy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="update-cache-baseline-") as tmp:
            root = pathlib.Path(tmp)
            source = self.source.read_text(encoding="utf-8")
            owner = self.write_scripts(
                root, self.baseline_blocks(source), mode="signal"
            )
            process, runtime, _worker_pid = self.run_owner(owner, signaled=True)
            self.assertEqual(process.returncode, 0)
            self.assertTrue((runtime / "worker-after").exists())
            self.assertTrue((runtime / "owner-after").exists())
            self.assertFalse((runtime / "apt-state").exists())
            self.assertEqual(
                (runtime / "cleanup.log").read_text().splitlines(),
                ["subshell-cleanup", "subshell-cleanup"],
            )
            self.assertEqual(
                (runtime / "owner-cleanup.log").read_text().splitlines(),
                ["owner-cleanup"],
            )

    def test_candidate_term_propagates_and_rerun_succeeds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="update-cache-candidate-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            blocks = self.candidate_blocks(candidate)
            runtime = root / "runtime"
            owner = self.write_scripts(runtime, blocks, mode="signal")
            process, runtime, _worker_pid = self.run_owner(owner, signaled=True)
            self.assertEqual(process.returncode, 143)
            self.assertFalse((runtime / "worker-after").exists())
            self.assertFalse((runtime / "owner-after").exists())
            self.assertFalse((runtime / "apt-state").exists())
            self.assertEqual(
                (runtime / "cleanup.log").read_text().splitlines(),
                ["subshell-cleanup"],
            )
            self.assertEqual(
                (runtime / "owner-cleanup.log").read_text().splitlines(),
                ["owner-cleanup"],
            )

            for name in (
                "cleanup.log",
                "owner-cleanup.log",
                "ready",
                "worker.pid",
                "proxy.pid",
            ):
                (runtime / name).unlink(missing_ok=True)
            owner = self.write_scripts(runtime, blocks, mode="success")
            rerun, runtime, _worker_pid = self.run_owner(owner, signaled=False)
            self.assertEqual(rerun.returncode, 0)
            self.assertTrue((runtime / "worker-after").exists())
            self.assertTrue((runtime / "owner-after").exists())
            self.assertFalse((runtime / "apt-state").exists())
            self.assertEqual(
                (runtime / "cleanup.log").read_text().splitlines(),
                ["subshell-cleanup"],
            )
            self.assertEqual(
                (runtime / "owner-cleanup.log").read_text().splitlines(),
                ["owner-cleanup"],
            )

    def test_candidate_preserves_ordinary_failure_and_signal_over_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="update-cache-precedence-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            blocks = self.candidate_blocks(candidate)

            failure_owner = self.write_scripts(
                root / "failure", blocks, mode="failure", cleanup_failure=True
            )
            failure, failure_runtime, _worker_pid = self.run_owner(
                failure_owner, signaled=False
            )
            self.assertEqual(failure.returncode, 42)
            self.assertFalse((failure_runtime / "worker-after").exists())
            self.assertEqual(
                (failure_runtime / "cleanup.log").read_text().splitlines(),
                ["subshell-cleanup"],
            )

            signal_owner = self.write_scripts(
                root / "signal", blocks, mode="signal", cleanup_failure=True
            )
            signaled, signal_runtime, _worker_pid = self.run_owner(
                signal_owner, signaled=True
            )
            self.assertEqual(signaled.returncode, 143)
            self.assertFalse((signal_runtime / "worker-after").exists())
            self.assertEqual(
                (signal_runtime / "cleanup.log").read_text().splitlines(),
                ["subshell-cleanup"],
            )

    def test_candidate_source_confines_cleanup_to_subshell_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="update-cache-source-") as tmp:
            candidate = self.prepare_candidate(pathlib.Path(tmp))
            self.assertNotIn(
                'trap \'kill "$PROXYPID" || :;cleanupapt\' EXIT INT TERM',
                candidate,
            )
            self.assertIn("update_cache_exit_cleanup() {", candidate)
            self.assertIn("update_cache_signal_exit() {", candidate)
            self.assertIn("trap 'update_cache_exit_cleanup' EXIT", candidate)
            self.assertIn("trap 'update_cache_signal_exit 130' INT", candidate)
            self.assertIn("trap 'update_cache_signal_exit 131' QUIT", candidate)
            self.assertIn("trap 'update_cache_signal_exit 143' TERM", candidate)
            self.assertIn('trap "-" EXIT INT QUIT TERM', candidate)
            update_start = candidate.index("update_cache() (\n")
            update_end = candidate.index("\n)\n", update_start)
            update_block = candidate[update_start:update_end]
            self.assertNotIn('kill "$PROXYPID"', update_block)


if __name__ == "__main__":
    unittest.main()
