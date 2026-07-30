from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
BASE_PATCHES = (
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
)
REPAIR_PATCH = ROOT / (
    "investigations/mmdebstrap-file-mirror-containment/"
    "0003-reject-parent-uri-components.patch"
)


class FileMirrorAutomountParentComponentReachabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="file-mirror-parent-uri-")
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)
        self.fakebin = self.work / "fakebin"
        self.fakebin.mkdir()
        self._write_executable(
            self.fakebin / "apt-get",
            "#!/bin/sh\nprintf '%s\n' \"$FAKE_REPO_URI\"\n",
        )
        self._write_executable(
            self.fakebin / "mount",
            "#!/bin/sh\nprintf '%s\\0' \"$@\" >>\"$MOUNT_LOG\"\n",
        )

        self.predecessor = self.prepare_tree("predecessor", BASE_PATCHES)
        self.candidate = self.prepare_tree(
            "candidate", (*BASE_PATCHES, REPAIR_PATCH)
        )

    @staticmethod
    def _write_executable(path: pathlib.Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def prepare_tree(
        self, name: str, patches: tuple[pathlib.Path, ...]
    ) -> pathlib.Path:
        tree = self.work / name
        destination = tree / "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SETUP_SOURCE, destination)
        for patch in patches:
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                cwd=tree,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        checked = subprocess.run(
            ["/bin/sh", "-n", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination

    def environment(self, uri: str, mount_log: pathlib.Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fakebin}:/usr/bin:/bin",
                "FAKE_REPO_URI": uri,
                "MOUNT_LOG": str(mount_log),
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
    def fields(path: pathlib.Path) -> list[str]:
        if not path.exists():
            return []
        return [part.decode() for part in path.read_bytes().split(b"\0") if part]

    def run(
        self,
        script: pathlib.Path,
        root: pathlib.Path,
        uri: str,
        mount_log: pathlib.Path,
    ) -> subprocess.CompletedProcess[str]:
        root.mkdir()
        return subprocess.run(
            ["/bin/sh", str(script), str(root)],
            env=self.environment(uri, mount_log),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )

    def test_parent_component_predecessor_creates_an_unreachable_uri(self) -> None:
        parent = self.work / "sources"
        spelling = parent / "spelling"
        repository = parent / "repository"
        spelling.mkdir(parents=True)
        repository.mkdir()
        uri = f"file://{spelling}/../repository"

        predecessor_root = self.work / "predecessor-root"
        predecessor_log = self.work / "predecessor-mount.log"
        predecessor = self.run(
            self.predecessor,
            predecessor_root,
            uri,
            predecessor_log,
        )
        self.assertEqual(predecessor.returncode, 0, predecessor.stderr)
        normalized_target = predecessor_root.resolve() / repository.relative_to("/")
        self.assertEqual(
            self.fields(predecessor_log),
            ["-o", "ro,bind", str(repository.resolve()), str(normalized_target)],
        )
        configured_path = (
            predecessor_root
            / spelling.relative_to("/")
            / ".."
            / "repository"
        )
        self.assertFalse(configured_path.exists())

        candidate_root = self.work / "candidate-root"
        candidate_log = self.work / "candidate-mount.log"
        candidate = self.run(
            self.candidate,
            candidate_root,
            uri,
            candidate_log,
        )
        self.assertEqual(candidate.returncode, 0, candidate.stderr)
        self.assertIn("refusing unsafe file repository path", candidate.stderr)
        self.assertEqual(self.fields(candidate_log), [])
        self.assertFalse(
            (candidate_root / "run/mmdebstrap/file-mirror-automount").exists()
        )


if __name__ == "__main__":
    unittest.main()
