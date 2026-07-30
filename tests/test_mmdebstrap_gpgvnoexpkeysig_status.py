from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
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
eval 'printf %s "$FAKE_GPGV_STATUS_OUTPUT" >&'"$status_fd"
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
        fake_sed.write_text(
            "#!/bin/sh\ncat >/dev/null\nexit 9\n", encoding="utf-8"
        )
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
            }
        )
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
            ),
            timeout=10,
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
        try:
            with os.fdopen(read_fd, encoding="utf-8") as stream:
                captured_status = stream.read()
        finally:
            if read_fd >= 0:
                try:
                    os.close(read_fd)
                except OSError:
                    pass
        self.assertEqual(list(case_tmp.iterdir()), [], f"leftovers for {label}")
        return result, captured_status

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

    def test_filter_failure_is_returned_when_verifier_succeeds(self) -> None:
        candidate = self.run_wrapper(
            self.candidate,
            "candidate-filter-failure",
            0,
            EXPIRED,
            bin_dir=self.filter_fail_bin,
        )
        self.assertEqual(candidate.returncode, 9)

    def test_candidate_source_has_explicit_status_handoff(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertIn('gpgv "$@"', baseline)
        self.assertNotIn("GPGV_STATUS=$?", baseline)
        self.assertIn("GPGV_STATUS=$?", candidate)
        self.assertIn('exit "$GPGV_STATUS"', candidate)
        self.assertIn('exit "$FILTER_STATUS"', candidate)
        self.assertIn("mkfifo", candidate)


if __name__ == "__main__":
    unittest.main()
