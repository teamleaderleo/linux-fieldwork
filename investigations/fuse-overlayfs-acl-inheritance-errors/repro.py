#!/usr/bin/env python3
"""Reduced cross-filesystem ACL inheritance failure control."""

import os
import struct
import tempfile

ACL_XATTR = "system.posix_acl_default"
ACL_XATTR_VERSION = 2
ACL_USER_OBJ = 0x01
ACL_GROUP_OBJ = 0x04
ACL_MASK = 0x10
ACL_OTHER = 0x20
ACL_UNDEFINED_ID = 0xFFFFFFFF


def entry(tag: int, perm: int, ident: int = ACL_UNDEFINED_ID) -> bytes:
    return struct.pack("<HHI", tag, perm, ident)


acl = (
    struct.pack("<I", ACL_XATTR_VERSION)
    + entry(ACL_USER_OBJ, 0o7)
    + entry(ACL_GROUP_OBJ, 0o5)
    + entry(ACL_MASK, 0o7)
    + entry(ACL_OTHER, 0o5)
)

lower_parent = tempfile.mkdtemp(dir="/tmp")
fd, upper_target = tempfile.mkstemp(dir="/dev/shm")
os.close(fd)

try:
    os.setxattr(lower_parent, ACL_XATTR, acl)
    inherited = os.getxattr(lower_parent, ACL_XATTR)
    print("lower default ACL read: OK bytes=", len(inherited))
    try:
        os.setxattr(upper_target, ACL_XATTR, inherited)
        print("upper ACL apply: OK")
    except OSError as e:
        print("upper ACL apply errno:", e.errno, e.strerror)
        print("current Rust inherit_acl outcome: success (error discarded)")
        print("pre-Rust/candidate outcome: error propagated; child not published")
finally:
    try:
        os.removexattr(lower_parent, ACL_XATTR)
    except OSError:
        pass
    os.rmdir(lower_parent)
    os.unlink(upper_target)
