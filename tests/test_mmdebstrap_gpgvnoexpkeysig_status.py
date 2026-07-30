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
NORMAL_STDOUT = "normal verifier stdout\n"


class MmdebstrapGpgvStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-status/"
            "0001-preserve-gpgv-status.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="gpgvnoexpkeysig-status-")
        root = pathlib.Path(cls.work.name)
        cls.fake_bin = root / "bin"
        cls.fake_bin.mkdir()
        cls.fake_gpgv = cls.fake_bin / "gpgv"
        cls.fake_gpgv.write_text(
            """#!/bin/sh
set -eu
status_fd=1
while [ "$#" -gt 0 ]; do
  case $1 in
    --status-fd)
      status_fd=$2
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [ -n "${FAKE_GPGV_PIDFILE-}" ]; then
  printf '%s\n' "$$" >"$FAKE_GPGV_PIDFILE"
fi
if [ "${FAKE_GPGV_MODE-normal}" = sleep ]; then
  sleep "${FAKE_GPGV_SLEEP-30}"
fi
repeat=${FAKE_GPGV_REPEAT-1}
i=0
while [ "$i" -lt "$repeat" ]; do
  eval 'printf %s "$FAKE_GPGV_STATUS_OUTPUT" >&'"$status_fd"
  i=$((i + 1))
done
printf '%s' "${FAKE_GPGV_STDOUT-}"
printf '%s' "${FAKE_GPGV_STDERR-}" >&2
exit "$FAKE_GPGV_STATUS"
""",
            encoding="utf-8",
        )
        cls.fake_gpgv.chmod(0o755)

        cls.filter_fail_bin = root / "filter-fail-bin"
        cls.filter_fail_bin.mkdir()
        (cls.filter_fail_bin / "gpgv").symlink_to(cls.fake_gpgv)
        fake_sed = cls.filter_fail_bin / "sed"
        fake_sed.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
        fake_sed.chmod(0o755)

        cls.baseline = root / "baseline"
        cls.candidate_root = root / "candidate"
        cls.candidate = cls.candidate_root / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.candidate.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.baseline)
        shutil.copy2(cls.source, cls.candidate)

        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "-p1",
                "-i",
                str(cls.patch),
            ],
            cwd=cls.candidate_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)
        for wrapper in (cls.baseline, cls.candidate):
            syntax = subprocess.run(
                ["/bin/sh", "-n", str(wrapper)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if syntax.returncode != 0:
                cls.work.cleanup()
                raise AssertionError(syntax.stdout + syntax.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def environment(
        self,
        case_tmp: pathlib.Path,
        status: int,
        status_output: str,
        *,
        stdout: str = "",
        stderr: str = "",
        bin_dir: pathlib.Path | None = None,
        repeat: int = 1,
        mode: str = "normal",
        pidfile: pathlib.Path | None = None,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{bin_dir or self.fake_bin}:/usr/bin:/bin",
                "TMPDIR": str(case_tmp),
                "FAKE_GPGV_STATUS": str(status),
                "FAKE_GPGV_STATUS_OUTPUT": status_output,
                "FAKE_GPGV_STDOUT": stdout,
                "FAKE_GPGV_STDERR": stderr,
                "FAKE_GPGV_REPEAT": str(repeat),
                "FAKE_GPGV_MODE": mode,
            }
        )
        if pidfile is not None:
            env["FAKE_GPGV_PIDFILE"] = str(pidfile)
        return env

    def run_wrapper(
        self,
        wrapper: pathlib.Path,
        label: str,
        status: int,
        status_output: str,
        stderr: str = "",
        *,
        stdout: str = "",
        bin_dir: pathlib.Path | None = None,
        repeat: int = 1,
    ) -> subprocess.CompletedProcess[str]:
        case_tmp = pathlib.Path(self.work.name) / label
        case_tmp.mkdir()
        result = subprocess.run(
            ["/bin/sh", str(wrapper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(
                case_tmp,
                status,
                status_output,
                stdout=stdout,
                stderr=stderr,
                bin_dir=bin_dir,
                repeat=repeat,
            ),
            timeout=15,
        )
        self.assertEqual(list(case_tmp.iterdir()), [], f"leftovers for {label}")
        return result

    def run_wrapper_with_status_fd(
        self,
        wrapper: pathlib.Path,
        label: str,
        status: int,
        status_output: str,
        *,
        stdout: str,
        stderr: str,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        case_tmp = pathlib.Path(self.work.name) / label
        case_tmp.mkdir()
        read_fd, write_fd = os.pipe()
        try:
            result = subprocess.run(
                ["/bin/sh", str(wrapper), "--status-fd", str(write_fd)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.environment(
                    case_tmp,
                    status,
                    status_output,
                    stdout=stdout,
                    stderr=stderr,
                ),
                pass_fds=(write_fd,),
                timeout=10,
            )
        finally:
            os.close(write_fd)
        with os.fdopen(read_fd, encoding="utf-8") as stream:
            captured_status = stream.read()
        self.assertEqual(list(case_tmp.iterdir()), [], f"leftovers for {label}")
        return result, captured_status

    @staticmethod
    def process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def wait_for_pidfile(self, process: subprocess.Popen[str], pidfile: pathlib.Path) -> int:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if pidfile.exists():
                return int(pidfile.read_text().strip())
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"wrapper exited before verifier pid: {process.returncode}: "
                    f"{stdout}{stderr}"
                )
            time.sleep(0.01)
        self.fail("fake verifier pidfile was not created")

    def start_sleeping_wrapper(
        self, label: str
    ) -> tuple[subprocess.Popen[str], pathlib.Path, int]:
        case_tmp = pathlib.Path(self.work.name) / label
        case_tmp.mkdir()
        pidfile = case_tmp / "gpgv.pid"
        process = subprocess.Popen(
            ["/bin/sh", str(self.candidate)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(
                case_tmp,
                0,
                EXPIRED,
                mode="sleep",
                pidfile=pidfile,
            ),
            start_new_session=True,
        )
        child_pid = self.wait_for_pidfile(process, pidfile)
        return process, case_tmp, child_pid

    def assert_process_gone(self, pid: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and self.process_exists(pid):
            time.sleep(0.02)
        self.assertFalse(self.process_exists(pid))

    def test_success_rewrites_only_expired_signature_status(self) -> None:
        output = EXPIRED + BAD
        expected = EXPIRED.replace("EXPKEYSIG", "GOODSIG") + BAD
        baseline = self.run_wrapper(
            self.baseline, "baseline-success", 0, output, "gpgv-stderr\n"
        )
        candidate = self.run_wrapper(
            self.candidate, "candidate-success", 0, output, "gpgv-stderr\n"
        )
        for result in (baseline, candidate):
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, expected)
            self.assertIn("gpgv-stderr", result.stderr)

    def test_candidate_preserves_gpgv_status_one(self) -> None:
        baseline = self.run_wrapper(self.baseline, "baseline-one", 1, BAD)
        candidate = self.run_wrapper(self.candidate, "candidate-one", 1, BAD)
        self.assertEqual(baseline.returncode, 0)
        self.assertEqual(candidate.returncode, 1)
        self.assertEqual(baseline.stdout, BAD)
        self.assertEqual(candidate.stdout, BAD)

    def test_candidate_preserves_gpgv_status_two(self) -> None:
        baseline = self.run_wrapper(self.baseline, "baseline-two", 2, EXPIRED)
        candidate = self.run_wrapper(self.candidate, "candidate-two", 2, EXPIRED)
        expected = EXPIRED.replace("EXPKEYSIG", "GOODSIG")
        self.assertEqual(baseline.returncode, 0)
        self.assertEqual(candidate.returncode, 2)
        self.assertEqual(baseline.stdout, expected)
        self.assertEqual(candidate.stdout, expected)

    def test_explicit_status_fd_is_filtered_separately_from_normal_stdout(self) -> None:
        baseline, baseline_status = self.run_wrapper_with_status_fd(
            self.baseline,
            "baseline-explicit-fd",
            2,
            EXPIRED,
            stdout=NORMAL_STDOUT,
            stderr="verifier-stderr\n",
        )
        candidate, candidate_status = self.run_wrapper_with_status_fd(
            self.candidate,
            "candidate-explicit-fd",
            2,
            EXPIRED,
            stdout=NORMAL_STDOUT,
            stderr="verifier-stderr\n",
        )
        expected_status = EXPIRED.replace("EXPKEYSIG", "GOODSIG")
        self.assertEqual(baseline.returncode, 0)
        self.assertEqual(candidate.returncode, 2)
        for result, captured in (
            (baseline, baseline_status),
            (candidate, candidate_status),
        ):
            self.assertEqual(result.stdout, NORMAL_STDOUT)
            self.assertIn("verifier-stderr", result.stderr)
            self.assertEqual(captured, expected_status)

    def test_immediate_filter_failure_cannot_mutate_verifier_status(self) -> None:
        for verifier_status, expected in ((0, 7), (2, 2)):
            with self.subTest(verifier_status=verifier_status):
                candidate = self.run_wrapper(
                    self.candidate,
                    f"candidate-filter-immediate-{verifier_status}",
                    verifier_status,
                    EXPIRED,
                    bin_dir=self.filter_fail_bin,
                    repeat=5000,
                )
                self.assertEqual(candidate.returncode, expected)

    def test_parent_only_term_is_deferred_but_eventually_cleans(self) -> None:
        process, case_tmp, child_pid = self.start_sleeping_wrapper(
            "candidate-parent-only-term"
        )
        os.kill(process.pid, signal.SIGTERM)
        time.sleep(0.25)
        self.assertIsNone(process.poll(), "parent-only TERM unexpectedly became prompt")
        self.assertTrue(self.process_exists(child_pid))

        os.kill(child_pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 143, stdout + stderr)
        self.assert_process_gone(child_pid)
        self.assertEqual(list(case_tmp.iterdir()), [])

    def test_process_group_term_stops_verifier_and_cleans(self) -> None:
        process, case_tmp, child_pid = self.start_sleeping_wrapper(
            "candidate-process-group-term"
        )
        os.killpg(process.pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 143, stdout + stderr)
        self.assert_process_gone(child_pid)
        self.assertEqual(list(case_tmp.iterdir()), [])

    def test_candidate_source_uses_regular_status_spool(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertIn('gpgv "$@"', baseline)
        self.assertNotIn("GPGV_STATUS=$?", baseline)
        self.assertIn("GPGV_STATUS=$?", candidate)
        self.assertIn('exit "$GPGV_STATUS"', candidate)
        self.assertIn('exit "$FILTER_STATUS"', candidate)
        self.assertIn('STATUS_FILE="$FILTER_DIR/status"', candidate)
        self.assertIn('>"$STATUS_FILE"', candidate)
        self.assertIn('<"$STATUS_FILE"', candidate)
        self.assertNotIn("mkfifo", candidate)
        self.assertNotIn("FILTER_PID", candidate)
        self.assertLess(candidate.index('gpgv "$@"'), candidate.index('sed "s/^'))


if __name__ == "__main__":
    unittest.main()
