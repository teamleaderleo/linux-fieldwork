#!/usr/bin/env python3
"""Rootless stat-override value proposition control.

Run as root for the uid-drop portion. It creates a temporary file owned by
uid/gid 65534, drops permanently to that identity, then compares a physical
chown to an arbitrary unmapped identity with writing the user override xattr.
"""

import os
import tempfile

OVERRIDE = b"user.containers.override_stat"
VALUE = b"12345:12345:600"
NOBODY = 65534

fd, path = tempfile.mkstemp(dir="/tmp")
os.close(fd)
os.chown(path, NOBODY, NOBODY)

try:
    if os.geteuid() != 0:
        print("SKIP uid-drop control: run as root")
    else:
        os.setgid(NOBODY)
        os.setuid(NOBODY)
        print("running as:", os.geteuid(), os.getegid())

        try:
            os.chown(path, 12345, 12345)
            print("physical chown unexpectedly succeeded")
        except OSError as e:
            print("physical chown errno:", e.errno, e.strerror)

        os.setxattr(path, OVERRIDE, VALUE)
        print("override xattr write: OK")
        print("override xattr value:", os.getxattr(path, OVERRIDE))
        st = os.stat(path)
        print("backing owner remains:", st.st_uid, st.st_gid, oct(st.st_mode & 0o7777))
finally:
    # After permanent setuid this process may no longer be able to remove the
    # root-created path if /tmp policy forbids it. Best-effort cleanup only;
    # the normal Fieldwork invocation should wrap this in a disposable tmp dir.
    try:
        os.unlink(path)
    except OSError:
        pass
