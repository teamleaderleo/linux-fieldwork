from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tools.relative_exec_cwd_audit import (
    audit_text,
    is_relative_program_with_separator,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/relative_exec_cwd_audit.py"


class RelativeExecCwdAuditTest(unittest.TestCase):
    def test_python_relative_program_with_cwd_is_reported(self) -> None:
        findings = audit_text(
            "sample.py",
            "import subprocess\nsubprocess.run(['./proxy', '--check'], cwd=work)\n",
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "./proxy")
        self.assertEqual(findings[0].cwd, "work")

    def test_python_keyword_args_and_executable_are_reported(self) -> None:
        source = """\
import subprocess
subprocess.run(args=['./proxy', '--check'], cwd=work)
subprocess.Popen(['decoy-name'], executable='../real-proxy', cwd=work)
"""
        findings = audit_text("sample.py", source)
        self.assertEqual(
            [item.program for item in findings], ["./proxy", "../real-proxy"]
        )

    def test_python_executable_override_controls_identity(self) -> None:
        source = """\
import subprocess
subprocess.Popen(['./decoy'], executable='/usr/bin/real-tool', cwd=work)
subprocess.Popen(['./decoy'], executable=selected_tool, cwd=work)
"""
        self.assertEqual(audit_text("sample.py", source), [])

    def test_python_shell_true_uses_the_shell_identity(self) -> None:
        source = """\
import subprocess
subprocess.run('./decoy --check', cwd=work, shell=True)
subprocess.run('./decoy --check', cwd=work, shell=use_shell)
subprocess.run('./decoy --check', cwd=work, shell=True, executable='../custom-shell')
"""
        findings = audit_text("sample.py", source)
        self.assertEqual([item.program for item in findings], ["../custom-shell"])

    def test_python_absolute_and_simple_programs_are_controls(self) -> None:
        source = """\
import subprocess
subprocess.run(['/usr/bin/proxy'], cwd=work)
subprocess.run(['proxy'], cwd=work)
subprocess.run(['./proxy'])
subprocess.run(['./proxy'], cwd=None)
"""
        self.assertEqual(audit_text("sample.py", source), [])

    def test_cross_platform_absolute_paths_are_controls(self) -> None:
        for program in (
            "/usr/bin/tool",
            r"C:\Windows\System32\tool.exe",
            r"\Windows\System32\tool.exe",
            r"\\server\share\tool.exe",
        ):
            with self.subTest(program=program):
                self.assertFalse(is_relative_program_with_separator(program))
        self.assertTrue(is_relative_program_with_separator(r"C:relative\tool.exe"))

    def test_rust_relative_program_with_current_dir_is_reported(self) -> None:
        source = """\
let output = Command::new("./../nuget.exe")
    .arg("restore")
    .current_dir(renderer_path)
    .output()?;
"""
        findings = audit_text("build.rs", source, language="rust")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "./../nuget.exe")
        self.assertEqual(findings[0].cwd, "renderer_path")

    def test_rust_multiline_program_literal_is_reported(self) -> None:
        source = """\
let output = Command::new(
    "./tools/renderer",
)
.current_dir(renderer_path)
.output()?;
"""
        findings = audit_text("build.rs", source, language="rust")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "./tools/renderer")
        self.assertEqual(findings[0].line, 1)

    def test_rust_adjacent_command_does_not_lend_current_dir(self) -> None:
        source = """\
let pair = (
    Command::new("./first"),
    Command::new("second").current_dir(work),
);
"""
        self.assertEqual(audit_text("build.rs", source, language="rust"), [])

    def test_rust_adjacent_owned_chains_are_reported_separately(self) -> None:
        source = """\
let pair = (
    Command::new("./first").current_dir(first_work),
    Command::new("../second").current_dir(second_work),
);
"""
        findings = audit_text("build.rs", source, language="rust")
        self.assertEqual(
            [(item.program, item.cwd) for item in findings],
            [("./first", "first_work"), ("../second", "second_work")],
        )

    def test_rust_absolute_and_simple_programs_are_controls(self) -> None:
        source = """\
Command::new("/usr/bin/tool").current_dir(work).output()?;
Command::new("tool").current_dir(work).output()?;
Command::new("./tool").output()?;
"""
        self.assertEqual(audit_text("build.rs", source, language="rust"), [])

    def test_shell_env_chdir_relative_program_is_reported(self) -> None:
        source = "env --chdir=/tmp/target ./proxy --check\n"
        findings = audit_text("probe.sh", source)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "./proxy")
        self.assertEqual(findings[0].cwd, "/tmp/target")

    def test_shell_short_chdir_and_absolute_env_are_reported(self) -> None:
        source = "/usr/bin/env -u OLD_VALUE -C /tmp/target ../proxy --check\n"
        findings = audit_text("probe.sh", source)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "../proxy")
        self.assertEqual(findings[0].cwd, "/tmp/target")

    def test_shell_attached_short_chdir_is_reported(self) -> None:
        findings = audit_text("probe.sh", "env -C/tmp/target ./proxy\n")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].cwd, "/tmp/target")

    def test_shell_assignments_and_separator_are_parsed(self) -> None:
        source = "env FLAG=yes --chdir /tmp/target -- ../proxy --check\n"
        findings = audit_text("probe.sh", source)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "../proxy")

    def test_shell_assignment_after_option_separator_is_parsed(self) -> None:
        source = "env --chdir /tmp/target -- FLAG=yes ../proxy --check\n"
        findings = audit_text("probe.sh", source)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "../proxy")
        self.assertEqual(findings[0].cwd, "/tmp/target")

    def test_shell_split_strings_are_outside_literal_scope(self) -> None:
        source = """\
env -C /tmp/target -S './proxy --check'
env --chdir=/tmp/target --split-string='./proxy --check'
"""
        self.assertEqual(audit_text("probe.sh", source), [])

    def test_shell_env_argument_text_is_not_a_launch(self) -> None:
        source = """\
printf '%s\\n' env --chdir=/tmp/target ./proxy
logger env -C /tmp/target ../proxy
"""
        self.assertEqual(audit_text("probe.sh", source), [])

    def test_shell_relative_env_binary_is_not_assumed_coreutils(self) -> None:
        source = """\
./env -C /tmp/target ../proxy
tools/env --chdir=/tmp/target ./proxy
"""
        self.assertEqual(audit_text("probe.sh", source), [])

    def test_shell_leading_assignment_preserves_env_command_position(self) -> None:
        source = "TRACE=yes /usr/bin/env -C /tmp/target ../proxy --check\n"
        findings = audit_text("probe.sh", source)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].program, "../proxy")
        self.assertEqual(findings[0].cwd, "/tmp/target")

    def test_shell_absolute_and_simple_programs_are_controls(self) -> None:
        source = """\
env --chdir=/tmp/target /usr/bin/proxy
env --chdir=/tmp/target proxy
env FLAG=yes ./proxy
"""
        self.assertEqual(audit_text("probe.sh", source), [])

    def test_cli_json_and_failure_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "sample.py"
            path.write_text(
                "import subprocess\nsubprocess.run(['../tool'], cwd=work)\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--json",
                    "--fail-on-findings",
                    str(path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 1, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload[0]["program"], "../tool")
        self.assertEqual(payload[0]["language"], "python")

    def test_cli_clean_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "sample.py"
            path.write_text(
                "import subprocess\nsubprocess.run(['tool'], cwd=work)\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(TOOL), "--fail-on-findings", str(path)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("no relative executable", completed.stdout)


if __name__ == "__main__":
    unittest.main()
