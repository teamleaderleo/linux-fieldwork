from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "upstream/mmdebstrap/coverage.txt"
DRIVER = ROOT / "upstream/mmdebstrap/coverage.py"
TESTSUITE = ROOT / "upstream/mmdebstrap/debian/tests/testsuite"
CASE = ROOT / "upstream/mmdebstrap/tests/root-without-cap-sys-admin"
PATCH = ROOT / (
    "investigations/mmdebstrap-root-without-cap-sys-admin-scheduling/"
    "0001-run-capability-case-without-host-apt-hooks.patch"
)


def paragraph(text: str, name: str) -> str:
    marker = f"Test: {name}\n"
    start = text.index(marker)
    end = text.find("\n\n", start)
    if end == -1:
        end = len(text)
    return text[start:end]


class RootWithoutCapSysAdminSchedulingTest(unittest.TestCase):
    def apply_candidate(self) -> pathlib.Path:
        tempdir = pathlib.Path(
            tempfile.mkdtemp(prefix="mmdebstrap-capability-scheduling-")
        )
        self.addCleanup(shutil.rmtree, tempdir)
        destination = tempdir / "coverage.txt"
        shutil.copy2(COVERAGE, destination)
        completed = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "-p1",
                "-d",
                str(tempdir),
                "-i",
                str(PATCH),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return destination

    def test_candidate_moves_case_out_of_host_apt_hook_phase(self) -> None:
        baseline_text = COVERAGE.read_text(encoding="utf-8")
        candidate_text = self.apply_candidate().read_text(encoding="utf-8")
        baseline = paragraph(baseline_text, "root-without-cap-sys-admin")
        candidate = paragraph(candidate_text, "root-without-cap-sys-admin")

        self.assertNotIn("Needs-APT-Config: true", baseline)
        self.assertIn("Needs-Root: true", candidate)
        self.assertIn("Needs-APT-Config: true", candidate)

    def test_existing_second_phase_runs_incompatible_cases_without_hooks(self) -> None:
        testsuite = TESTSUITE.read_text(encoding="utf-8")
        self.assertIn(
            'CMD="mmdebstrap --setup-hook=$SRC/debian/tests/sourcesfilter '
            '--hook-dir=$SRC/hooks/file-mirror-automount"',
            testsuite,
        )
        self.assertIn(
            "SKIPPED_TESTS=$(grep-dctrl --exact-match --field "
            "Needs-APT-Config true",
            testsuite,
        )
        self.assertIn(
            'env CMD="mmdebstrap" DEFAULT_DIST=$DEFAULT_DIST',
            testsuite,
        )
        second_phase = testsuite.index('env CMD="mmdebstrap" DEFAULT_DIST=')
        second_command = testsuite[second_phase : second_phase + 400]
        self.assertNotIn("sourcesfilter", second_command)
        self.assertNotIn("file-mirror-automount", second_command)

    def test_driver_uses_needs_apt_config_as_host_config_incompatibility(self) -> None:
        driver = DRIVER.read_text(encoding="utf-8")
        self.assertIn(
            'test.get("Needs-APT-Config", "false") == "true" '
            "and use_host_apt_config",
            driver,
        )
        self.assertIn('(\"skip\", \"test cannot use host apt config\")', driver)

    def test_capability_invariant_remains_unchanged(self) -> None:
        case = CASE.read_text(encoding="utf-8")
        self.assertIn("capsh --drop=cap_sys_admin", case)
        self.assertIn("test ! -e /proc/self/fd", case)
        self.assertIn("tar -tf /tmp/debian-chroot.tar", case)


if __name__ == "__main__":
    unittest.main()
