from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest


def publish_noclobber(source: Path, destination: Path) -> None:
    """Publish one same-directory name without replacing an existing entry."""

    os.link(source, destination, follow_symlinks=False)
    source.unlink()


def discard_owned_staging(staging: Path) -> None:
    """Remove only the private name created by this modeled operation."""

    staging.unlink(missing_ok=True)


def restore_after_copy_failure(
    *, staging: Path, backup: Path, destination: Path
) -> bool:
    """Return true on restoration and false when another entry owns destination."""

    discard_owned_staging(staging)
    try:
        publish_noclobber(backup, destination)
    except FileExistsError:
        return False
    return True


def publish_completed_copy(*, staging: Path, destination: Path) -> bool:
    """Publish a completed staged copy without clobbering another entry."""

    try:
        publish_noclobber(staging, destination)
    except FileExistsError:
        discard_owned_staging(staging)
        return False
    return True


class CoreutilsInstallBackupRollbackModelTests(unittest.TestCase):
    def test_copy_failure_restores_backup_when_destination_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            staging = directory / ".install-staging"
            backup = directory / "file~"
            destination = directory / "file"
            staging.write_text("partial", encoding="utf-8")
            backup.write_text("original", encoding="utf-8")

            restored = restore_after_copy_failure(
                staging=staging,
                backup=backup,
                destination=destination,
            )

            self.assertTrue(restored)
            self.assertEqual(destination.read_text(encoding="utf-8"), "original")
            self.assertFalse(staging.exists())
            self.assertFalse(backup.exists())

    def test_copy_failure_does_not_delete_concurrent_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            staging = directory / ".install-staging"
            backup = directory / "file~"
            destination = directory / "file"
            staging.write_text("partial", encoding="utf-8")
            backup.write_text("original", encoding="utf-8")
            destination.write_text("replacement", encoding="utf-8")

            restored = restore_after_copy_failure(
                staging=staging,
                backup=backup,
                destination=destination,
            )

            self.assertFalse(restored)
            self.assertEqual(destination.read_text(encoding="utf-8"), "replacement")
            self.assertEqual(backup.read_text(encoding="utf-8"), "original")
            self.assertFalse(staging.exists())

    def test_completed_staging_copy_publishes_without_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            staging = directory / ".install-staging"
            destination = directory / "file"
            staging.write_text("new", encoding="utf-8")

            with staging.open("rb") as retained_handle:
                published = publish_completed_copy(
                    staging=staging,
                    destination=destination,
                )
                retained_identity = os.fstat(retained_handle.fileno())
                destination_identity = destination.stat()

            self.assertTrue(published)
            self.assertEqual(destination.read_text(encoding="utf-8"), "new")
            self.assertFalse(staging.exists())
            self.assertEqual(retained_identity.st_dev, destination_identity.st_dev)
            self.assertEqual(retained_identity.st_ino, destination_identity.st_ino)

    def test_completed_copy_does_not_overwrite_concurrent_destination(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            staging = directory / ".install-staging"
            destination = directory / "file"
            staging.write_text("new", encoding="utf-8")
            destination.write_text("replacement", encoding="utf-8")

            published = publish_completed_copy(
                staging=staging,
                destination=destination,
            )

            self.assertFalse(published)
            self.assertEqual(destination.read_text(encoding="utf-8"), "replacement")
            self.assertFalse(staging.exists())

    def test_noclobber_publish_preserves_both_names_on_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            source = directory / "backup"
            destination = directory / "file"
            source.write_text("original", encoding="utf-8")
            destination.write_text("replacement", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                publish_noclobber(source, destination)

            self.assertEqual(source.read_text(encoding="utf-8"), "original")
            self.assertEqual(destination.read_text(encoding="utf-8"), "replacement")


if __name__ == "__main__":
    unittest.main()
