#!/usr/bin/env python3

"""Reduce crun's propagation-fallback target-identity question.

Run inside a disposable user+mount namespace, for example:

    unshare -Urnm sh -c 'mount --make-rprivate / && python3 probe.py'

The script creates one mount, opens an O_PATH fd to it, overmounts the same
path, reopens it, and then applies a propagation change first through the old
pre-overmount fd and then through the reopened fd. Mount IDs from fdinfo are
the oracle.
"""

import ctypes
import os
import tempfile

libc = ctypes.CDLL(None, use_errno=True)
libc.mount.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
]

MS_PRIVATE = 1 << 18
MS_SHARED = 1 << 20
O_PATH = getattr(os, "O_PATH", 0o10000000)


def _bytes(value):
    return None if value is None else os.fsencode(value)


def mount(source, target, fstype=None, flags=0, data=None):
    result = libc.mount(
        _bytes(source),
        _bytes(target),
        _bytes(fstype),
        flags,
        _bytes(data),
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def mount_id(fd):
    with open(f"/proc/self/fdinfo/{fd}", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("mnt_id:"):
                return int(line.split()[1])
    raise RuntimeError(f"no mount id for fd {fd}")


def mountinfo(mount_id_value):
    with open("/proc/self/mountinfo", encoding="utf-8") as stream:
        for line in stream:
            if int(line.split()[0]) == mount_id_value:
                return line.strip()
    return None


def propagation(line):
    if line is None:
        return "gone"

    pre_separator = line.split(" - ", 1)[0].split()
    optional = pre_separator[6:]
    shared = [item for item in optional if item.startswith("shared:")]
    master = [item for item in optional if item.startswith("master:")]
    return ",".join(shared + master) or "private"


def report(label, mount_id_value):
    line = mountinfo(mount_id_value)
    print(label, mount_id_value, propagation(line), line)


root = tempfile.mkdtemp(prefix="crun-fd-")
target = os.path.join(root, "target")
os.mkdir(target)

# Lower mount: mark it shared so changing it later is directly observable.
mount("tmpfs", target, "tmpfs", 0, "mode=0755")
mount(None, target, None, MS_SHARED, None)
old_fd = os.open(target, O_PATH | os.O_CLOEXEC)
old_id = mount_id(old_fd)
report("old-before", old_id)

# Overmount the same pathname. old_fd remains attached to the hidden lower
# mount. The newly opened fd points at the visible top mount.
mount("tmpfs", target, "tmpfs", 0, "mode=0755")
mount(None, target, None, MS_SHARED, None)
new_fd = os.open(target, O_PATH | os.O_CLOEXEC)
new_id = mount_id(new_fd)
report("new-before", new_id)
print("old-hidden-before", old_id, propagation(mountinfo(old_id)))

# Emulate the stale-proc-path fallback: use the fd captured before overmount.
mount(None, f"/proc/self/fd/{old_fd}", None, MS_PRIVATE, None)
report("old-after-fallback", old_id)
report("new-after-fallback", new_id)

# Negative/control path: use the reopened fd. This must change the visible top
# mount, proving the oracle distinguishes the two mount objects.
mount(None, f"/proc/self/fd/{new_fd}", None, MS_PRIVATE, None)
report("new-after-control", new_id)

os.close(new_fd)
os.close(old_fd)
