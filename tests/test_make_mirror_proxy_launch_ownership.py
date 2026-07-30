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
PATCH = (
    ROOT
    / "investigations"
    / "make-mirror-signal-exit"
    / "0001-preserve-signal-exit-status.patch"
)


class MakeMirrorProxyLaunchOwnershipTest(unittest.TestCase):
    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate-tree"
        destination = tree / "upstream/mmdebstrap/make_mirror.sh"
        destination.parent.mkdir(parents=True)
        destination.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=tree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return destination.read_text(encoding="utf-8")

    @staticmethod
    def functions(source: str) -> str:
        start = source.index("record_signal() {\n")
        end = source.index("trap 'cleanup_owner' EXIT", start)
        functions = source[start:end]

        launch = '  "$@" &\n  PROXYPID=$!\n'
        instrumented = (
            '  "$@" &\n'
            "  launch_count=$((launch_count + 1))\n"
            '  if [ "$launch_count" -eq "$window_at" ]; then\n'
            "    printf '%s\\n' \"$!\" >\"$runtime/window-proxy.pid\"\n"
            "    printf 'window\\n' >\"$runtime/window\"\n"
            '    kill -STOP "$$"\n'
            "  fi\n"
            "  PROXYPID=$!\n"
        )
        if functions.count(launch) != 1:
            raise AssertionError("launch_proxy registration seam changed")
        functions = functions.replace(launch, instrumented)

        stop = "stop_proxy() {\n"
        if functions.count(stop) != 1:
            raise AssertionError("stop_proxy seam changed")
        functions = functions.replace(
            stop,
            "stop_proxy() {\n"
            "  printf 'stop-proxy\\n' >>\"$runtime/stop.log\"\n",
        )

        cleanup = "cleanup_owner() {\n  stop_proxy\n"
        if functions.count(cleanup) != 1:
            raise AssertionError("cleanup_owner seam changed")
        return functions.replace(
            cleanup,
            "cleanup_owner() {\n"
            "  printf 'owner-cleanup\\n' >>\"$runtime/owner.log\"\n"
            "  stop_proxy\n",
        )

    @staticmethod
    def quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def write_harness(
        self,
        root: pathlib.Path,
        label: str,
        source: str,
        launch_index: int,
        window_at: int,
    ) -> pathlib.Path:
        runtime = root / label
        runtime.mkdir()
        script = runtime / "harness.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"runtime={self.quote(str(runtime))}\n"
            f"launch_total={launch_index}\n"
            f"window_at={window_at}\n"
            "launch_count=0\n"
            "cleanup_newcachedir() {\n"
            "  printf 'cache-cleanup\\n' >>\"$runtime/cache.log\"\n"
            "  rm -f \"$runtime/cache-state\"\n"
            "}\n"
            "newcache=cache.B\n"
            "PROXYPID=\n"
            "PENDING_SIGNAL=\n"
            "CLEANUP_TMPDIR=no\n"
            'if [ "$launch_total" -eq 2 ]; then\n'
            "  CLEANUP_PROXY_CACHE=yes\n"
            "  touch \"$runtime/cache-state\"\n"
            "else\n"
            "  CLEANUP_PROXY_CACHE=no\n"
            "fi\n"
            + self.functions(source)
            + "trap 'cleanup_owner' EXIT\n"
            "install_signal_traps\n"
            'if [ "$launch_total" -eq 2 ]; then\n'
            "  launch_proxy true\n"
            "  stop_proxy\n"
            "  launch_proxy sh -c 'printf ready >\"$1\"; exec sleep 60' "
            "proxy \"$runtime/proxy-ready-2\"\n"
            "else\n"
            "  launch_proxy sh -c 'printf ready >\"$1\"; exec sleep 60' "
            "proxy \"$runtime/proxy-ready-1\"\n"
            "fi\n"
            'while [ ! -e "$runtime/proxy-ready-$launch_total" ]; do sleep 0.01; done\n'
            "printf 'after\\n' >\"$runtime/after\"\n",
            encoding="utf-8",
        )
        return script

    @staticmethod
    def exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def wait_for_window(
        self, process: subprocess.Popen[str], runtime: pathlib.Path, launch_index: int
    ) -> int:
        deadline = time.monotonic() + 5
        ready = runtime / f"proxy-ready-{launch_index}"
        while time.monotonic() < deadline:
            if (runtime / "window").exists() and ready.exists():
                break
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"owner exited before registration window: {process.returncode}: "
                    f"{stdout}{stderr}"
                )
            time.sleep(0.01)
        self.assertTrue((runtime / "window").exists())
        self.assertTrue(ready.exists())

        stopped = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            waited_pid, status = os.waitpid(
                process.pid, os.WUNTRACED | os.WNOHANG
            )
            if waited_pid == process.pid and os.WIFSTOPPED(status):
                stopped = True
                break
            if process.poll() is not None:
                break
            time.sleep(0.01)
        self.assertTrue(stopped, "owner did not stop inside registration window")
        return int((runtime / "window-proxy.pid").read_text().strip())

    def assert_logs(self, runtime: pathlib.Path, launch_index: int) -> None:
        self.assertEqual(
            (runtime / "owner.log").read_text().splitlines(), ["owner-cleanup"]
        )
        expected_stops = ["stop-proxy"] * launch_index
        self.assertEqual((runtime / "stop.log").read_text().splitlines(), expected_stops)
        cache_log = runtime / "cache.log"
        if launch_index == 1:
            self.assertFalse(cache_log.exists())
            self.assertFalse((runtime / "cache-state").exists())
        else:
            self.assertEqual(cache_log.read_text().splitlines(), ["cache-cleanup"])
            self.assertFalse((runtime / "cache-state").exists())

    def exercise_launch(self, launch_index: int) -> None:
        with tempfile.TemporaryDirectory(
            prefix=f"make-mirror-launch-{launch_index}-ownership-"
        ) as td:
            root = pathlib.Path(td)
            source = self.prepare_candidate(root)

            signaled = self.write_harness(
                root, "signaled", source, launch_index=launch_index, window_at=launch_index
            )
            process = subprocess.Popen(
                ["/bin/sh", str(signaled)],
                cwd=signaled.parent,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            proxy_pid = self.wait_for_window(process, signaled.parent, launch_index)
            os.kill(process.pid, signal.SIGTERM)
            os.kill(process.pid, signal.SIGCONT)
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 143, stdout + stderr)
            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "")
            self.assertFalse((signaled.parent / "after").exists())
            self.assert_logs(signaled.parent, launch_index)

            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and self.exists(proxy_pid):
                time.sleep(0.02)
            self.assertFalse(self.exists(proxy_pid))

            rerun = self.write_harness(
                root, "rerun", source, launch_index=launch_index, window_at=0
            )
            completed = subprocess.run(
                ["/bin/sh", str(rerun)],
                cwd=rerun.parent,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            self.assertTrue((rerun.parent / "after").exists())
            self.assert_logs(rerun.parent, launch_index)

    def test_launch_one_has_owner_cleanup_without_cache_deletion(self) -> None:
        self.exercise_launch(1)

    def test_launch_two_has_owner_and_private_cache_cleanup(self) -> None:
        self.exercise_launch(2)

    def test_source_changes_cache_ownership_only_after_first_readiness(self) -> None:
        with tempfile.TemporaryDirectory(prefix="make-mirror-ownership-order-") as td:
            source = self.prepare_candidate(pathlib.Path(td))
        initialized = source.index("CLEANUP_PROXY_CACHE=no")
        first_launch = source.index(
            'launch_proxy ./caching_proxy.py "$oldcachedir" "$newcachedir"'
        )
        owns_cache = source.index("CLEANUP_PROXY_CACHE=yes", first_launch)
        second_launch = source.index(
            'launch_proxy ./caching_proxy.py --readonly "$oldcachedir" "$newcachedir"'
        )
        self.assertLess(initialized, first_launch)
        self.assertLess(first_launch, owns_cache)
        self.assertLess(owns_cache, second_launch)


if __name__ == "__main__":
    unittest.main()
