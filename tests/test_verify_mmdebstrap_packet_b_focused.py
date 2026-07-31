from __future__ import annotations

import unittest

from tools.verify_mmdebstrap_packet_b_focused import (
    VerificationError,
    verify_console,
)


PASSING = """\
(30/284) create-directory
 dist: unstable mode: root variant: apt format: directory
result: SUCCESS
(41/284) root-without-cap-sys-admin
 dist: unstable mode: root variant: apt format: tar
result: SUCCESS
testsuite PASS
"""


class PacketBFocusedVerificationTest(unittest.TestCase):
    def test_accepts_exact_completed_pair_and_no_other_case(self) -> None:
        receipt = verify_console(PASSING, raw_status=0)
        self.assertEqual(receipt.raw_status, 0)
        self.assertEqual(receipt.producer.name, "create-directory")
        self.assertEqual(receipt.producer.outcome, "success")
        self.assertEqual(receipt.consumer.name, "root-without-cap-sys-admin")
        self.assertEqual(receipt.consumer.outcome, "success")
        self.assertEqual(receipt.named_test_count, 2)
        self.assertEqual(receipt.later_named_tests, ())
        self.assertGreater(receipt.testsuite_pass_line, receipt.consumer.outcome_line)

    def test_rejects_nonzero_autopkgtest_status(self) -> None:
        with self.assertRaisesRegex(VerificationError, "status is not zero"):
            verify_console(PASSING, raw_status=6)

    def test_rejects_unresolved_consumer(self) -> None:
        console = """\
(30/284) create-directory
result: SUCCESS
(41/284) root-without-cap-sys-admin
testsuite PASS
"""
        with self.assertRaisesRegex(VerificationError, "consumer did not succeed"):
            verify_console(console, raw_status=0)

    def test_rejects_consumer_failure(self) -> None:
        console = PASSING.replace(
            "root-without-cap-sys-admin\n dist: unstable mode: root variant: apt format: tar\nresult: SUCCESS",
            "root-without-cap-sys-admin\n dist: unstable mode: root variant: apt format: tar\nresult: FAILURE",
        ).replace("testsuite PASS", "testsuite FAIL")
        with self.assertRaisesRegex(VerificationError, "consumer did not succeed"):
            verify_console(console, raw_status=0)

    def test_rejects_reversed_pair(self) -> None:
        console = """\
(41/284) root-without-cap-sys-admin
result: SUCCESS
(30/284) create-directory
result: SUCCESS
testsuite PASS
"""
        with self.assertRaisesRegex(VerificationError, "completed producer before"):
            verify_console(console, raw_status=0)

    def test_rejects_duplicate_producer(self) -> None:
        console = PASSING.replace(
            "(41/284) root-without-cap-sys-admin",
            "(30/284) create-directory\nresult: SUCCESS\n"
            "(41/284) root-without-cap-sys-admin",
        )
        with self.assertRaisesRegex(VerificationError, "exactly one create-directory"):
            verify_console(console, raw_status=0)

    def test_rejects_unrelated_named_case_before_producer(self) -> None:
        console = "(1/284) help\nresult: SUCCESS\n" + PASSING
        with self.assertRaisesRegex(VerificationError, "exactly two named focused tests"):
            verify_console(console, raw_status=0)

    def test_rejects_later_broad_case_even_when_it_passes(self) -> None:
        console = PASSING.replace(
            "testsuite PASS",
            "(1/284) help\nresult: SUCCESS\ntestsuite PASS",
        )
        with self.assertRaisesRegex(VerificationError, "exactly two named focused tests"):
            verify_console(console, raw_status=0)

    def test_rejects_wrapper_failure_after_success_markers(self) -> None:
        console = PASSING.replace("testsuite PASS", "testsuite FAIL")
        with self.assertRaisesRegex(VerificationError, "testsuite FAIL"):
            verify_console(console, raw_status=0)

    def test_ansi_and_compact_dimensions_are_retained(self) -> None:
        console = """\
\x1b[32m(30/284) create-directory dist: unstable mode: root variant: apt format: directory\x1b[0m
result: SUCCESS
(41/284) root-without-cap-sys-admin dist: unstable mode: root variant: apt format: tar
result: SUCCESS
testsuite PASS
"""
        receipt = verify_console(console, raw_status=0)
        self.assertEqual(receipt.producer.dimensions["format"], "directory")
        self.assertEqual(receipt.consumer.dimensions["format"], "tar")


if __name__ == "__main__":
    unittest.main()
