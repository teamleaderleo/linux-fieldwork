from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


class TarfilterTypeExcludedHardlinkPatchContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repository / "upstream/mmdebstrap/tarfilter"
        cls.integrated_patch = cls.repository / (
            "investigations/tarfilter-transform-target-scopes/"
            "tarfilter-transform-target-scopes.patch"
        )
        cls.candidate_patch = cls.repository / (
            "investigations/tarfilter-type-excluded-hardlink-target/"
            "0001-reject-hardlinks-to-type-excluded-members.patch"
        )

    def apply_exact_patch(self, root: pathlib.Path, patch: pathlib.Path) -> None:
        completed = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(patch),
            ],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertNotIn("fuzz", (completed.stdout + completed.stderr).lower())

    def test_exact_two_patch_composition_and_candidate_source(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tarfilter-type-hardlink-patch-contract-"
        ) as tmp:
            root = pathlib.Path(tmp)
            destination = root / "upstream/mmdebstrap/tarfilter"
            destination.parent.mkdir(parents=True)
            shutil.copy2(self.source, destination)

            self.apply_exact_patch(root, self.integrated_patch)
            self.apply_exact_patch(root, self.candidate_patch)

            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", str(destination)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

            source = destination.read_text(encoding="utf-8")
            self.assertIn(
                'hardlink_prefix = re.compile(r"^(?:(?:\\.\\.?/)|/)+")',
                source,
            )
            self.assertIn("type_excluded_members = set()", source)
            self.assertIn(
                '"hard-link target excluded by type filter: %s -> %s"',
                source,
            )


if __name__ == "__main__":
    unittest.main()
