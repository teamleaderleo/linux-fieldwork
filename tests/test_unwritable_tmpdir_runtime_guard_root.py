from __future__ import annotations

import unittest

from tests.test_unwritable_tmpdir_runtime_guard import (
    UnwritableTmpdirRuntimeGuardTest,
)


class UnwritableTmpdirRuntimeGuardRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = UnwritableTmpdirRuntimeGuardTest(methodName="runTest")
        self.leaf = "linux-fieldwork-mmdebstrap-tmpdir"

    def test_repository_root_is_rejected_with_allowed_parent(self) -> None:
        result = self.helper.run_guard(
            "/",
            "/home/tester",
            "/tmp",
            self.leaf,
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("repository root", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_home_root_is_rejected_with_allowed_parent(self) -> None:
        result = self.helper.run_guard(
            "/opt/linux-fieldwork-repository",
            "/",
            "/tmp",
            self.leaf,
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("home root", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_hosted_parent_does_not_bypass_home_root_rejection(self) -> None:
        result = self.helper.run_guard(
            "/home/runner/work/repository/repository",
            "/",
            "/home/runner/work/_temp",
            self.leaf,
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("home root", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
