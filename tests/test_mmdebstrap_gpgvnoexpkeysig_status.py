from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


EXPIRED = "[GNUPG:] EXPKEYSIG 0123456789ABCDEF expired key\n"
BAD = "[GNUPG:] BADSIG 0123456789ABCDEF bad signature\n"


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
        fake_gpgv = cls.fake_bin / "gpgv"
        fake_gpgv.write_text(
            """#!/bin/sh
set -eu
printf '%s' "$FAKE_GPGV_STATUS_OUTPUT"
printf '%s' "${FAKE_GPGV_STDERR-}" >&2
exit "$FAKE_GPGV_STATUS"
""",
            encoding="utf-8",
        )
        fake_gpgv.chmod(0o755)

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

    def run_wrapper(
        self,
        wrapper: pathlib.Path,
        label: str,
        status: int,
        status_output: str,
        stderr: str = "",
    ) -> subprocess.CompletedProcess[str]:
        case_tmp = pathlib.Path(self.work.name) / label
        case_tmp.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "TMPDIR": str(case_tmp),
                "FAKE_GPGV_STATUS": str(status),
                "FAKE_GPGV_STATUS_OUTPUT": status_output,
                "FAKE_GPGV_STDERR": stderr,
            }
        )
        result = subprocess.run(
            ["/bin/sh", str(wrapper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=10,
        )
        self.assertEqual(list(case_tmp.iterdir()), [], f"leftovers for {label}")
        return result

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

    def test_candidate_source_has_explicit_status_handoff(self) -> None:
        baseline = self.baseline.read_text(encoding="utf-8")
        candidate = self.candidate.read_text(encoding="utf-8")
        self.assertIn("gpgv \"$@\"", baseline)
        self.assertNotIn("GPGV_STATUS=$?", baseline)
        self.assertIn("GPGV_STATUS=$?", candidate)
        self.assertIn('exit "$GPGV_STATUS"', candidate)
        self.assertIn("mkfifo", candidate)


if __name__ == "__main__":
    unittest.main()
