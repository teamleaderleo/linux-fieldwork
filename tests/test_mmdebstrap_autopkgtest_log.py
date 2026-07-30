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
        self.assertFalse(result["wrapper_failure_only"])
        self.assertEqual(result["first_failure_signal"], "perltidy failed")

    def test_classifies_first_named_coverage_failure_with_dimensions(self):
        result = MODULE.classify_text(
            """
------------------------------------------------------------------------------
(17/329) unshare-as-root-user-inside-chroot
 dist: testing mode: unshare variant: apt format: auto
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
        self.assertFalse(result["wrapper_failure_only"])
        self.assertEqual(result["first_failure_signal"], "coverage.py reported FAILURE")

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
        self.assertIsNone(result["first_failure_line"])

    def test_classifies_mirror_failure_before_coverage(self):
        result = MODULE.classify_text(
            """
creating local package cache
./make_mirror.sh failed
testsuite FAIL non-zero exit status 77
"""
        )
        self.assertEqual(result["phase"], "mirror")
        self.assertIsNone(result["first_failed_test"])
        self.assertIn("make_mirror.sh failed", result["signals"])
        self.assertFalse(result["wrapper_failure_only"])

    def test_ansi_and_timestamp_prefixes_do_not_hide_named_failure(self):
        result = MODULE.classify_text(
            """
2026-07-30T00:00:00Z [32m(8/329) pivot_root[0m
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

    def test_earlier_mirror_failure_is_not_overridden_by_later_case(self):
        result = MODULE.classify_text(
            """
./make_mirror.sh failed
(9/10) later-case
result: FAILURE
"""
        )
        self.assertEqual(result["phase"], "mirror")
        self.assertEqual(result["first_failure_signal"], "make_mirror.sh failed")
        self.assertEqual(result["first_failed_test"]["name"], "later-case")
        self.assertLess(result["first_failure_line"], 4)

    def test_earlier_case_failure_is_not_overridden_by_later_mirror(self):
        result = MODULE.classify_text(
            """
(4/10) first-case
result: FAILURE
./make_mirror.sh failed
"""
        )
        self.assertEqual(result["phase"], "coverage-case")
        self.assertEqual(result["first_failed_test"]["name"], "first-case")
        self.assertEqual(result["first_failure_signal"], "coverage.py reported FAILURE")

    def test_earlier_preflight_failure_is_not_overridden_by_later_case(self):
        result = MODULE.classify_text(
            """
perlcritic failed
(4/10) later-case
result: FAILURE
"""
        )
        self.assertEqual(result["phase"], "coverage-preflight")
        self.assertEqual(result["first_failure_signal"], "perlcritic")
        self.assertEqual(result["first_failed_test"]["name"], "later-case")

    def test_completed_success_clears_active_test_before_stray_failure_text(self):
        result = MODULE.classify_text(
            """
(1/2) successful-case
result: SUCCESS
unrelated diagnostic contains result: FAILURE
testsuite PASS
"""
        )
        self.assertEqual(result["phase"], "pass")
        self.assertIsNone(result["first_failed_test"])
        self.assertEqual(result["last_named_test"]["name"], "successful-case")

    def test_multiple_dimensions_on_one_line_are_all_retained(self):
        result = MODULE.classify_text(
            """
(7/9) compact-case dist: testing mode: root variant: apt format: tar
result: FAILURE
"""
        )
        self.assertEqual(
            result["first_failed_test"],
            {
                "index": 7,
                "total": 9,
                "name": "compact-case",
                "dist": "testing",
                "mode": "root",
                "variant": "apt",
                "format": "tar",
            },
        )


if __name__ == "__main__":
    unittest.main()
