from __future__ import annotations

import os
import pathlib
import tarfile
import tempfile
import unittest

from tests.test_tarfilter_type_excluded_final_name_identity import (
    TarfilterTypeExcludedFinalNameIdentityTest as FinalIdentityTest,
)


class TarfilterTypeExcludedInheritedMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        FinalIdentityTest.setUpClass()

    @staticmethod
    def helper() -> FinalIdentityTest:
        return FinalIdentityTest(methodName="runTest")

    def prepare_candidate(
        self, root: pathlib.Path
    ) -> tuple[FinalIdentityTest, pathlib.Path]:
        helper = self.helper()
        helper.prepare_predecessor(root)
        source = helper.apply_candidate(root / "candidate")
        return helper, source

    def test_leading_prefix_equivalence_and_distinct_dot_prefix(self) -> None:
        equivalent_targets = (
            "./root/base",
            "/root/base",
            "../root/base",
            "../../root/base",
            ".//root/base",
            "//root/base",
        )
        with tempfile.TemporaryDirectory(
            prefix="tarfilter-unit16-prefixes-"
        ) as td:
            root = pathlib.Path(td)
            helper, candidate = self.prepare_candidate(root)

            for index, target in enumerate(equivalent_targets):
                with self.subTest(target=target):
                    archive = helper.archive_bytes(
                        (
                            (
                                "root/base",
                                tarfile.REGTYPE,
                                "",
                                b"prefix-target\n",
                            ),
                            ("root/peer", tarfile.LNKTYPE, target, b""),
                        )
                    )
                    direct, destination = helper.extract(
                        archive, root, f"direct-equivalent-{index}"
                    )
                    self.assertEqual(
                        direct.returncode, 0, direct.stdout + direct.stderr
                    )
                    self.assertEqual(
                        (destination / "root/peer").read_bytes(),
                        b"prefix-target\n",
                    )

                    rejected = helper.run_filter(
                        candidate, archive, "--type-exclude=REGTYPE"
                    )
                    self.assertEqual(rejected.returncode, 1)
                    self.assertIn(
                        f"root/peer -> {target}",
                        rejected.stderr.decode("utf-8", "replace"),
                    )
                    self.assertEqual(helper.member_map(rejected.stdout), {})

            distinct = helper.archive_bytes(
                (
                    (
                        "root/base",
                        tarfile.REGTYPE,
                        "",
                        b"distinct-target\n",
                    ),
                    (
                        "root/peer",
                        tarfile.LNKTYPE,
                        ".../root/base",
                        b"",
                    ),
                )
            )
            direct, _ = helper.extract(distinct, root, "direct-distinct")
            self.assertNotEqual(direct.returncode, 0)

            filtered = helper.run_filter(
                candidate, distinct, "--type-exclude=REGTYPE"
            )
            self.assertEqual(
                filtered.returncode,
                0,
                filtered.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                helper.member_map(filtered.stdout),
                {"root/peer": (tarfile.LNKTYPE, ".../root/base")},
            )

    def test_independent_type_filters_and_immediate_rerun(self) -> None:
        archive = self.helper().archive_bytes(
            (
                ("root/base", tarfile.REGTYPE, "", b"independent-target\n"),
                ("root/peer", tarfile.LNKTYPE, "root/base", b""),
            )
        )
        with tempfile.TemporaryDirectory(
            prefix="tarfilter-unit16-independent-"
        ) as td:
            root = pathlib.Path(td)
            helper, candidate = self.prepare_candidate(root)

            for label in ("first", "rerun"):
                result = helper.run_filter(
                    candidate,
                    archive,
                    "--type-exclude=LNKTYPE",
                    "--transform=s,^root/,,",
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stderr.decode("utf-8", "replace"),
                )
                self.assertEqual(
                    helper.member_map(result.stdout),
                    {"base": (tarfile.REGTYPE, "")},
                )
                extracted, destination = helper.extract(
                    result.stdout, root, label
                )
                self.assertEqual(
                    extracted.returncode,
                    0,
                    extracted.stdout + extracted.stderr,
                )
                self.assertEqual(
                    (destination / "base").read_bytes(),
                    b"independent-target\n",
                )

            all_removed = helper.run_filter(
                candidate,
                archive,
                "--type-exclude=REGTYPE",
                "--type-exclude=LNKTYPE",
            )
            self.assertEqual(
                all_removed.returncode,
                0,
                all_removed.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(helper.member_map(all_removed.stdout), {})

    def test_first_removed_dependency_stops_multiple_peers(self) -> None:
        archive = self.helper().archive_bytes(
            (
                ("root/base", tarfile.REGTYPE, "", b"peer-target\n"),
                ("root/peer", tarfile.LNKTYPE, "root/base", b""),
                ("root/peer2", tarfile.LNKTYPE, "root/base", b""),
            )
        )
        with tempfile.TemporaryDirectory(
            prefix="tarfilter-unit16-multiple-peers-"
        ) as td:
            helper, candidate = self.prepare_candidate(pathlib.Path(td))
            result = helper.run_filter(
                candidate, archive, "--type-exclude=REGTYPE"
            )
            self.assertEqual(result.returncode, 1)
            diagnostic = result.stderr.decode("utf-8", "replace")
            self.assertIn("root/peer -> root/base", diagnostic)
            self.assertNotIn("root/peer2 -> root/base", diagnostic)
            self.assertEqual(helper.member_map(result.stdout), {})

    def test_retained_duplicate_target_remains_available(self) -> None:
        archive = self.helper().archive_bytes(
            (
                (
                    "root/base",
                    tarfile.REGTYPE,
                    "",
                    b"retained-duplicate-target\n",
                ),
                ("root/base", tarfile.SYMTYPE, "missing", b""),
                ("root/peer", tarfile.LNKTYPE, "root/base", b""),
            )
        )
        with tempfile.TemporaryDirectory(
            prefix="tarfilter-unit16-retained-duplicate-"
        ) as td:
            root = pathlib.Path(td)
            helper, candidate = self.prepare_candidate(root)
            result = helper.run_filter(
                candidate, archive, "--type-exclude=SYMTYPE"
            )
            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                helper.member_map(result.stdout),
                {
                    "root/base": (tarfile.REGTYPE, ""),
                    "root/peer": (tarfile.LNKTYPE, "root/base"),
                },
            )
            extracted, destination = helper.extract(
                result.stdout, root, "retained-duplicate"
            )
            self.assertEqual(
                extracted.returncode, 0, extracted.stdout + extracted.stderr
            )
            self.assertEqual(
                os.stat(destination / "root/base").st_ino,
                os.stat(destination / "root/peer").st_ino,
            )


if __name__ == "__main__":
    unittest.main()
