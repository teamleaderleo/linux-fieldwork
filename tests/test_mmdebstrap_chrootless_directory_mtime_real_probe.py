from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROBE = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime/real_metadata_probe.sh"
)
WORKFLOW = (
    REPOSITORY_ROOT
    / ".github/workflows/mmdebstrap-chrootless-directory-mtime.yml"
)


class ChrootlessDirectoryMtimeRealProbeContractTest(unittest.TestCase):
    def test_probe_shell_syntax(self) -> None:
        completed = subprocess.run(
            ["bash", "-n", str(PROBE)],
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_cleanup_never_recursively_removes_an_active_mount(self) -> None:
        source = PROBE.read_text(encoding="utf-8")
        cleanup = source[
            source.index("cleanup() {") : source.index("on_signal() {")
        ]

        unmount = cleanup.index('sudo umount "$mount_dir"')
        recheck = cleanup.index('mountpoint -q "$mount_dir"', unmount)
        nonzero = cleanup.index(
            "[[ $cleanup_status -ne 0 ]] || cleanup_status=1",
            recheck,
        )
        refusal = cleanup.index(
            "refusing recursive cleanup while mount is still active",
            nonzero,
        )
        stop = cleanup.index("return", refusal)
        removal = cleanup.index('rm -rf "$runtime"', stop)
        self.assertLess(unmount, recheck)
        self.assertLess(recheck, nonzero)
        self.assertLess(nonzero, refusal)
        self.assertLess(refusal, stop)
        self.assertLess(stop, removal)

        self.assertIn("trap cleanup EXIT", source)
        self.assertIn("trap 'on_signal 130' INT", source)
        self.assertIn("trap 'on_signal 143' TERM", source)
        self.assertIn("trap - EXIT INT TERM\ncleanup", source)

    def test_runtime_authority_preserves_hosted_temp_without_weakening_repo_guard(
        self,
    ) -> None:
        source = PROBE.read_text(encoding="utf-8")
        self.assertIn(
            "/home/runner/work/_temp|/home/runner/work/_temp/*",
            source,
        )
        self.assertIn(
            'runtime="$runtime_parent/mmdebstrap-chrootless-directory-mtime-real"',
            source,
        )
        self.assertIn('if [[ -L "$runtime" ]]; then', source)
        self.assertIn("refusing symlink runtime leaf", source)
        self.assertIn('runtime_canonical="$(realpath -m "$runtime")"', source)
        self.assertNotIn(
            'runtime="$(realpath -m "$runtime_parent/mmdebstrap-chrootless-directory-mtime-real")"',
            source,
        )
        self.assertIn("refusing runtime inside repository", source)
        self.assertIn("refusing runtime containing repository", source)
        self.assertIn("refusing runtime containing home", source)
        self.assertIn("refusing unbounded protected root", source)

        validation_end = source.index("result_dir=")
        stale_guard = source.index("refusing stale mount before runtime reset")
        first_recursive_removal = source.index('rm -rf "$runtime"', stale_guard)
        self.assertGreater(stale_guard, validation_end)
        self.assertLess(stale_guard, first_recursive_removal)

    def test_symlink_runtime_leaf_is_rejected_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="lf-real-metadata-parent-", dir="/tmp"
        ) as parent_name:
            parent = pathlib.Path(parent_name)
            target = parent / "protected-target"
            target.mkdir()
            sentinel = target / "sentinel"
            sentinel.write_text("preserve\n", encoding="utf-8")
            runtime = parent / "mmdebstrap-chrootless-directory-mtime-real"
            runtime.symlink_to(target, target_is_directory=True)

            environment = os.environ.copy()
            environment["RUNNER_TEMP"] = str(parent)
            result = subprocess.run(
                ["bash", str(PROBE), "--check-runtime-parent"],
                cwd=REPOSITORY_ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing symlink runtime leaf", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue(runtime.is_symlink())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")

    def test_probe_preserves_real_metadata_and_device_boundaries(self) -> None:
        source = PROBE.read_text(encoding="utf-8")
        required = (
            'sudo mount -t tmpfs -o size=1m,mode=0755 tmpfs "$mount_dir"',
            'root_device="$(stat -c \'%d\' "$tree")"',
            'mount_device="$(stat -c \'%d\' "$mount_dir")"',
            '[[ "$root_device" != "$mount_device" ]]',
            "from test_mmdebstrap_chrootless_directory_mtime import normalize_directory_mtimes",
            "normalize_directory_mtimes(tree, timestamp)",
            'acl_before="$(getfacl -cp "$tree/acl-directory" "$acl_file")"',
            'cap_before="$(getcap -n "$cap_file")"',
            '[[ "$acl_after" == "$acl_before" ]]',
            '[[ "$cap_after" == "$cap_before" ]]',
            "foreign_sentinel_preserved=yes",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, source)

        timestamp_setup = source.index('touch -h --date="@$old_timestamp"')
        capability_setup = source.index(
            "sudo setcap cap_net_bind_service=ep",
            timestamp_setup,
        )
        capability_receipt = source.index("cap_before=", capability_setup)
        self.assertLess(timestamp_setup, capability_setup)
        self.assertLess(capability_setup, capability_receipt)

    def test_workflow_requires_owned_exact_branch_before_privilege(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        job_start = source.index("  real-metadata-boundaries:\n")
        checkout = source.index("      - name: Check out proposed repository state")
        guard = source[job_start:checkout]
        self.assertIn("github.event_name == 'pull_request'", guard)
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            guard,
        )
        for branch in (
            "repair/chrootless-dir-mtime-real-boundaries-v2",
            "candidate/chrootless-directory-mtime-normalization-v3",
        ):
            with self.subTest(branch=branch):
                self.assertIn(f"github.head_ref == '{branch}'", guard)
        self.assertIn("||", guard)
        self.assertNotIn("startsWith", guard)
        self.assertLess(guard.index("if: >-"), guard.index("runs-on:"))
        self.assertEqual(source.count("sudo mount -t tmpfs"), 0)
        self.assertEqual(PROBE.read_text(encoding="utf-8").count("sudo mount -t tmpfs"), 1)

    def test_workflow_runs_candidate_rerun_and_retains_receipts_read_only(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", source)
        self.assertIn(
            "sudo apt-get install --yes acl libcap2-bin perltidy",
            source,
        )
        self.assertIn(
            "tests/test_mmdebstrap_chrootless_directory_mtime_candidate.py -v",
            source,
        )
        self.assertIn("for label in first rerun; do", source)
        self.assertIn('test ! -e "$runtime"', source)
        self.assertIn('findmnt -rn -M "$runtime/tree/foreign-device"', source)
        self.assertIn("acl_preserved=yes", source)
        self.assertIn("capability_preserved=yes", source)
        self.assertIn("actions/upload-artifact@v4", source)
        self.assertIn("real-boundary-results/", source)


if __name__ == "__main__":
    unittest.main()
