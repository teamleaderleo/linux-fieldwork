import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MMDEBSTRAP = REPO_ROOT / "upstream/mmdebstrap/mmdebstrap"
EPOCH = 1_700_000_000
OLD = EPOCH - 50_000
O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
OPEN_FLAGS = os.O_RDONLY | O_DIRECTORY
NOFOLLOW_FLAGS = OPEN_FLAGS | O_NOFOLLOW


def descriptor_identity(fd: int) -> tuple[int, int]:
    state = os.fstat(fd)
    return state.st_dev, state.st_ino


def is_currently_beneath(fd: int, root_fd: int, *, max_depth: int = 1024) -> bool:
    root_identity = descriptor_identity(root_fd)
    current = os.dup(fd)
    visited: set[tuple[int, int]] = set()
    try:
        for _ in range(max_depth):
            current_identity = descriptor_identity(current)
            if current_identity == root_identity:
                return True
            if current_identity in visited:
                return False
            visited.add(current_identity)

            parent = os.open("..", NOFOLLOW_FLAGS, dir_fd=current)
            parent_identity = descriptor_identity(parent)
            if parent_identity == current_identity:
                os.close(parent)
                return False
            os.close(current)
            current = parent
    finally:
        os.close(current)
    raise AssertionError("descriptor ancestry exceeded the bounded depth")


def set_mtime_by_descriptor(fd: int, timestamp: int) -> None:
    state = os.fstat(fd)
    os.utime(fd, (state.st_atime, timestamp))


@unittest.skipUnless(
    sys.platform.startswith("linux") and O_DIRECTORY and O_NOFOLLOW,
    "Linux directory descriptor controls are required",
)
class DirectoryMtimeAuthorityMatrixTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "root"
        self.outside = self.base / "outside"
        self.root.mkdir()
        self.outside.mkdir()
        self.root_fd = os.open(self.root, OPEN_FLAGS)
        self.addCleanup(os.close, self.root_fd)

    def create_child(self, parent: Path, name: str = "child") -> Path:
        child = parent / name
        child.mkdir()
        os.utime(child, (OLD, OLD))
        return child

    def open_child(self, child: Path) -> int:
        fd = os.open(child, NOFOLLOW_FLAGS)
        self.addCleanup(os.close, fd)
        return fd

    def test_open_time_authority_mutates_inode_after_out_of_root_rename(self) -> None:
        child = self.create_child(self.root)
        child_fd = self.open_child(child)
        moved = self.outside / "moved"
        child.rename(moved)
        child.symlink_to(self.outside, target_is_directory=True)
        outside_before = self.outside.stat().st_mtime_ns

        set_mtime_by_descriptor(child_fd, EPOCH)

        self.assertEqual(int(moved.stat().st_mtime), EPOCH)
        self.assertTrue(child.is_symlink())
        self.assertEqual(self.outside.stat().st_mtime_ns, outside_before)

    def test_current_membership_allows_unchanged_and_in_root_rename(self) -> None:
        child = self.create_child(self.root)
        child_fd = self.open_child(child)
        self.assertTrue(is_currently_beneath(child_fd, self.root_fd))

        renamed = self.root / "renamed"
        child.rename(renamed)
        self.assertTrue(is_currently_beneath(child_fd, self.root_fd))
        set_mtime_by_descriptor(child_fd, EPOCH)
        self.assertEqual(int(renamed.stat().st_mtime), EPOCH)

    def test_current_membership_rejects_out_of_root_rename(self) -> None:
        child = self.create_child(self.root)
        child_fd = self.open_child(child)
        moved = self.outside / "moved"
        child.rename(moved)

        self.assertFalse(is_currently_beneath(child_fd, self.root_fd))
        self.assertEqual(int(moved.stat().st_mtime), OLD)

    def test_current_membership_rejects_out_move_with_path_replacements(self) -> None:
        for replacement in ("symlink", "regular"):
            with self.subTest(replacement=replacement):
                parent = self.root / replacement
                parent.mkdir()
                child = self.create_child(parent)
                child_fd = self.open_child(child)
                moved = self.outside / f"moved-{replacement}"
                child.rename(moved)
                if replacement == "symlink":
                    child.symlink_to(self.outside, target_is_directory=True)
                else:
                    child.write_text("replacement\n", encoding="utf-8")
                    os.utime(child, (OLD, OLD))

                self.assertFalse(is_currently_beneath(child_fd, self.root_fd))
                self.assertEqual(int(moved.stat().st_mtime), OLD)

    def test_moved_back_inside_before_check_is_currently_owned(self) -> None:
        child = self.create_child(self.root)
        child_fd = self.open_child(child)
        moved = self.outside / "moved"
        child.rename(moved)
        self.assertFalse(is_currently_beneath(child_fd, self.root_fd))

        returned = self.root / "returned"
        moved.rename(returned)
        self.assertTrue(is_currently_beneath(child_fd, self.root_fd))
        set_mtime_by_descriptor(child_fd, EPOCH)
        self.assertEqual(int(returned.stat().st_mtime), EPOCH)

    def test_move_after_membership_check_is_residual_race(self) -> None:
        child = self.create_child(self.root)
        child_fd = self.open_child(child)
        self.assertTrue(is_currently_beneath(child_fd, self.root_fd))

        moved = self.outside / "moved-after-check"
        child.rename(moved)
        set_mtime_by_descriptor(child_fd, EPOCH)

        self.assertEqual(int(moved.stat().st_mtime), EPOCH)
        self.assertFalse(is_currently_beneath(child_fd, self.root_fd))

    def test_current_tar_boundary_uses_path_after_setup_returns(self) -> None:
        source = MMDEBSTRAP.read_text(encoding="utf-8")
        setup_index = source.index("        setup($options);")
        tar_index = source.index(
            "0 == system('tar', @taropts, '-C', $options->{root}, '.')",
            setup_index,
        )
        self.assertLess(setup_index, tar_index)
        boundary = source[setup_index:tar_index]
        self.assertIn("print $childsock (pack('n', 0) . 'adios');", boundary)
        self.assertIn("close $childsock;", boundary)
        self.assertNotIn("waitpid", boundary)
        self.assertNotIn("is_currently_beneath", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
