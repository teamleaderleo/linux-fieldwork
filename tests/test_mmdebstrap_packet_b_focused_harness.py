from __future__ import annotations

import os
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_mmdebstrap_packet_b_focused.sh"


class PacketBFocusedHarnessTest(unittest.TestCase):
    def test_shell_syntax_and_exact_carrier_boundaries(self) -> None:
        syntax = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("validate_disposable_runtime", source)
        self.assertIn("trap '' INT TERM", source)
        self.assertIn("trap - EXIT", source)
        self.assertIn("apply_exact_patch capability", source)
        self.assertIn("apply_exact_patch installed-proxy", source)
        self.assertLess(
            source.index("apply_exact_patch capability"),
            source.index("apply_exact_patch installed-proxy"),
        )
        self.assertIn("prepare_mmdebstrap_packet_b_focused.py", source)
        self.assertIn("verify_mmdebstrap_packet_b_focused.py", source)
        self.assertIn("124|137)", source)
        self.assertIn("carrier_status=77", source)
        self.assertIn("carrier_status=$raw_status", source)
        self.assertNotIn("sourcesfilter-deb822.patch", source)
        self.assertNotIn("sigint-process-group-kill-sid.patch", source)
        self.assertNotIn("debian_bug_report", source)

    def run_check(
        self, parent: str, *, run_id: str = "focused-guard-control"
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["RUN_ID"] = run_id
        return subprocess.run(
            ["bash", str(SCRIPT), "--check-runtime-parent", parent],
            cwd=ROOT,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

    def test_safe_tmp_parent_is_accepted_without_creating_state(self) -> None:
        result = self.run_check("/tmp")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(
            pathlib.Path("/tmp/lf-mmdebstrap-packet-b-focused-guard-control").exists()
        )

    def test_unsafe_parent_is_rejected(self) -> None:
        result = self.run_check("/etc")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing unsafe runtime parent", result.stderr)

    def test_unsafe_run_id_is_rejected_before_runtime_selection(self) -> None:
        result = self.run_check("/tmp", run_id="../escape")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing unsafe run id", result.stderr)


if __name__ == "__main__":
    unittest.main()
