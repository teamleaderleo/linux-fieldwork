from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPRODUCTION_SCRIPT = REPOSITORY_ROOT / "scripts/reproduce-mmdebstrap-autopkgtest.sh"
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/linux-fieldwork-ci.yml"


class ReproductionHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = REPRODUCTION_SCRIPT.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_uses_package_metadata_for_autopkgtest_version(self) -> None:
        self.assertNotIn("autopkgtest --version", self.script)
        self.assertIn(
            "dpkg-query -W -f='${binary:Package}\\t${Version}\\t${Architecture}\\n'",
            self.script,
        )
        self.assertIn(
            "autopkgtest mmdebstrap perltidy apt dpkg patch",
            self.script,
        )

    def test_retains_the_real_autopkgtest_command_and_status(self) -> None:
        self.assertIn(
            'autopkgtest --output-dir "$output_dir" "$source_tree" -- null',
            self.script,
        )
        self.assertIn('printf \'%s\\n\' "$status" >"$status_file"', self.script)
        self.assertIn('exit "$status"', self.script)

    def test_shell_files_do_not_depend_on_executable_mode(self) -> None:
        self.assertIn(
            'bash scripts/reproduce-mmdebstrap-autopkgtest.sh',
            self.workflow,
        )
        self.assertIn(
            'bash "$repo_root/scripts/capture-linux-context.sh"',
            self.script,
        )


if __name__ == "__main__":
    unittest.main()
