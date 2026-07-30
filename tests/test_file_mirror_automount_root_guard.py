from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


class FileMirrorAutomountRootGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-file-mirror-containment/"
            "0001-contain-file-mirror-targets.patch"
        )
        cls.setup_source = cls.repo / (
            "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
        )
        cls.cleanup_source = cls.repo / (
            "upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh"
        )

    def prepare_candidate(self, root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        tree = root / "candidate"
        hooks = tree / "upstream/mmdebstrap/hooks/file-mirror-automount"
        hooks.mkdir(parents=True)
        shutil.copy2(self.setup_source, hooks / "setup00.sh")
        shutil.copy2(self.cleanup_source, hooks / "customize00.sh")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        for script in (hooks / "setup00.sh", hooks / "customize00.sh"):
            syntax = subprocess.run(
                ["/bin/sh", "-n", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return hooks / "setup00.sh", hooks / "customize00.sh"

    @staticmethod
    def write_fake(path: pathlib.Path) -> None:
        path.write_text(
            "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >>\"$ACTION_LOG\"\nexit 97\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def environment(self, fakebin: pathlib.Path, action_log: pathlib.Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fakebin}:/usr/bin:/bin",
                "ACTION_LOG": str(action_log),
                "MMDEBSTRAP_APT_CONFIG": "/dev/null",
                "MMDEBSTRAP_MODE": "fakechroot",
                "MMDEBSTRAP_INCLUDE": "",
                "MMDEBSTRAP_ARGV0": "/bin/false",
                "MMDEBSTRAP_HOOK": "file-mirror-automount",
                "MMDEBSTRAP_HOOKSOCK": "9",
                "MMDEBSTRAP_VERBOSITY": "1",
            }
        )
        return env

    def test_literal_and_symlinked_filesystem_root_are_refused_before_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="file-mirror-root-guard-") as tmp:
            root = pathlib.Path(tmp)
            setup, cleanup = self.prepare_candidate(root)
            fakebin = root / "fakebin"
            fakebin.mkdir()
            for command in ("apt-get", "mount", "umount", "rm", "xargs"):
                self.write_fake(fakebin / command)
            action_log = root / "actions.log"
            root_link = root / "root-link"
            root_link.symlink_to("/", target_is_directory=True)

            for script in (setup, cleanup):
                for selected_root in (pathlib.Path("/"), root_link):
                    with self.subTest(script=script.name, root=str(selected_root)):
                        result = subprocess.run(
                            ["/bin/sh", str(script), str(selected_root)],
                            env=self.environment(fakebin, action_log),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=10,
                        )
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(
                            "refusing filesystem root as generated root", result.stderr
                        )
                        self.assertFalse(action_log.exists())

    def test_source_guard_precedes_marker_and_repository_processing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="file-mirror-root-source-") as tmp:
            setup, cleanup = self.prepare_candidate(pathlib.Path(tmp))
            setup_text = setup.read_text(encoding="utf-8")
            cleanup_text = cleanup.read_text(encoding="utf-8")
            guard = 'case "$rootdir" in\n\t/) echo "E: refusing filesystem root'
            self.assertIn(guard, setup_text)
            self.assertIn(guard, cleanup_text)
            self.assertLess(setup_text.index(guard), setup_text.index("apt-get indextargets"))
            self.assertLess(cleanup_text.index(guard), cleanup_text.index("marker="))


if __name__ == "__main__":
    unittest.main()
