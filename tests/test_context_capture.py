from __future__ import annotations

import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture-linux-context.sh"


class ContextCaptureTest(unittest.TestCase):
    def test_default_capture_redacts_hostname(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "context.md"
            completed = subprocess.run(
                ["bash", str(SCRIPT), str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            report = output.read_text(encoding="utf-8")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("- Host: `redacted`", report)
        self.assertIn("Sensitive fields included: `no`", report)
        hostname = socket.gethostname()
        if hostname:
            self.assertNotIn(hostname, report)

    def test_help_documents_sensitive_mode(self) -> None:
        completed = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("--include-sensitive", completed.stdout)


if __name__ == "__main__":
    unittest.main()
