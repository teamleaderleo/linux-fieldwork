from __future__ import annotations

import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest


class QemuBuilderAtomicImageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        cls.patch = cls.repo / (
            "investigations/qemu-builder-atomic-image/"
            "0001-publish-image-atomically.patch"
        )

    def prepare_candidate(self, root: pathlib.Path) -> pathlib.Path:
        tree = root / "candidate"
        destination = tree / "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        destination.parent.mkdir(parents=True)
        shutil.copy2(self.source, destination)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return destination

    @staticmethod
    def helper_blocks(source: str) -> tuple[str, str]:
        helper_start = source.index("WORKDIR=\n")
        helper_end = source.index("\ncleanup() {", helper_start)
        helpers = source[helper_start:helper_end] + "\n"
        cleanup_start = helper_end + 1
        cleanup_end = source.index("\n}\n\ntrap ", cleanup_start) + len("\n}\n")
        cleanup = source[cleanup_start:cleanup_end]
        return helpers, cleanup

    def write_harness(self, root: pathlib.Path, candidate: pathlib.Path) -> pathlib.Path:
        helpers, cleanup = self.helper_blocks(candidate.read_text(encoding="utf-8"))
        script = root / "harness.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "die() { echo \"$*\" >&2; exit 1; }\n"
            "mode=$1\n"
            "IMAGE=$2\n"
            "umask 022\n"
            + helpers
            + cleanup
            + "trap cleanup EXIT INT TERM QUIT\n"
            + "prepare_image\n"
            + "case $mode in\n"
            + "  fail) printf 'partial' >\"$IMAGE_TMP\"; exit 7 ;;\n"
            + "  success) printf 'complete-image' >\"$IMAGE_TMP\"; publish_image ;;\n"
            + "  *) die \"unknown mode: $mode\" ;;\n"
            + "esac\n",
            encoding="utf-8",
        )
        return script

    @staticmethod
    def temporary_siblings(image: pathlib.Path) -> list[pathlib.Path]:
        return sorted(image.parent.glob(f".{image.name}.mmdebstrap.*"))

    def test_failure_preserves_existing_image_and_removes_temporary_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-atomic-existing-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            harness = self.write_harness(root, candidate)
            image = root / "existing.img"
            image.write_bytes(b"trusted-existing-image")
            original_mode = stat.S_IMODE(image.stat().st_mode)

            result = subprocess.run(
                ["/bin/sh", str(harness), "fail", str(image)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertEqual(image.read_bytes(), b"trusted-existing-image")
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), original_mode)
            self.assertEqual(self.temporary_siblings(image), [])

    def test_failure_keeps_absent_output_absent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-atomic-absent-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            harness = self.write_harness(root, candidate)
            image = root / "absent.img"

            result = subprocess.run(
                ["/bin/sh", str(harness), "fail", str(image)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertFalse(image.exists())
            self.assertEqual(self.temporary_siblings(image), [])

    def test_success_publishes_complete_image_with_normal_creation_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-atomic-success-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            harness = self.write_harness(root, candidate)
            image = root / "result.img"
            image.write_bytes(b"old-image")

            result = subprocess.run(
                ["/bin/sh", str(harness), "success", str(image)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(image.read_bytes(), b"complete-image")
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), 0o644)
            self.assertEqual(self.temporary_siblings(image), [])

    def test_success_replaces_final_symlink_without_overwriting_referent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-atomic-symlink-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            harness = self.write_harness(root, candidate)
            referent = root / "referent.img"
            referent.write_bytes(b"trusted-referent")
            image = root / "result.img"
            image.symlink_to(referent.name)

            result = subprocess.run(
                ["/bin/sh", str(harness), "success", str(image)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(image.is_symlink())
            self.assertEqual(image.read_bytes(), b"complete-image")
            self.assertEqual(referent.read_bytes(), b"trusted-referent")
            self.assertEqual(self.temporary_siblings(image), [])

    def test_every_image_mutation_uses_temporary_path_before_one_publication(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-atomic-source-") as tmp:
            candidate = self.prepare_candidate(pathlib.Path(tmp))
            source = candidate.read_text(encoding="utf-8")
            self.assertIn('"$IMAGE_TMP" "$SIZE"', source)
            self.assertIn('truncate --size="+$((34 * 512))" "$IMAGE_TMP"', source)
            self.assertIn('/sbin/sfdisk "$IMAGE_TMP"', source)
            self.assertIn('of="$IMAGE_TMP"', source)
            self.assertEqual(source.count("publish_image\n"), 1)
            self.assertLess(source.index("publish_image\n"), source.index("I: SUCCESS!"))
            self.assertIn('mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"', source)


if __name__ == "__main__":
    unittest.main()
