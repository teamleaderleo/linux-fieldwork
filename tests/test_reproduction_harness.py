from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPRODUCTION_SCRIPT = REPOSITORY_ROOT / "scripts/reproduce-mmdebstrap-autopkgtest.sh"
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/linux-fieldwork-ci.yml"
SOURCE_TESTSUITE = REPOSITORY_ROOT / "upstream/mmdebstrap/debian/tests/testsuite"
CWD_CHANGING_TEST = (
    REPOSITORY_ROOT
    / "upstream/mmdebstrap/tests/cwd-directory-not-accessible-by-unshared-user"
)
WRAPPER_PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-autopkgtest-1141078"
    / "installed-command-wrapper.patch"
)
SOURCESFILTER_PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-autopkgtest-1141078"
    / "sourcesfilter-deb822.patch"
)
CAPABILITY_PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure"
    / "0001-run-hook-free-capability-case-as-hard-failure.patch"
)
SIGNAL_PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-autopkgtest-1141078"
    / "sigint-process-group-kill-sid.patch"
)


def extract_mmdebstrap_proxy(testsuite: str) -> str:
    marker = "cat << 'END' > ./mmdebstrap\n"
    start = testsuite.index(marker) + len(marker)
    end = testsuite.index("\nEND\nchmod 0755 ./mmdebstrap", start)
    return testsuite[start:end] + "\n"


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
            "autopkgtest mmdebstrap perltidy apt dpkg patch procps dash",
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
            "bash scripts/reproduce-mmdebstrap-autopkgtest.sh",
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

    def apply_wrapper_patch(self, tree: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-d",
                str(tree),
                "-i",
                str(WRAPPER_PATCH),
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def assert_exact_patch_output(self, completed: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(completed.returncode, 0, completed.stderr)
        combined = (completed.stdout + completed.stderr).lower()
        self.assertNotIn("fuzz", combined)
        self.assertNotIn("offset", combined)

    def test_installed_command_wrapper_patch_applies_exactly_and_proxy_has_pod(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            destination = tree / "debian/tests"
            destination.mkdir(parents=True)
            shutil.copy2(SOURCE_TESTSUITE, destination / "testsuite")
            completed = self.apply_wrapper_patch(tree)
            patched = (destination / "testsuite").read_text(encoding="utf-8")
            proxy_path = Path(tmp) / "mmdebstrap-proxy"
            proxy_path.write_text(extract_mmdebstrap_proxy(patched), encoding="utf-8")
            perl_syntax = subprocess.run(
                ["perl", "-c", str(proxy_path)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            pod = subprocess.run(
                ["pod2man", str(proxy_path)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )

        self.assert_exact_patch_output(completed)
        self.assertIn("exec '/usr/bin/mmdebstrap', @ARGV", patched)
        self.assertIn('CMD="$AUTOPKGTEST_TMP/mmdebstrap --setup-hook=', patched)
        self.assertNotIn('CMD="./mmdebstrap --setup-hook=', patched)
        self.assertNotIn('CMD="$SRC/mmdebstrap --setup-hook=', patched)
        self.assertNotIn("mmdebstrap-under-test", patched)
        self.assertEqual(perl_syntax.returncode, 0, perl_syntax.stderr)
        self.assertEqual(pod.returncode, 0, pod.stderr)
        self.assertIn("proxy to the installed package under test", pod.stdout)

    def test_installed_proxy_survives_a_test_working_directory_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tree = root / "tree"
            autopkgtest_tmp = root / "autopkgtest-tmp"
            autopkgtest_tmp.mkdir()
            destination = tree / "debian/tests"
            destination.mkdir(parents=True)
            shutil.copy2(SOURCE_TESTSUITE, destination / "testsuite")
            completed = self.apply_wrapper_patch(tree)
            self.assert_exact_patch_output(completed)
            patched = (destination / "testsuite").read_text(encoding="utf-8")
            command_match = re.search(r'env CMD="([^"]+)" DEFAULT_DIST=', patched)
            self.assertIsNotNone(command_match)
            command = command_match.group(1)
            expanded_command = command.replace(
                "$AUTOPKGTEST_TMP", str(autopkgtest_tmp)
            ).replace("$SRC", str(tree))
            rendered_test = CWD_CHANGING_TEST.read_text(encoding="utf-8").replace(
                "{{ CMD }}", expanded_command
            )
            self.assertIn("set -- env --chdir=/tmp/debian-chroot", rendered_test)
            self.assertIn(
                f'set -- "$@" {autopkgtest_tmp}/mmdebstrap --setup-hook=',
                rendered_test,
            )

            source_decoy = tree / "mmdebstrap"
            source_decoy.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
            source_decoy.chmod(0o755)

            proxy = autopkgtest_tmp / "mmdebstrap"
            result_path = root / "proxy-result"
            proxy.write_text(
                "#!/bin/sh\n"
                'printf "%s\\n" "$PWD" >"$PROXY_RESULT"\n'
                'printf "%s\\n" "$@" >>"$PROXY_RESULT"\n',
                encoding="utf-8",
            )
            proxy.chmod(0o755)
            changed_directory = root / "changed-directory"
            changed_directory.mkdir()
            script = (
                f"CMD={shlex.quote(expanded_command)}\n"
                f"set -- env --chdir={shlex.quote(str(changed_directory))}\n"
                'set -- "$@" $CMD\n'
                '"$@"\n'
            )
            env = os.environ.copy()
            env["PROXY_RESULT"] = str(result_path)
            invoked = subprocess.run(
                ["/bin/sh", "-eu", "-c", script],
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(invoked.returncode, 0, invoked.stderr)
            result = result_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result[0], str(changed_directory))
        self.assertEqual(
            result[1:],
            [
                f"--setup-hook={tree}/debian/tests/sourcesfilter",
                f"--hook-dir={tree}/hooks/file-mirror-automount",
            ],
        )

    def test_exact_patch_helper_rejects_fuzz_and_offset_and_orders_patches(self) -> None:
        self.assertIn("apply_exact_patch()", self.script)
        self.assertIn("patch --batch --forward --fuzz=0", self.script)
        self.assertIn("(fuzz|offset)", self.script)
        self.assertIn("zero fuzz and zero offset", self.script)

        calls = [
            'apply_exact_patch sourcesfilter "$sourcesfilter_patch"',
            'apply_exact_patch capability "$capability_patch"',
            'apply_exact_patch override "$override_patch"',
            'apply_exact_patch signal "$signal_patch"',
        ]
        positions = [self.script.index(call) for call in calls]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(set(positions)), 4)

    def test_sourcesfilter_patch_is_preflighted_applied_and_hashed(self) -> None:
        self.assertTrue(SOURCESFILTER_PATCH.is_file())
        self.assertIn(
            'sourcesfilter_patch="$repo_root/investigations/'
            'mmdebstrap-autopkgtest-1141078/sourcesfilter-deb822.patch"',
            self.script,
        )
        self.assertIn('if [[ ! -f $sourcesfilter_patch ]]', self.script)
        self.assertIn(
            'apply_exact_patch sourcesfilter "$sourcesfilter_patch"',
            self.script,
        )
        self.assertIn('"$source_tree/debian/tests/sourcesfilter"', self.script)
        self.assertIn(
            'Source compatibility override: `sourcesfilter-deb822.patch`',
            self.script,
        )

    def test_capability_hard_failure_patch_is_applied_and_hashed(self) -> None:
        self.assertTrue(CAPABILITY_PATCH.is_file())
        self.assertIn(
            'capability_patch="$repo_root/investigations/'
            'mmdebstrap-root-without-cap-sys-admin-hard-failure/'
            '0001-run-hook-free-capability-case-as-hard-failure.patch"',
            self.script,
        )
        self.assertIn('if [[ ! -f $capability_patch ]]', self.script)
        self.assertIn(
            'apply_exact_patch capability "$capability_patch"',
            self.script,
        )
        self.assertIn('"$source_tree/debian/tests/testsuite"', self.script)
        self.assertIn('"$source_tree/coverage.py"', self.script)
        self.assertIn('"$source_tree/coverage.txt"', self.script)
        self.assertIn(
            'Test scheduling override: '
            '`0001-run-hook-free-capability-case-as-hard-failure.patch`',
            self.script,
        )

    def test_signal_patch_is_preflighted_applied_and_hashed(self) -> None:
        self.assertTrue(SIGNAL_PATCH.is_file())
        self.assertIn('if [[ ! -f $signal_patch ]]', self.script)
        self.assertIn('apply_exact_patch signal "$signal_patch"', self.script)
        self.assertIn('"$source_tree/tests/sigint-during-customize-hook"', self.script)
        self.assertIn(
            'Integration signal override: `sigint-process-group-kill-sid.patch`',
            self.script,
        )

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
