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
)
SETUP_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
CLEANUP_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh"


class FileMirrorAutomountCleanupPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="file-mirror-preflight-")
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
        self.cleanup = hooks / "customize00.sh"
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(self.cleanup)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

        self.fakebin = self.work / "fakebin"
        self.fakebin.mkdir()
        self.action_log = self.work / "actions.log"
        umount = self.fakebin / "umount"
        umount.write_text(
            "#!/bin/sh\nprintf '%s\\0' \"$0\" \"$@\" >>\"$ACTION_LOG\"\n",
            encoding="utf-8",
        )
        umount.chmod(0o755)
        rm = self.fakebin / "rm"
        rm.write_text(
            "#!/bin/sh\n"
            "if [ \"${1:-}\" = -r ]; then\n"
            "    printf '%s\\0' \"$0\" \"$@\" >>\"$ACTION_LOG\"\n"
            "    exit 0\n"
            "fi\n"
            "exec /bin/rm \"$@\"\n",
            encoding="utf-8",
        )
        rm.chmod(0o755)

    def environment(self, mode: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fakebin}:/usr/bin:/bin",
                "ACTION_LOG": str(self.action_log),
                "MMDEBSTRAP_MODE": mode,
                "MMDEBSTRAP_VERBOSITY": "1",
            }
        )
        return env

    def run_cleanup(self, root: pathlib.Path, mode: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/sh", str(self.cleanup), str(root)],
            env=self.environment(mode),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )

    @staticmethod
    def marker(root: pathlib.Path) -> pathlib.Path:
        return root / "run/mmdebstrap/file-mirror-automount"

    def test_invalid_later_entry_prevents_every_cleanup_action_and_allows_rerun(self) -> None:
        invalid_entries = (
            b"../../outside",
            b"/absolute",
            b"var//cache",
            b"var/./cache",
            b"var/cache/",
        )
        for mode in ("root", "fakechroot"):
            for index, invalid in enumerate(invalid_entries):
                with self.subTest(mode=mode, invalid=invalid):
                    self.action_log.unlink(missing_ok=True)
                    root = self.work / f"root-{mode}-{index}"
                    valid_target = root / "var/cache/local mirror"
                    valid_target.mkdir(parents=True)
                    marker = self.marker(root)
                    marker.parent.mkdir(parents=True, exist_ok=True)
                    marker.write_bytes(b"var/cache/local mirror\0" + invalid + b"\0")

                    rejected = self.run_cleanup(root, mode)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(self.action_log.exists())
                    self.assertTrue(valid_target.exists())
                    self.assertTrue(marker.exists())

                    marker.write_bytes(b"var/cache/local mirror\0")
                    rerun = self.run_cleanup(root, mode)
                    self.assertEqual(rerun.returncode, 0, rerun.stderr)
                    self.assertTrue(self.action_log.exists())
                    self.assertFalse(marker.exists())

    def test_symlink_escape_after_valid_entry_prevents_every_cleanup_action(self) -> None:
        for mode in ("root", "fakechroot"):
            with self.subTest(mode=mode):
                self.action_log.unlink(missing_ok=True)
                root = self.work / f"symlink-root-{mode}"
                valid_target = root / "var/cache/valid"
                valid_target.mkdir(parents=True)
                outside = self.work / f"outside-{mode}"
                outside.mkdir()
                (root / "escape").symlink_to(outside, target_is_directory=True)
                marker = self.marker(root)
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_bytes(b"var/cache/valid\0escape/target\0")

                rejected = self.run_cleanup(root, mode)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(self.action_log.exists())
                self.assertTrue(valid_target.exists())
                self.assertEqual(list(outside.iterdir()), [])
                self.assertTrue(marker.exists())

    def test_source_runs_validation_pass_before_action_pass(self) -> None:
        source = self.cleanup.read_text(encoding="utf-8")
        validation = 'sh -c "$cleanup_entry" sh "$rootdir" validate'
        action = 'sh -c "$cleanup_entry" sh "$rootdir" "$MMDEBSTRAP_MODE"'
        self.assertIn("validate) : ;;", source)
        self.assertLess(source.index(validation), source.index(action))


if __name__ == "__main__":
    unittest.main()
