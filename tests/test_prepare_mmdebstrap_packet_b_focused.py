from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.prepare_mmdebstrap_packet_b_focused import (
    BROAD_MARKER,
    HOOK_MARKER,
    SOFT_MARKER,
    STOP_BLOCK,
    PreparationError,
    prepare_focused_testsuite,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap"
CAPABILITY_PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-root-without-cap-sys-admin-hard-failure"
    / "0001-run-hook-free-capability-case-as-hard-failure.patch"
)
PROXY_PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-packet-b-focused"
    / "0001-use-installed-mmdebstrap-proxy.patch"
)


class PacketBFocusedPreparationTest(unittest.TestCase):
    def prepare_patched_source(self, root: pathlib.Path) -> pathlib.Path:
        tree = root / "source"
        for relative in (
            pathlib.Path("coverage.py"),
            pathlib.Path("coverage.txt"),
            pathlib.Path("debian/tests/testsuite"),
        ):
            destination = tree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / relative, destination)

        for patch_path in (CAPABILITY_PATCH, PROXY_PATCH):
            completed = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(patch_path),
                ],
                cwd=tree,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            output = completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, output)
            self.assertNotRegex(output.lower(), r"\b(?:fuzz|offset)\b")
        return tree

    def test_exact_imported_generation_prepares_focused_only_testsuite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="packet-b-focused-prepare-") as td:
            tree = self.prepare_patched_source(pathlib.Path(td))
            testsuite = tree / "debian/tests/testsuite"
            original = testsuite.read_text(encoding="utf-8")
            prepared, receipt = prepare_focused_testsuite(original)
            testsuite.write_text(prepared, encoding="utf-8")
            syntax = subprocess.run(
                ["sh", "-n", str(testsuite)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )

        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        self.assertEqual(
            receipt.original_order,
            ("broad", "hook-free-hard", "soft-transition"),
        )
        self.assertEqual(
            receipt.prepared_order,
            ("hook-free-hard", "focused-stop", "broad", "soft-transition"),
        )
        self.assertEqual(receipt.focused_stop_count, 1)
        self.assertNotEqual(receipt.original_sha256, receipt.prepared_sha256)
        self.assertLess(prepared.index(HOOK_MARKER), prepared.index(STOP_BLOCK))
        self.assertLess(prepared.index(STOP_BLOCK), prepared.index(BROAD_MARKER))
        self.assertLess(prepared.index(BROAD_MARKER), prepared.index(SOFT_MARKER))
        self.assertIn(
            'HOOK_FREE_HARD_TESTS="create-directory\n$HOOK_FREE_HARD_CONSUMERS"',
            prepared,
        )
        self.assertIn('CMD="mmdebstrap"', prepared)
        self.assertIn('exit "$ret"', prepared)

    def test_rejects_already_prepared_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="packet-b-focused-repeat-") as td:
            tree = self.prepare_patched_source(pathlib.Path(td))
            original = (tree / "debian/tests/testsuite").read_text(encoding="utf-8")
            prepared, _receipt = prepare_focused_testsuite(original)
        with self.assertRaisesRegex(PreparationError, "already contains"):
            prepare_focused_testsuite(prepared)

    def test_rejects_missing_exact_selector(self) -> None:
        with tempfile.TemporaryDirectory(prefix="packet-b-focused-selector-") as td:
            tree = self.prepare_patched_source(pathlib.Path(td))
            original = (tree / "debian/tests/testsuite").read_text(encoding="utf-8")
        broken = original.replace(
            'HOOK_FREE_HARD_TESTS="create-directory\n$HOOK_FREE_HARD_CONSUMERS"',
            'HOOK_FREE_HARD_TESTS="$HOOK_FREE_HARD_CONSUMERS"',
            1,
        )
        with self.assertRaisesRegex(PreparationError, "missing required fragment"):
            prepare_focused_testsuite(broken)

    def test_rejects_ambiguous_broad_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="packet-b-focused-marker-") as td:
            tree = self.prepare_patched_source(pathlib.Path(td))
            original = (tree / "debian/tests/testsuite").read_text(encoding="utf-8")
        with self.assertRaisesRegex(PreparationError, "exactly one broad phase"):
            prepare_focused_testsuite(original + BROAD_MARKER)


if __name__ == "__main__":
    unittest.main()
