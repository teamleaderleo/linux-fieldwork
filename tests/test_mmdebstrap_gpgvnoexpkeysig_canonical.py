from __future__ import annotations

import os
import pathlib
import signal
import shutil
import subprocess
import tempfile
import time
import unittest


EXPIRED = "[GNUPG:] EXPKEYSIG 0123456789ABCDEF expired key\n"
BAD = "[GNUPG:] BADSIG 0123456789ABCDEF bad signature\n"
REWRITTEN = EXPIRED.replace("EXPKEYSIG", "GOODSIG")


class CanonicalGpgvNoExpKeySigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-canonical/"
            "0001-canonical-lifecycle.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="gpgvnoexpkeysig-canonical-")
        cls.root = pathlib.Path(cls.work.name)
        cls.candidate_root = cls.root / "candidate"
        cls.candidate = cls.candidate_root / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.candidate.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.candidate)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(cls.patch)],
            cwd=cls.candidate_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(cls.candidate)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if syntax.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(syntax.stdout + syntax.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def setUp(self) -> None:
        self.case = pathlib.Path(tempfile.mkdtemp(prefix="case-", dir=self.root))
        self.bin = self.case / "bin"
        self.tmp = self.case / "tmp"
        self.bin.mkdir()
        self.tmp.mkdir()
        self.marker = self.case / "gpgv-invoked"
        self.gpgv_pidfile = self.case / "gpgv.pid"
        self.filter_pidfile = self.case / "filter.pid"
        self.signal_file = self.case / "signal"

    def tearDown(self) -> None:
        shutil.rmtree(self.case, ignore_errors=True)

    def environment(self, **updates: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.bin}:/usr/bin:/bin",
                "TMPDIR": str(self.tmp),
                "FAKE_GPGV_MARKER": str(self.marker),
                "FAKE_GPGV_PIDFILE": str(self.gpgv_pidfile),
                "FAKE_FILTER_PIDFILE": str(self.filter_pidfile),
                "FAKE_SIGNAL_FILE": str(self.signal_file),
                "FAKE_GPGV_STATUS": "0",
                "FAKE_GPGV_OUTPUT": EXPIRED + BAD,
                "FAKE_GPGV_STDOUT": "normal verifier stdout\n",
                "FAKE_GPGV_STDERR": "verifier stderr\n",
                "FAKE_FILTER_STATUS": "0",
            }
        )
        env.update(updates)
        return env

    def install_gpgv(self, *, blocking: bool = False) -> None:
        script = self.bin / "gpgv"
        script.write_text(
            r"""#!/usr/bin/python3
import os
import pathlib
import signal
import sys
import time

status_fd = 1
i = 1
while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == "--":
        break
    if arg == "--status-fd":
        status_fd = int(sys.argv[i + 1])
        i += 2
        continue
    if arg.startswith("--status-fd="):
        status_fd = int(arg.split("=", 1)[1])
    i += 1

pathlib.Path(os.environ["FAKE_GPGV_MARKER"]).write_text("invoked\n")
pathlib.Path(os.environ["FAKE_GPGV_PIDFILE"]).write_text(f"{os.getpid()}\n")
with os.fdopen(os.dup(status_fd), "w", encoding="utf-8") as stream:
    stream.write(os.environ["FAKE_GPGV_OUTPUT"] * int(os.environ.get("FAKE_GPGV_REPEAT", "1")))
    stream.flush()
sys.stdout.write(os.environ["FAKE_GPGV_STDOUT"])
sys.stdout.flush()
sys.stderr.write(os.environ["FAKE_GPGV_STDERR"])
sys.stderr.flush()

if os.environ.get("FAKE_GPGV_BLOCK") == "1":
    def stop(signum, _frame):
        pathlib.Path(os.environ["FAKE_SIGNAL_FILE"]).write_text(f"{signum}\n")
        raise SystemExit(64 + signum)
    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(number, stop)
    while True:
        time.sleep(1)

raise SystemExit(int(os.environ["FAKE_GPGV_STATUS"]))
""",
            encoding="utf-8",
        )
        script.chmod(0o755)

    def install_filter(self, *, blocking: bool = False, immediate: bool = False) -> None:
        script = self.bin / "sed"
        script.write_text(
            r"""#!/usr/bin/python3
import os
import pathlib
import signal
import sys
import time

pathlib.Path(os.environ["FAKE_FILTER_PIDFILE"]).write_text(f"{os.getpid()}\n")
if os.environ.get("FAKE_FILTER_IMMEDIATE") == "1":
    raise SystemExit(int(os.environ["FAKE_FILTER_STATUS"]))
if os.environ.get("FAKE_FILTER_BLOCK") == "1":
    def stop(signum, _frame):
        raise SystemExit(64 + signum)
    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(number, stop)
    while True:
        time.sleep(1)
data = sys.stdin.read().replace("[GNUPG:] EXPKEYSIG ", "[GNUPG:] GOODSIG ")
sys.stdout.write(data)
sys.stdout.flush()
raise SystemExit(int(os.environ["FAKE_FILTER_STATUS"]))
""",
            encoding="utf-8",
        )
        script.chmod(0o755)

    def install_failing_rmdir(self) -> None:
        script = self.bin / "rmdir"
        script.write_text(
            """#!/bin/sh
/usr/bin/rmdir "$@"
exit 9
""",
            encoding="utf-8",
        )
        script.chmod(0o755)

    def run_plain(
        self,
        args: list[str] | None = None,
        *,
        wrapper: pathlib.Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["/bin/sh", str(wrapper or self.candidate), *(args or [])],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env or self.environment(),
            timeout=15,
        )
        self.assert_tmp_empty()
        return result

    def run_with_fds(
        self,
        argument_builder,
        count: int,
        *,
        env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        pipes = [os.pipe() for _ in range(count)]
        reads = [pair[0] for pair in pipes]
        writes = [pair[1] for pair in pipes]
        try:
            result = subprocess.run(
                ["/bin/sh", str(self.candidate), *argument_builder(writes)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env or self.environment(),
                pass_fds=tuple(writes),
                timeout=15,
            )
        finally:
            for fd in writes:
                os.close(fd)
        captured: list[str] = []
        for fd in reads:
            with os.fdopen(fd, encoding="utf-8") as stream:
                captured.append(stream.read())
        self.assert_tmp_empty()
        return result, captured

    def assert_tmp_empty(self) -> None:
        self.assertEqual(list(self.tmp.iterdir()), [])

    @staticmethod
    def wait_for_file(path: pathlib.Path, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists() and path.read_text(encoding="utf-8").strip():
                return
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {path}")

    @staticmethod
    def assert_process_gone(pid: int, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not pathlib.Path(f"/proc/{pid}").exists():
                return
            time.sleep(0.02)
        raise AssertionError(f"process {pid} survived")

    def test_parser_validates_all_occurrences_before_execution(self) -> None:
        self.install_gpgv()
        self.install_filter()
        malformed = (
            ["--status-fd"],
            ["--status-fd", "abc"],
            ["--status-fd="],
            ["--status-fd=3x"],
            ["--status-fd", "-1"],
            ["--status-fd=1", "--status-fd=broken"],
            ["--status-fd=broken", "--status-fd=1"],
        )
        for args in malformed:
            with self.subTest(args=args):
                self.marker.unlink(missing_ok=True)
                result = self.run_plain(list(args))
                self.assertEqual(result.returncode, 1)
                self.assertIn("invalid --status-fd argument", result.stderr)
                self.assertFalse(self.marker.exists())

    def test_status_fd_spellings_repetition_and_end_of_options(self) -> None:
        self.install_gpgv()
        self.install_filter()

        plain = self.run_plain()
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(plain.stdout, REWRITTEN + BAD + "normal verifier stdout\n")

        for style in ("separate", "equals"):
            with self.subTest(style=style):
                def one(fds: list[int], style: str = style) -> list[str]:
                    if style == "separate":
                        return ["--status-fd", str(fds[0])]
                    return [f"--status-fd={fds[0]}"]

                result, captured = self.run_with_fds(one, 1)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(captured, [REWRITTEN + BAD])
                self.assertEqual(result.stdout, "normal verifier stdout\n")

        def repeated(fds: list[int]) -> list[str]:
            return ["--status-fd", str(fds[0]), f"--status-fd={fds[1]}"]

        result, captured = self.run_with_fds(repeated, 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(captured, ["", REWRITTEN + BAD])

        def ended(fds: list[int]) -> list[str]:
            return ["--status-fd", str(fds[0]), "--", f"--status-fd={fds[1]}"]

        result, captured = self.run_with_fds(ended, 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(captured, [REWRITTEN + BAD, ""])

    def test_verifier_status_wins_and_filter_failure_cannot_mutate_it(self) -> None:
        self.install_gpgv()
        self.install_filter()
        for verifier_status in (0, 1, 2):
            with self.subTest(verifier_status=verifier_status):
                result = self.run_plain(
                    env=self.environment(FAKE_GPGV_STATUS=str(verifier_status))
                )
                self.assertEqual(result.returncode, verifier_status)
                self.assertIn(REWRITTEN, result.stdout)
                self.assertIn(BAD, result.stdout)

        success_filter_failure = self.run_plain(
            env=self.environment(
                FAKE_GPGV_REPEAT="20000",
                FAKE_GPGV_STATUS="0",
                FAKE_FILTER_STATUS="7",
                FAKE_FILTER_IMMEDIATE="1",
            )
        )
        self.assertEqual(success_filter_failure.returncode, 7)

        verifier_failure = self.run_plain(
            env=self.environment(
                FAKE_GPGV_REPEAT="20000",
                FAKE_GPGV_STATUS="2",
                FAKE_FILTER_STATUS="7",
                FAKE_FILTER_IMMEDIATE="1",
            )
        )
        self.assertEqual(verifier_failure.returncode, 2)

    def test_cleanup_failure_is_last_in_ordinary_precedence(self) -> None:
        self.install_gpgv()
        self.install_filter()
        self.install_failing_rmdir()

        cleanup_only = self.run_plain()
        self.assertEqual(cleanup_only.returncode, 9)

        filter_wins = self.run_plain(
            env=self.environment(FAKE_FILTER_STATUS="7")
        )
        self.assertEqual(filter_wins.returncode, 7)

        verifier_wins = self.run_plain(
            env=self.environment(FAKE_GPGV_STATUS="2", FAKE_FILTER_STATUS="7")
        )
        self.assertEqual(verifier_wins.returncode, 2)

    def test_wrapper_signals_reach_verifier_preserve_flushed_status_and_rerun(self) -> None:
        self.install_gpgv(blocking=True)
        self.install_filter()
        for signum, expected in (
            (signal.SIGHUP, 129),
            (signal.SIGINT, 130),
            (signal.SIGTERM, 143),
        ):
            with self.subTest(signum=signum):
                for path in (self.marker, self.gpgv_pidfile, self.signal_file):
                    path.unlink(missing_ok=True)
                process = subprocess.Popen(
                    ["/bin/sh", str(self.candidate)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=self.environment(FAKE_GPGV_BLOCK="1"),
                    start_new_session=True,
                )
                self.wait_for_file(self.gpgv_pidfile)
                child_pid = int(self.gpgv_pidfile.read_text(encoding="utf-8"))
                os.kill(process.pid, signum)
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, expected, stderr)
                self.assertEqual(stdout.count(REWRITTEN), 1)
                self.assertIn(BAD, stdout)
                self.wait_for_file(self.signal_file)
                self.assertEqual(
                    int(self.signal_file.read_text(encoding="utf-8")), int(signum)
                )
                self.assert_process_gone(child_pid)
                self.assert_tmp_empty()

        rerun = self.run_plain(env=self.environment(FAKE_GPGV_BLOCK="0"))
        self.assertEqual(rerun.returncode, 0, rerun.stderr)

    def mutate_launch_window(self, kind: str) -> pathlib.Path:
        source = self.candidate.read_text(encoding="utf-8")
        marker = self.case / f"{kind}-launch"
        if kind == "gpgv":
            old = '  run_gpgv_child "$@" &\n  GPGV_PID=$!\n'
            new = (
                '  run_gpgv_child "$@" &\n'
                f'  printf "%s\\n" "$!" >"{marker}"\n'
                '  kill -STOP "$$"\n'
                '  GPGV_PID=$!\n'
            )
        else:
            old = (
                'start_filter() {\n'
                '  PENDING_STATUS=\n'
                '  PENDING_SIGNAL=\n'
                '  install_recording_traps\n'
                '  run_filter_child &\n'
                '  FILTER_PID=$!\n'
            )
            new = (
                'start_filter() {\n'
                '  PENDING_STATUS=\n'
                '  PENDING_SIGNAL=\n'
                '  install_recording_traps\n'
                '  run_filter_child &\n'
                f'  printf "%s\\n" "$!" >"{marker}"\n'
                '  kill -STOP "$$"\n'
                '  FILTER_PID=$!\n'
            )
        self.assertIn(old, source)
        mutated = self.case / f"candidate-{kind}-launch"
        mutated.write_text(source.replace(old, new, 1), encoding="utf-8")
        mutated.chmod(0o755)
        return mutated

    def exercise_launch_window(self, kind: str) -> None:
        self.install_gpgv(blocking=(kind == "gpgv"))
        self.install_filter(blocking=(kind == "filter"))
        mutated = self.mutate_launch_window(kind)
        marker = self.case / f"{kind}-launch"
        process = subprocess.Popen(
            ["/bin/sh", str(mutated)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(
                FAKE_GPGV_BLOCK="1" if kind == "gpgv" else "0",
                FAKE_FILTER_BLOCK="1" if kind == "filter" else "0",
            ),
            start_new_session=True,
        )
        self.wait_for_file(marker)
        child_pid = int(marker.read_text(encoding="utf-8"))
        os.kill(process.pid, signal.SIGTERM)
        os.kill(process.pid, signal.SIGCONT)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 143, stderr)
        self.assertLessEqual(stdout.count(REWRITTEN), 1)
        self.assert_process_gone(child_pid)
        self.assert_tmp_empty()

    def test_signal_during_gpgv_launch_registration_has_no_orphan(self) -> None:
        self.exercise_launch_window("gpgv")

    def test_signal_during_filter_launch_registration_has_no_orphan_or_duplicate(self) -> None:
        self.exercise_launch_window("filter")

    def test_filter_child_is_reaped_on_wrapper_signal(self) -> None:
        self.install_gpgv()
        self.install_filter(blocking=True)
        process = subprocess.Popen(
            ["/bin/sh", str(self.candidate)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(FAKE_FILTER_BLOCK="1"),
            start_new_session=True,
        )
        self.wait_for_file(self.filter_pidfile)
        filter_pid = int(self.filter_pidfile.read_text(encoding="utf-8"))
        os.kill(process.pid, signal.SIGTERM)
        _stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 143, stderr)
        self.assert_process_gone(filter_pid)
        self.assert_tmp_empty()


if __name__ == "__main__":
    unittest.main()
