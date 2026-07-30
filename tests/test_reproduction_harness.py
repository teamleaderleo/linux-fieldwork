from __future__ import annotations

import os
import subprocess
import tempfile
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

    def test_workflow_bootstrap_installs_patch_and_rejects_fork_heads(self) -> None:
        self.assertIn(
            "autopkgtest ca-certificates patch python3 procps util-linux",
            self.workflow,
        )
        same_repository_guard = (
            "github.event.pull_request.head.repo.full_name == github.repository"
        )
        self.assertEqual(self.workflow.count(same_repository_guard), 2)

    def test_early_neutral_exit_retains_reason_in_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "bin"
            fake_bin.mkdir()
            fake_id = fake_bin / "id"
            fake_id.write_text("#!/bin/sh\nprintf '1000\\n'\n", encoding="utf-8")
            fake_id.chmod(0o755)
            run_dir = tmp_path / "run"
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            env["RUN_DIR"] = str(run_dir)
            completed = subprocess.run(
                ["bash", str(REPRODUCTION_SCRIPT)],
                cwd=REPOSITORY_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )

            self.assertEqual(completed.returncode, 77, completed.stderr)
            self.assertEqual((run_dir / "exit-status").read_text(), "77\n")
            reason = (run_dir / "preflight-error.txt").read_text()
            self.assertIn("requires root", reason)
            result = (run_dir / "result.md").read_text()
            self.assertIn("neutral-or-skipped", result)
            self.assertIn("requires root", result)


if __name__ == "__main__":
    unittest.main()
