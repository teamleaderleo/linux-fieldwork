from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCHES = (
    ROOT
    / (
        "investigations/mmdebstrap-file-mirror-containment/"
        "0001-contain-file-mirror-targets.patch"
    ),
    ROOT
    / (
        "investigations/mmdebstrap-file-mirror-containment/"
        "0002-preserve-file-uri-target-path.patch"
    ),
    ROOT
    / (
        "investigations/mmdebstrap-file-mirror-containment/"
        "0003-reject-parent-uri-components.patch"
    ),
)
SETUP_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
CLEANUP_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh"


class FileMirrorAutomountSourceNormalizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="file-mirror-normalize-")
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)
        self.tree = self.work / "candidate"
        hooks = self.tree / "upstream/mmdebstrap/hooks/file-mirror-automount"
        hooks.mkdir(parents=True)
        shutil.copy2(SETUP_SOURCE, hooks / "setup00.sh")
        shutil.copy2(CLEANUP_SOURCE, hooks / "customize00.sh")
        for patch in PATCHES:
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                cwd=self.tree,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.setup = hooks / "setup00.sh"

        self.fakebin = self.work / "fakebin"
        self.fakebin.mkdir()
        apt_get = self.fakebin / "apt-get"
        apt_get.write_text("#!/bin/sh\nprintf '%s\n' \"$FAKE_REPO_URI\"\n", encoding="utf-8")
        apt_get.chmod(0o755)
        mount = self.fakebin / "mount"
        mount.write_text(
            "#!/bin/sh\nprintf '%s\\0' \"$@\" >>\"$MOUNT_LOG\"\n",
            encoding="utf-8",
        )
        mount.chmod(0o755)
        self.mount_log = self.work / "mount.log"

    def environment(self, uri: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fakebin}:/usr/bin:/bin",
                "FAKE_REPO_URI": uri,
                "MOUNT_LOG": str(self.mount_log),
                "MMDEBSTRAP_APT_CONFIG": "/dev/null",
                "MMDEBSTRAP_MODE": "root",
                "MMDEBSTRAP_INCLUDE": "",
                "MMDEBSTRAP_ARGV0": "/bin/false",
                "MMDEBSTRAP_HOOK": "file-mirror-automount",
                "MMDEBSTRAP_HOOKSOCK": "9",
                "MMDEBSTRAP_VERBOSITY": "1",
            }
        )
        return env

    @staticmethod
    def nul_fields(path: pathlib.Path) -> list[str]:
        return [field.decode() for field in path.read_bytes().split(b"\0") if field]

    def test_embedded_parent_component_is_rejected_before_action(self) -> None:
        parent = self.work / "sources"
        repository = parent / "repository"
        spelling = parent / "spelling"
        repository.mkdir(parents=True)
        spelling.mkdir()
        root = self.work / "generated-root"
        root.mkdir()
        uri = f"file://{spelling}/../repository"

        result = subprocess.run(
            ["/bin/sh", str(self.setup), str(root)],
            env=self.environment(uri),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("refusing unsafe file repository path", result.stderr)
        self.assertFalse(self.mount_log.exists())
        self.assertFalse((root / "run/mmdebstrap/file-mirror-automount").exists())

    def test_dot_component_keeps_configured_path_reachable(self) -> None:
        spelling = self.work / "sources" / "spelling"
        repository = spelling / "repository"
        repository.mkdir(parents=True)
        root = self.work / "dot-root"
        root.mkdir()
        uri = f"file://{spelling}/./repository"

        result = subprocess.run(
            ["/bin/sh", str(self.setup), str(root)],
            env=self.environment(uri),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        target = root.resolve() / repository.relative_to("/")
        self.assertEqual(
            self.nul_fields(self.mount_log),
            ["-o", "ro,bind", str(repository.resolve()), str(target)],
        )
        marker = root / "run/mmdebstrap/file-mirror-automount"
        self.assertEqual(self.nul_fields(marker), [str(repository.relative_to("/"))])
        configured_path = root / spelling.relative_to("/") / "." / "repository"
        self.assertTrue(configured_path.exists())

    def test_leading_parent_traversal_remains_rejected_before_action(self) -> None:
        root = self.work / "leading-parent-root"
        root.mkdir()
        result = subprocess.run(
            ["/bin/sh", str(self.setup), str(root)],
            env=self.environment("file:///../../etc"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("refusing unsafe file repository path", result.stderr)
        self.assertFalse(self.mount_log.exists())
        self.assertFalse((root / "run/mmdebstrap/file-mirror-automount").exists())


if __name__ == "__main__":
    unittest.main()
