from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
CUSTOMIZE_SOURCE = ROOT / "upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh"
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


class FileMirrorAutomountContainmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="file-mirror-containment-")
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)
        self.fakebin = self.work / "fakebin"
        self.fakebin.mkdir()
        self.mount_log = self.work / "mount.log"
        self.umount_log = self.work / "umount.log"
        self._write_executable(
            self.fakebin / "apt-get",
            "#!/bin/sh\nprintf '%s\\n' \"${FAKE_REPO_URIS:-}\"\n",
        )
        self._write_executable(
            self.fakebin / "mount",
            "#!/bin/sh\nprintf '%s\\0' \"$@\" >> \"$FAKE_MOUNT_LOG\"\n",
        )
        self._write_executable(
            self.fakebin / "umount",
            "#!/bin/sh\nprintf '%s\\0' \"$@\" >> \"$FAKE_UMOUNT_LOG\"\n",
        )

        self.baseline_root = self.work / "baseline-tree"
        self.candidate_root = self.work / "candidate-tree"
        for tree in (self.baseline_root, self.candidate_root):
            hooks = tree / "upstream/mmdebstrap/hooks/file-mirror-automount"
            hooks.mkdir(parents=True)
            shutil.copy2(SETUP_SOURCE, hooks / "setup00.sh")
            shutil.copy2(CUSTOMIZE_SOURCE, hooks / "customize00.sh")
        for patch in PATCHES:
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                cwd=self.candidate_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

        self.baseline_setup = self.baseline_root / (
            "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
        )
        self.candidate_setup = self.candidate_root / (
            "upstream/mmdebstrap/hooks/file-mirror-automount/setup00.sh"
        )
        self.candidate_customize = self.candidate_root / (
            "upstream/mmdebstrap/hooks/file-mirror-automount/customize00.sh"
        )

    @staticmethod
    def _write_executable(path: pathlib.Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def env(self, *, uris: str = "", include: str = "", mode: str = "root") -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fakebin}:{env['PATH']}",
                "FAKE_REPO_URIS": uris,
                "FAKE_MOUNT_LOG": str(self.mount_log),
                "FAKE_UMOUNT_LOG": str(self.umount_log),
                "MMDEBSTRAP_APT_CONFIG": "/dev/null",
                "MMDEBSTRAP_MODE": mode,
                "MMDEBSTRAP_INCLUDE": include,
                "MMDEBSTRAP_ARGV0": "/bin/true",
                "MMDEBSTRAP_HOOK": "file-mirror-automount",
                "MMDEBSTRAP_HOOKSOCK": "9",
                "MMDEBSTRAP_VERBOSITY": "1",
            }
        )
        return env

    @staticmethod
    def nul_fields(path: pathlib.Path) -> list[str]:
        if not path.exists():
            return []
        return [field.decode() for field in path.read_bytes().split(b"\0") if field]

    def run_hook(
        self,
        script: pathlib.Path,
        root: pathlib.Path,
        *,
        uris: str = "",
        include: str = "",
        mode: str = "root",
    ) -> subprocess.CompletedProcess[str]:
        root.mkdir(parents=True, exist_ok=True)
        return subprocess.run(
            ["sh", str(script), str(root)],
            env=self.env(uris=uris, include=include, mode=mode),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )

    def test_baseline_traversal_targets_outside_generated_root(self) -> None:
        root = self.work / "negative" / "a" / "b" / "root"
        result = self.run_hook(
            self.baseline_setup,
            root,
            uris="file:///../../etc",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = self.nul_fields(self.mount_log)
        self.assertEqual(fields[:2], ["-o", "ro,bind"])
        self.assertEqual(fields[2], "/../../etc")
        self.assertEqual(fields[3], str(root / "../../etc"))
        self.assertTrue((self.work / "negative" / "a" / "etc").is_dir())

    def test_candidate_rejects_repository_traversal_before_side_effects(self) -> None:
        root = self.work / "candidate-negative" / "a" / "b" / "root"
        result = self.run_hook(
            self.candidate_setup,
            root,
            uris="file:///../../etc",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("refusing unsafe file repository path", result.stderr)
        self.assertEqual(self.nul_fields(self.mount_log), [])
        self.assertFalse((self.work / "candidate-negative" / "a" / "etc").exists())
        self.assertFalse((root / "run/mmdebstrap/file-mirror-automount").exists())

    def test_candidate_maps_valid_repository_below_root_and_records_relative_marker(self) -> None:
        source = self.work / "repository"
        source.mkdir()
        root = self.work / "valid-root"
        result = self.run_hook(
            self.candidate_setup,
            root,
            uris=f"file://{source}",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        canonical_source = source.resolve()
        target = root.resolve() / source.relative_to("/")
        self.assertTrue(target.is_dir())
        fields = self.nul_fields(self.mount_log)
        self.assertEqual(fields, ["-o", "ro,bind", str(canonical_source), str(target)])
        marker = root / "run/mmdebstrap/file-mirror-automount"
        entries = self.nul_fields(marker)
        self.assertEqual(entries, [str(source.relative_to("/"))])
        self.assertNotIn("..", pathlib.PurePosixPath(entries[0]).parts)
        self.assertFalse(entries[0].startswith("/"))

    def test_symlinked_repository_keeps_configured_uri_path_reachable(self) -> None:
        canonical_source = self.work / "canonical-repository"
        canonical_source.mkdir()
        source_uri_path = self.work / "repository-link"
        source_uri_path.symlink_to(canonical_source, target_is_directory=True)
        root = self.work / "symlink-source-root"

        result = self.run_hook(
            self.candidate_setup,
            root,
            uris=f"file://{source_uri_path}",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        target = root.resolve() / source_uri_path.relative_to("/")
        self.assertTrue(target.is_dir())
        self.assertEqual(
            self.nul_fields(self.mount_log),
            ["-o", "ro,bind", str(canonical_source.resolve()), str(target)],
        )
        marker = root / "run/mmdebstrap/file-mirror-automount"
        self.assertEqual(self.nul_fields(marker), [str(source_uri_path.relative_to("/"))])

        cleaned = self.run_hook(self.candidate_customize, root)
        self.assertEqual(cleaned.returncode, 0, cleaned.stderr)
        self.assertEqual(self.nul_fields(self.umount_log), [str(target)])
        self.assertFalse(marker.exists())

        rerun = self.run_hook(self.candidate_customize, root)
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(self.nul_fields(self.umount_log), [str(target)])

    def test_candidate_rejects_symlinked_target_parent_escape(self) -> None:
        source = self.work / "symlink-source"
        source.mkdir()
        root = self.work / "symlink-root"
        outside = self.work / "outside-target"
        root.mkdir()
        outside.mkdir()
        first_component = source.relative_to("/").parts[0]
        (root / first_component).symlink_to(outside, target_is_directory=True)
        result = self.run_hook(
            self.candidate_setup,
            root,
            uris=f"file://{source}",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("outside generated root", result.stderr)
        self.assertEqual(self.nul_fields(self.mount_log), [])
        self.assertEqual(list(outside.iterdir()), [])

    def test_candidate_contains_local_package_destination(self) -> None:
        package = self.work / "package.deb"
        package.write_bytes(b"package")
        root = self.work / "package-root"
        result = self.run_hook(
            self.candidate_setup,
            root,
            include=str(package),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        target = root.resolve() / package.resolve().relative_to("/")
        self.assertTrue(target.is_file())
        fields = self.nul_fields(self.mount_log)
        self.assertEqual(fields, ["-o", "bind", str(package.resolve()), str(target)])
        marker = root / "run/mmdebstrap/file-mirror-automount"
        self.assertEqual(self.nul_fields(marker), [str(package.resolve().relative_to("/"))])

    def test_cleanup_uses_only_canonical_contained_marker_entry(self) -> None:
        root = self.work / "cleanup-root"
        target = root / "var/cache/local"
        target.mkdir(parents=True)
        marker = root / "run/mmdebstrap/file-mirror-automount"
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b"var/cache/local\0")
        result = self.run_hook(self.candidate_customize, root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.nul_fields(self.umount_log), [str(target.resolve())])
        self.assertFalse(marker.exists())

    def test_cleanup_rejects_traversing_and_symlink_escaping_markers(self) -> None:
        for label, entry in (
            ("traversal", "../../outside"),
            ("symlink", "var/cache/local"),
        ):
            with self.subTest(label=label):
                self.umount_log.unlink(missing_ok=True)
                root = self.work / f"cleanup-{label}-root"
                root.mkdir()
                if label == "symlink":
                    outside = self.work / "cleanup-outside"
                    outside.mkdir(exist_ok=True)
                    (root / "var").symlink_to(outside, target_is_directory=True)
                marker = root / "run/mmdebstrap/file-mirror-automount"
                marker.parent.mkdir(parents=True)
                marker.write_bytes(entry.encode() + b"\0")
                result = self.run_hook(self.candidate_customize, root)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.nul_fields(self.umount_log), [])
                self.assertTrue(marker.exists())

    def test_candidate_source_contract(self) -> None:
        setup = self.candidate_setup.read_text(encoding="utf-8")
        customize = self.candidate_customize.read_text(encoding="utf-8")
        self.assertIn('rootdir="$(realpath -e -- "$1")"', setup)
        self.assertIn('normalized_target="$(realpath -m -s -- "$target_source")"', setup)
        self.assertIn('canonical_target="$(realpath -m -- "$rootdir/$target_relative")"', setup)
        self.assertIn('resolve_contained_target "/$path" "/$path"', setup)
        self.assertIn('printf \'%s\\0\' "$target_relative"', setup)
        self.assertIn('target=$(realpath -m -- "$rootdir/$entry")', customize)
        self.assertIn('rm -r "$target"', customize)
        self.assertIn('umount "$target"', customize)


if __name__ == "__main__":
    unittest.main()
