from __future__ import annotations

import os
import pathlib
import tempfile
import unittest

import test_lf23_cancellation_harness_safety as safety_tests


class LF23CancellationHarnessSymlinkSafetyTest(
    safety_tests.LF23CancellationHarnessSafetyTest
):
    @staticmethod
    def writable_disposable_root() -> pathlib.Path | None:
        return next(
            (
                root
                for root in (pathlib.Path("/tmp"), pathlib.Path("/var/tmp"))
                if root.is_dir() and os.access(root, os.W_OK | os.X_OK)
            ),
            None,
        )

    def test_refuses_allowed_root_symlink_resolving_outside_disposable_roots(self) -> None:
        allowed_root = self.writable_disposable_root()
        if allowed_root is None:
            self.skipTest("no writable explicit LF-23 disposable root is available")

        with tempfile.TemporaryDirectory(prefix="lf23-symlink-target-", dir=self.repo) as unsafe_td:
            unsafe = pathlib.Path(unsafe_td)
            sentinel = unsafe / "sentinel"
            sentinel.write_text("preserve me\n")

            with tempfile.TemporaryDirectory(
                prefix="lf23-symlink-parent-", dir=allowed_root
            ) as allowed_td:
                link = pathlib.Path(allowed_td) / "output"
                link.symlink_to(unsafe, target_is_directory=True)

                completed = self.run_with_output(link)

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("output must be a child", completed.stderr)
                self.assertEqual(sentinel.read_text(), "preserve me\n")
                self.assertTrue(link.is_symlink())

    def test_refuses_output_below_ancestor_symlink_resolving_outside(self) -> None:
        allowed_root = self.writable_disposable_root()
        if allowed_root is None:
            self.skipTest("no writable explicit LF-23 disposable root is available")

        with tempfile.TemporaryDirectory(
            prefix="lf23-ancestor-target-", dir=self.repo
        ) as unsafe_td:
            unsafe = pathlib.Path(unsafe_td)
            sentinel = unsafe / "sentinel"
            sentinel.write_text("preserve me\n")

            with tempfile.TemporaryDirectory(
                prefix="lf23-ancestor-parent-", dir=allowed_root
            ) as allowed_td:
                ancestor = pathlib.Path(allowed_td) / "linked-parent"
                ancestor.symlink_to(unsafe, target_is_directory=True)
                requested = ancestor / "output"

                completed = self.run_with_output(requested)

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("output must be a child", completed.stderr)
                self.assertEqual(sentinel.read_text(), "preserve me\n")
                self.assertTrue(ancestor.is_symlink())
                self.assertFalse((unsafe / "output").exists())


if __name__ == "__main__":
    unittest.main()
