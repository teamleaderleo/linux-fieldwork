#!/usr/bin/env python3
"""Model persisted stat-override mode detection across layer reuse."""

import os
import tempfile

XATTR = b"user.containers.override_stat"
ROOT_MARKER = b"0:0:555"
CHILD_OVERRIDE = b"12345:12345:600"


def detect_mode(root: bytes) -> str:
    try:
        os.getxattr(root, XATTR)
        return "Containers"
    except OSError:
        return "None"


with tempfile.TemporaryDirectory(dir="/tmp") as root_s:
    root = os.fsencode(root_s)
    child = root + b"/child"
    fd = os.open(child, os.O_CREAT | os.O_WRONLY, 0o644)
    os.close(fd)
    os.setxattr(child, XATTR, CHILD_OVERRIDE)

    print("child override present:", os.getxattr(child, XATTR))
    print("mode detected without root marker:", detect_mode(root))
    print("current later-lower interpretation: backing stat; child override not consulted")

    os.setxattr(root, XATTR, ROOT_MARKER)
    print("mode detected with old-style root marker:", detect_mode(root))
    print("old/candidate later-lower interpretation: child logical override eligible")
