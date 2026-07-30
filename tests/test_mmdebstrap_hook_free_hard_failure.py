from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap"
PATCH = ROOT / (
    "investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure/"
    "0001-run-hook-free-capability-case-as-hard-failure.patch"
)
CASE = SOURCE / "tests/root-without-cap-sys-admin"


def paragraph(text: str, name: str) -> str:
    marker = f"Test: {name}\n"
    start = text.index(marker)
    end = text.find("\n\n", start)
    return text[start:] if end == -1 else text[start:end]


class MmdebstrapHookFreeHardFailureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="mmdebstrap-hook-free-hard-failure-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.tree = pathlib.Path(self.temporary.name) / "mmdebstrap"
        for relative in (
            "coverage.txt",
            "coverage.py",
            "debian/tests/testsuite",
        ):
            destination = self.tree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / relative, destination)

        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=self.tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

        self.baseline_coverage = (SOURCE / "coverage.txt").read_text(encoding="utf-8")
        self.candidate_coverage = (self.tree / "coverage.txt").read_text(
            encoding="utf-8"
        )
        self.candidate_driver = (self.tree / "coverage.py").read_text(
            encoding="utf-8"
        )
        self.baseline_testsuite = (SOURCE / "debian/tests/testsuite").read_text(
            encoding="utf-8"
        )
        self.candidate_testsuite = (
            self.tree / "debian/tests/testsuite"
        ).read_text(encoding="utf-8")

    def test_candidate_uses_distinct_hook_free_hard_failure_metadata(self) -> None:
        baseline = paragraph(self.baseline_coverage, "root-without-cap-sys-admin")
        candidate = paragraph(self.candidate_coverage, "root-without-cap-sys-admin")

        self.assertNotIn("Needs-APT-Config: true", baseline)
        self.assertNotIn("Needs-Hook-Free-APT-Config: true", baseline)
        self.assertIn("Needs-Root: true", candidate)
        self.assertIn("Needs-Hook-Free-APT-Config: true", candidate)
        self.assertNotIn("Needs-APT-Config: true", candidate)

        self.assertIn(
            'test.get("Needs-Hook-Free-APT-Config", "false") == "true"',
            self.candidate_driver,
        )
        self.assertIn("and use_host_apt_config", self.candidate_driver)
        self.assertIn(
            '("skip", "test cannot use host apt config")', self.candidate_driver
        )

    def test_hard_phase_is_hook_free_and_precedes_soft_transition_phase(self) -> None:
        hard_start = self.candidate_testsuite.index("HOOK_FREE_HARD_TESTS=")
        soft_start = self.candidate_testsuite.index(
            "# run only those tests that were skipped because of USE_HOST_APT_CONFIG=yes"
        )
        self.assertLess(hard_start, soft_start)
        hard = self.candidate_testsuite[hard_start:soft_start]
        soft = self.candidate_testsuite[soft_start : soft_start + 800]

        self.assertIn("Needs-Hook-Free-APT-Config true", hard)
        self.assertIn('env CMD="mmdebstrap"', hard)
        self.assertIn('"$SRC/coverage.py" --exitfirst $HOOK_FREE_HARD_TESTS', hard)
        self.assertNotIn("sourcesfilter", hard)
        self.assertNotIn("file-mirror-automount", hard)
        self.assertIn('exit "$ret"', hard)

        self.assertIn("Needs-APT-Config true", soft)
        self.assertIn("$SKIPPED_TESTS || exit 77", soft)
        self.assertNotIn("Needs-Hook-Free-APT-Config", soft)

    def test_actual_candidate_status_block_preserves_hard_failures(self) -> None:
        hard_start = self.candidate_testsuite.index("HOOK_FREE_HARD_TESTS=")
        soft_start = self.candidate_testsuite.index(
            "# run only those tests that were skipped because of USE_HOST_APT_CONFIG=yes"
        )
        hard = self.candidate_testsuite[hard_start:soft_start]
        block_start = hard.index('if [ "$ret" -eq 124 ]; then')
        block_end = hard.index("\nfi", block_start) + len("\nfi")
        status_block = hard[block_start:block_end]

        script = pathlib.Path(self.temporary.name) / "classify-status.sh"
        script.write_text(
            '#!/bin/sh\nret=$1\nTIMEOUT=123\n'
            + status_block
            + "\nexit 0\n",
            encoding="utf-8",
        )
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(script)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

        expected = {0: 0, 1: 1, 2: 2, 124: 77}
        for child_status, wrapper_status in expected.items():
            with self.subTest(child_status=child_status):
                completed = subprocess.run(
                    ["/bin/sh", str(script), str(child_status)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(completed.returncode, wrapper_status)

    def test_candidate_sources_compile_and_parse(self) -> None:
        python = subprocess.run(
            ["python3", "-m", "py_compile", str(self.tree / "coverage.py")],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        shell = subprocess.run(
            ["/bin/sh", "-n", str(self.tree / "debian/tests/testsuite")],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(python.returncode, 0, python.stderr)
        self.assertEqual(shell.returncode, 0, shell.stderr)

    def test_capability_invariant_remains_unchanged(self) -> None:
        case = CASE.read_text(encoding="utf-8")
        self.assertIn("capsh --drop=cap_sys_admin", case)
        self.assertIn("test ! -e /proc/self/fd", case)
        self.assertIn("tar -tf /tmp/debian-chroot.tar", case)

    def test_baseline_soft_phase_is_the_negative_control(self) -> None:
        self.assertNotIn("HOOK_FREE_HARD_TESTS=", self.baseline_testsuite)
        self.assertIn(
            '"$SRC/coverage.py" --exitfirst $SKIPPED_TESTS || exit 77',
            self.baseline_testsuite,
        )


if __name__ == "__main__":
    unittest.main()
