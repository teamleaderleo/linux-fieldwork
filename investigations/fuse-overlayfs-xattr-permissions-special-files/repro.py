#!/usr/bin/env python3
"""Reduced special-file stat-override reachability model."""

S_IFIFO = 0o010000
S_IFREG = 0o100000
S_IFDIR = 0o040000
S_IFMT = 0o170000


def current_override(st_mode: int, override_mode: int) -> int:
    """Current production gate: special files return before xattr parsing."""
    file_type = st_mode & S_IFMT
    if file_type not in (S_IFREG, S_IFDIR):
        return st_mode
    return (st_mode & S_IFMT) | override_mode


def candidate_override(st_mode: int, override_mode: int, override_type: int) -> int:
    return override_type | override_mode


backing = S_IFIFO | 0o755
logical = 0o600
print("backing FIFO mode:", oct(backing))
print("current getattr after override xattr 0:0:600:pipe:", oct(current_override(backing, logical)))
print("candidate/old logical mode:", oct(candidate_override(backing, logical, S_IFIFO)))

# Default xattr_permissions=0 control: backing mode should not be widened.
requested = S_IFIFO | 0o600
current_backing_default = requested | 0o755
old_default = requested
print("default xattr_permissions current mknod backing:", oct(current_backing_default))
print("default xattr_permissions old/candidate backing:", oct(old_default))
