from __future__ import annotations

import pathlib
import tarfile
import tempfile
import unittest

from tests import test_tarfilter_type_excluded_final_name_identity as final_identity_tests


class TarfilterTypeExcludedLinkBeforeTargetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        final_identity_tests.TarfilterTypeExcludedFinalNameIdentityTest.setUpClass()

    @staticmethod
    def helper():
        return final_identity_tests.TarfilterTypeExcludedFinalNameIdentityTest(
            methodName="runTest"
        )

    def test_later_type_excluded_target_rejects_earlier_hardlink(self) -> None:
        """A later excluded target must not leave an earlier broken hard link."""
        archive = self.helper().archive_bytes(
            (
                ("root/peer", tarfile.LNKTYPE, "root/base", b""),
                ("root/base", tarfile.REGTYPE, "", b"late-target\n"),
            )
        )

        with tempfile.TemporaryDirectory(
            prefix="tarfilter-unit16-link-before-target-"
        ) as td:
            root = pathlib.Path(td)
            helper = self.helper()

            # GNU tar cannot extract a hard link before its target exists. This
            # passing control proves that the input order is already unusable
            # and that retaining only the link after type filtering is worse,
            # not an alternate valid archive representation.
            direct, _ = helper.extract(archive, root, "direct-link-first")
            self.assertNotEqual(direct.returncode, 0)
            self.assertIn("Cannot hard link", direct.stderr)

            helper.prepare_predecessor(root)
            candidate = helper.apply_candidate(root / "candidate")
            result = helper.run_filter(
                candidate, archive, "--type-exclude=REGTYPE"
            )

            self.assertEqual(
                result.returncode,
                1,
                "a hard link was emitted before its later target was removed "
                "by the type filter",
            )
            self.assertIn(
                "hard-link target excluded by type filter: "
                "root/peer -> root/base",
                result.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(helper.member_map(result.stdout), {})
            helper.assert_empty_extract(
                result.stdout, root, "candidate-link-first-rejected"
            )


if __name__ == "__main__":
    unittest.main()
