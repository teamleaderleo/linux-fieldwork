from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from tools.reorder_mmdebstrap_hook_free_phase import (
    BROAD_MARKER,
    HOOK_MARKER,
    SOFT_MARKER,
    OrderingError,
    reorder_hook_free_phase,
)


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPOSITORY_ROOT / "tools/reorder_mmdebstrap_hook_free_phase.py"


def product_order_fixture() -> str:
    return """\
#!/bin/sh
TIMEOUT=100
# now run the script
broad-phase-body
# run hook-free tests whose failures remain authoritative for the package test
HOOK_FREE_HARD_TESTS=$(grep-dctrl --field Needs-Hook-Free-APT-Config)
CMD="mmdebstrap"
if [ "$ret" -ne 0 ]; then
    exit "$ret"
fi
TIMEOUT=90
# run only those tests that were skipped because of USE_HOST_APT_CONFIG=yes but
soft-transition-body
"""


class HookFreeIntegrationOrderTest(unittest.TestCase):
    def test_moves_exact_block_and_preserves_every_line(self) -> None:
        original = product_order_fixture()
        result = reorder_hook_free_phase(original)

        self.assertNotEqual(result.original_sha256, result.reordered_sha256)
        self.assertLess(result.text.index(HOOK_MARKER), result.text.index(BROAD_MARKER))
        self.assertLess(result.text.index(BROAD_MARKER), result.text.index(SOFT_MARKER))
        self.assertEqual(result.text.count(HOOK_MARKER), 1)
        self.assertEqual(result.text.count(BROAD_MARKER), 1)
        self.assertEqual(result.text.count(SOFT_MARKER), 1)

        original_lines = sorted(original.splitlines())
        reordered_lines = sorted(result.text.splitlines())
        self.assertEqual(reordered_lines, original_lines)
        self.assertIn('CMD="mmdebstrap"', result.text)
        self.assertIn('exit "$ret"', result.text)

    def test_missing_duplicate_and_already_reordered_boundaries_fail(self) -> None:
        original = product_order_fixture()
        cases = (
            original.replace(HOOK_MARKER, ""),
            original + HOOK_MARKER,
            original.replace(HOOK_MARKER, "")
            .replace(BROAD_MARKER, HOOK_MARKER + BROAD_MARKER),
        )
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(OrderingError):
                    reorder_hook_free_phase(source)

    def test_selector_command_and_hard_failure_contracts_are_required(self) -> None:
        original = product_order_fixture()
        cases = (
            original.replace("Needs-Hook-Free-APT-Config", "Needs-Other"),
            original.replace('CMD="mmdebstrap"', 'CMD="other"'),
            original.replace('exit "$ret"', "exit 77"),
        )
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(OrderingError):
                    reorder_hook_free_phase(source)

    def test_cli_check_is_non_mutating_and_write_mode_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "testsuite"
            original = product_order_fixture()
            path.write_text(original, encoding="utf-8")

            checked = subprocess.run(
                ["python3", str(TOOL), "--check", str(path)],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertIn(
                "integration_order=hook-free-hard,broad,soft-transition",
                checked.stdout,
            )

            written = subprocess.run(
                ["python3", str(TOOL), str(path)],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            transformed = path.read_text(encoding="utf-8")
            expected = reorder_hook_free_phase(original).text
            self.assertEqual(transformed, expected)


if __name__ == "__main__":
    unittest.main()
