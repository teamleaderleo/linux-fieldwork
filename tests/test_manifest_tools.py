from __future__ import annotations

import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import manifest_diff  # noqa: E402
import tar_manifest  # noqa: E402


class ManifestToolsTest(unittest.TestCase):
    def make_tar(
        self,
        path: Path,
        *,
        payload: bytes = b"hello\n",
        mtime: int = 1,
        reverse: bool = False,
    ) -> None:
        directory = tarfile.TarInfo("etc")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        directory.uid = 0
        directory.gid = 0
        directory.mtime = mtime

        file_info = tarfile.TarInfo("etc/example")
        file_info.size = len(payload)
        file_info.mode = 0o640
        file_info.uid = 1000
        file_info.gid = 1000
        file_info.mtime = mtime

        link = tarfile.TarInfo("example-link")
        link.type = tarfile.SYMTYPE
        link.linkname = "etc/example"
        link.mode = 0o777
        link.mtime = mtime

        entries = [
            (directory, None),
            (file_info, io.BytesIO(payload)),
            (link, None),
        ]
        if reverse:
            entries.reverse()

        with tarfile.open(path, "w") as archive:
            for info, stream in entries:
                archive.addfile(info, stream)

    def manifest(
        self,
        archive_path: Path,
    ) -> dict[str, dict[str, object]]:
        with tarfile.open(archive_path, "r:*") as archive:
            entries = list(tar_manifest.manifest_entries(archive))
        output = io.BytesIO()
        tar_manifest.write_manifest(entries, output)
        result: dict[str, dict[str, object]] = {}
        for line in output.getvalue().decode().splitlines():
            entry = json.loads(line)
            result[entry["path"]] = entry
        return result

    def test_records_content_and_archive_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "rootfs.tar"
            self.make_tar(archive_path)
            manifest = self.manifest(archive_path)

        self.assertEqual(manifest["etc/example"]["mode"], "0640")
        self.assertEqual(manifest["etc/example"]["uid"], 1000)
        self.assertEqual(manifest["etc/example"]["archive_index"], 1)
        self.assertEqual(
            manifest["etc/example"]["sha256"],
            "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
        )
        self.assertEqual(
            manifest["example-link"]["linkname"],
            "etc/example",
        )

    def test_pax_headers_do_not_duplicate_direct_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "pax.tar"
            with tarfile.open(
                archive_path,
                "w",
                format=tarfile.PAX_FORMAT,
            ) as archive:
                info = tarfile.TarInfo("example")
                info.size = 1
                info.mtime = 2.5
                info.pax_headers = {
                    "mtime": "2.5",
                    "SCHILY.xattr.user.test": "value",
                }
                archive.addfile(info, io.BytesIO(b"x"))
            manifest = self.manifest(archive_path)

        self.assertEqual(manifest["example"]["mtime"], 2.5)
        self.assertEqual(
            manifest["example"]["pax_headers"],
            {"SCHILY.xattr.user.test": "value"},
        )

    def test_rejects_absolute_and_parent_traversal_member_paths(self) -> None:
        for member_name in ("/etc/passwd", "../escape", "etc/../../escape"):
            with self.subTest(member_name=member_name):
                with tempfile.TemporaryDirectory() as tmp:
                    archive_path = Path(tmp) / "unsafe.tar"
                    with tarfile.open(archive_path, "w") as archive:
                        info = tarfile.TarInfo(member_name)
                        archive.addfile(info)
                    with tarfile.open(archive_path, "r:*") as archive:
                        with self.assertRaisesRegex(ValueError, "unsafe archive"):
                            list(tar_manifest.manifest_entries(archive))

    def test_preserves_exact_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "links.tar"
            with tarfile.open(archive_path, "w") as archive:
                link = tarfile.TarInfo("usr/bin/example")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../opt/example"
                archive.addfile(link)
            manifest = self.manifest(archive_path)

        self.assertEqual(
            manifest["usr/bin/example"]["linkname"],
            "../../opt/example",
        )

    def test_diff_can_ignore_timestamp_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            left_path = Path(tmp) / "left.tar"
            right_path = Path(tmp) / "right.tar"
            self.make_tar(left_path, mtime=1)
            self.make_tar(right_path, mtime=2)
            left = self.manifest(left_path)
            right = self.manifest(right_path)

        noisy = manifest_diff.compare(left, right, set())
        normalized = manifest_diff.compare(left, right, {"mtime"})
        self.assertFalse(noisy["equal"])
        self.assertTrue(normalized["equal"])

    def test_diff_detects_archive_order_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            left_path = Path(tmp) / "left.tar"
            right_path = Path(tmp) / "right.tar"
            self.make_tar(left_path)
            self.make_tar(right_path, reverse=True)
            left = self.manifest(left_path)
            right = self.manifest(right_path)

        ordered = manifest_diff.compare(left, right, set())
        content_only = manifest_diff.compare(left, right, {"archive_index"})
        self.assertFalse(ordered["equal"])
        self.assertTrue(content_only["equal"])

    def test_diff_detects_content_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            left_path = Path(tmp) / "left.tar"
            right_path = Path(tmp) / "right.tar"
            self.make_tar(left_path, payload=b"hello\n")
            self.make_tar(right_path, payload=b"goodbye\n")
            left = self.manifest(left_path)
            right = self.manifest(right_path)

        result = manifest_diff.compare(left, right, {"mtime"})
        self.assertFalse(result["equal"])
        self.assertEqual(result["summary"]["changed"], 1)
        self.assertIn("sha256", result["changed"][0]["fields"])
        self.assertIn("size", result["changed"][0]["fields"])

    def test_diff_distinguishes_missing_field_from_json_null(self) -> None:
        left = {"example": {"path": "example"}}
        right = {"example": {"path": "example", "optional": None}}

        result = manifest_diff.compare(left, right, set())

        self.assertFalse(result["equal"])
        self.assertEqual(result["changed"][0]["fields"], ["optional"])
        self.assertEqual(
            result["changed"][0]["left"]["optional"],
            {"present": False},
        )
        self.assertEqual(
            result["changed"][0]["right"]["optional"],
            {"present": True, "value": None},
        )


if __name__ == "__main__":
    unittest.main()
