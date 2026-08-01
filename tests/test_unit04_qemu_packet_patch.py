from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


class Unit04QemuPacketPatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.unit = cls.repo / (
            "upstream-packets/units/04-qemu-image-builder-lifecycle"
        )
        cls.source = cls.repo / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
        cls.patch = cls.unit / (
            "patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch"
        )
        cls.model = cls.unit / "scripts/verify_lifecycle_model.py"

    def test_patch_uses_upstream_root_paths_and_full_file_coordinates(self) -> None:
        patch = self.patch.read_text(encoding="utf-8")
        self.assertIn(
            "diff --git a/mmdebstrap-autopkgtest-build-qemu "
            "b/mmdebstrap-autopkgtest-build-qemu",
            patch,
        )
        self.assertNotIn("a/upstream/mmdebstrap/", patch)
        self.assertNotIn("@@ -1,12 +1,78 @@", patch)
        for header in (
            "@@ -318,12 +318,78 @@",
            "@@ -406,7 +472,7 @@",
            "@@ -465,8 +531,8 @@",
            "@@ -474,7 +540,7 @@",
            "@@ -483,5 +549,7 @@",
        ):
            self.assertIn(header, patch)

    def test_exact_imported_source_application_has_no_offset_or_fuzz(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unit04-exact-apply-") as tmp:
            root = pathlib.Path(tmp)
            destination = root / "mmdebstrap-autopkgtest-build-qemu"
            shutil.copy2(self.source, destination)
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-i",
                    str(self.patch),
                ],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            transcript = applied.stdout + applied.stderr
            self.assertEqual(applied.returncode, 0, transcript)
            self.assertNotIn("offset", transcript.lower(), transcript)
            self.assertNotIn("fuzz", transcript.lower(), transcript)

            checked = subprocess.run(
                ["sh", "-n", str(destination)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            candidate = destination.read_text(encoding="utf-8")
            for item in (
                'set -- "$@" -E "$EXTOPTS" "$IMAGE_TMP" "$SIZE"',
                'truncate --size="+$((34 * 512))" "$IMAGE_TMP"',
                '/sbin/sfdisk "$IMAGE_TMP" <<EOF',
                'dd if="$WORKDIR/fat" of="$IMAGE_TMP"',
                "trap exit_cleanup EXIT",
                "trap 'signal_exit 129' HUP",
                "trap 'signal_exit 130' INT",
                "trap 'signal_exit 131' QUIT",
                "trap 'signal_exit 143' TERM",
            ):
                self.assertIn(item, candidate)
            self.assertEqual(
                candidate.count('mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"'),
                1,
            )

    def test_repaired_lifecycle_model_passes(self) -> None:
        completed = subprocess.run(
            ["python", str(self.model)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Ran 3 tests", completed.stderr)
        self.assertIn("OK", completed.stderr)


if __name__ == "__main__":
    unittest.main()
