import importlib.util
import pathlib
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "tools"
    / "mmdebstrap_autopkgtest_log.py"
)
SPEC = importlib.util.spec_from_file_location("mmdebstrap_autopkgtest_log", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MmdebstrapAutopkgtestLogTests(unittest.TestCase):
    def test_classifies_preflight_formatter_failure_before_named_tests(self):
        result = MODULE.classify_text(
            """
--- /usr/bin/mmdebstrap
+++ perltidy output
perltidy failed
testsuite FAIL non-zero exit status 1
"""
        )

        self.assertEqual(result["phase"], "coverage-preflight")
        self.assertIsNone(result["first_failed_test"])
        self.assertFalse(result["saw_named_test"])
        self.assertTrue(result["wrapper_failure_only"])

    def test_classifies_first_named_coverage_failure_with_dimensions(self):
        result = MODULE.classify_text(
            """
------------------------------------------------------------------------------
(17/329) unshare-as-root-user-inside-chroot
dist: testing
mode: unshare
variant: apt
format: auto
------------------------------------------------------------------------------
result: FAILURE
------------------------------------------------------------------------------
testsuite FAIL non-zero exit status 1
"""
        )

        self.assertEqual(result["phase"], "coverage-case")
        self.assertEqual(
            result["first_failed_test"],
            {
                "index": 17,
                "total": 329,
                "name": "unshare-as-root-user-inside-chroot",
                "dist": "testing",
                "mode": "unshare",
                "variant": "apt",
                "format": "auto",
            },
        )

    def test_success_result_is_a_negative_control_for_failure_detection(self):
        result = MODULE.classify_text(
            """
(1/329) help
dist: testing
mode: auto
variant: apt
format: auto
result: SUCCESS
testsuite PASS
"""
        )

        self.assertEqual(result["phase"], "pass")
        self.assertIsNone(result["first_failed_test"])
        self.assertFalse(result["wrapper_failure_only"])

    def test_classifies_mirror_failure_before_coverage(self):
        result = MODULE.classify_text(
            """
creating local package cache
./make_mirror.sh failed
testsuite SKIP neutral
"""
        )

        self.assertEqual(result["phase"], "mirror")
        self.assertIsNone(result["first_failed_test"])
        self.assertIn("make_mirror.sh failed", result["signals"])

    def test_ansi_and_timestamp_prefixes_do_not_hide_named_failure(self):
        result = MODULE.classify_text(
            """
2026-07-30T00:00:00Z \x1b[32m(8/329) pivot_root\x1b[0m
2026-07-30T00:00:01Z dist: testing
2026-07-30T00:00:02Z mode: unshare
2026-07-30T00:00:03Z result: FAILURE
"""
        )

        self.assertEqual(result["phase"], "coverage-case")
        self.assertEqual(result["first_failed_test"]["name"], "pivot_root")
        self.assertEqual(result["first_failed_test"]["mode"], "unshare")

    def test_first_failure_is_retained_when_later_failures_exist(self):
        result = MODULE.classify_text(
            """
(2/10) first-case
result: FAILURE
(3/10) second-case
result: FAILURE
"""
        )

        self.assertEqual(result["first_failed_test"]["name"], "first-case")
        self.assertEqual(result["last_named_test"]["name"], "second-case")

    def test_wrapper_failure_without_source_signal_remains_unknown(self):
        result = MODULE.classify_text("testsuite FAIL non-zero exit status 1\n")

        self.assertEqual(result["phase"], "unknown")
        self.assertTrue(result["wrapper_failure_only"])


if __name__ == "__main__":
    unittest.main()
