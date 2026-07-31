from __future__ import annotations

import pathlib
import unittest

from tools.run_fieldwork_unittests import (
    DiscoveryPolicyError,
    LOCAL_METHOD_ONLY_CLASSES,
    apply_discovery_policy,
    discover_suite,
    iter_tests,
)


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS_DIR = REPOSITORY_ROOT / "tests"
INTENTIONAL_COMPOSITION_CLASS = (
    "test_tarfilter_transform_regex_edge_cases."
    "TarfilterTransformRegexEdgeCasesTest"
)


def class_id(test: unittest.TestCase) -> str:
    test_class = type(test)
    return f"{test_class.__module__}.{test_class.__name__}"


class FieldworkUnittestDiscoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_suite = discover_suite(start_dir=TESTS_DIR)
        cls.original_tests = list(iter_tests(cls.original_suite))
        cls.filtered_suite, cls.summary = apply_discovery_policy(cls.original_suite)
        cls.filtered_tests = list(iter_tests(cls.filtered_suite))

    def test_exact_duplicate_extensions_keep_only_local_methods(self) -> None:
        expected_removed = 0

        for target in sorted(LOCAL_METHOD_ONLY_CLASSES):
            with self.subTest(target=target):
                original = [
                    test for test in self.original_tests if class_id(test) == target
                ]
                filtered = [
                    test for test in self.filtered_tests if class_id(test) == target
                ]
                self.assertTrue(original, f"target class was not discovered: {target}")

                test_class = type(original[0])
                local_names = {
                    name
                    for name, value in test_class.__dict__.items()
                    if name.startswith("test_") and callable(value)
                }
                original_names = {
                    getattr(test, "_testMethodName") for test in original
                }
                filtered_names = {
                    getattr(test, "_testMethodName") for test in filtered
                }

                self.assertGreater(len(original_names), len(local_names))
                self.assertEqual(filtered_names, local_names)
                expected_removed += len(original) - len(filtered)

        self.assertEqual(self.summary.removed, expected_removed)

    def test_intentional_tarfilter_composition_rerun_is_preserved(self) -> None:
        original = [
            test
            for test in self.original_tests
            if class_id(test) == INTENTIONAL_COMPOSITION_CLASS
        ]
        filtered = [
            test
            for test in self.filtered_tests
            if class_id(test) == INTENTIONAL_COMPOSITION_CLASS
        ]
        self.assertTrue(original)
        self.assertEqual(
            [test.id() for test in filtered],
            [test.id() for test in original],
        )

        test_class = type(original[0])
        inherited = [
            test
            for test in original
            if getattr(test, "_testMethodName") not in test_class.__dict__
        ]
        self.assertTrue(
            inherited,
            "intentional composition class no longer includes inherited contracts",
        )

    def test_non_policy_tests_are_unchanged_and_ordered(self) -> None:
        original = [
            test.id()
            for test in self.original_tests
            if class_id(test) not in LOCAL_METHOD_ONLY_CLASSES
        ]
        filtered = [
            test.id()
            for test in self.filtered_tests
            if class_id(test) not in LOCAL_METHOD_ONLY_CLASSES
        ]
        self.assertEqual(filtered, original)
        self.assertEqual(
            self.summary.discovered - self.summary.removed,
            self.summary.retained,
        )

    def test_stale_policy_class_fails_closed(self) -> None:
        class ExampleTest(unittest.TestCase):
            def test_example(self) -> None:
                pass

        suite = unittest.TestSuite((ExampleTest("test_example"),))
        with self.assertRaises(DiscoveryPolicyError):
            apply_discovery_policy(
                suite,
                policy_classes=frozenset({"missing.module.MissingTest"}),
            )


if __name__ == "__main__":
    unittest.main()
