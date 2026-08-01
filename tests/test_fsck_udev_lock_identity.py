from __future__ import annotations

import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe-fsck-udev-lock-identity.sh"
WORKFLOW = ROOT / ".github/workflows/fsck-udev-lock-identity.yml"


class FsckUdevLockIdentityTests(unittest.TestCase):
    def test_probe_has_exact_controls_and_cleanup(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('fsck -l -t ext4 "$loopdev"', text)
        self.assertIn('FSCK_PATH="$fake_path"', text)
        self.assertIn('lockpath="/run/fsck/$loopname.lock"', text)
        self.assertIn('flock -sn "$lockpath" true', text)
        self.assertIn('flock -sn "$loopdev" true', text)
        self.assertIn('flock -x 9', text)
        self.assertIn('losetup -d "$loopdev"', text)
        self.assertIn('rm -f -- "$lockpath"', text)
        self.assertIn("This proves the lock-domain gap, not the ext4 UUID race", text)

        syntax = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_workflow_is_internal_disposable_and_evidence_retaining(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            text,
        )
        self.assertIn("investigation/fsck-udev-lock-identity", text)
        self.assertIn("docker run --privileged --rm", text)
        self.assertIn("debian:sid-slim", text)
        self.assertIn("bash scripts/probe-fsck-udev-lock-identity.sh", text)
        self.assertIn("Upload lock identity evidence", text)
        self.assertIn("retention-days: 14", text)


if __name__ == "__main__":
    unittest.main()
