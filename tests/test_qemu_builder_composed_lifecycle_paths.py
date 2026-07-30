from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest


class QemuBuilderComposedLifecyclePathTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
        cls.patch = cls.repo / (
            "investigations/qemu-builder-composed-lifecycle/"
            "0001-compose-image-publication-and-signal-lifecycle.patch"
        )

    @staticmethod
    def extract_function(source: str, name: str) -> str:
        start = source.index(f"{name}() {{\n")
        end = source.index("\n}\n", start) + 3
        return source[start:end]

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate"
        destination = tree / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
        destination.parent.mkdir(parents=True)
        destination.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        checked = subprocess.run(
            ["sh", "-n", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination.read_text(encoding="utf-8")

    def test_existing_directory_with_trailing_slash_is_rejected_before_mktemp(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-path-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            prepare = self.extract_function(candidate, "prepare_image")
            script = root / "prepare-harness.sh"
            script.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "die() { echo \"$*\" >&2; exit 1; }\n"
                "IMAGE_TMPDIR=\n"
                "IMAGE_TMP=\n"
                "MKTEMP_LOG=$1\n"
                "IMAGE=$2\n"
                "mktemp() { printf 'called\\n' >\"$MKTEMP_LOG\"; return 99; }\n"
                + prepare
                + "\nprepare_image\n",
                encoding="utf-8",
            )
            checked = subprocess.run(
                ["sh", "-n", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            destination_directory = root / "existing"
            destination_directory.mkdir()
            log = root / "mktemp.log"
            completed = subprocess.run(
                ["sh", str(script), str(log), f"{destination_directory}/"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertIn("invalid image path", completed.stderr)
            self.assertFalse(log.exists())
            self.assertFalse((destination_directory / destination_directory.name).exists())


if __name__ == "__main__":
    unittest.main()
