#!/usr/bin/env python3
"""Model privilege-mode persistence in a stat-override xattr across backing writes."""

import os
import tempfile

XATTR = b"user.containers.override_stat"
LOGICAL = b"1000:1000:4755"

with tempfile.NamedTemporaryFile(dir="/tmp") as f:
    os.setxattr(f.name, XATTR, LOGICAL)
    os.chmod(f.name, 0o755)
    print("backing mode before write:", oct(os.stat(f.name).st_mode & 0o7777))
    print("logical override before write:", os.getxattr(f.name, XATTR))

    with open(f.name, "ab", buffering=0) as out:
        out.write(b"x")

    print("backing mode after write:", oct(os.stat(f.name).st_mode & 0o7777))
    print("logical override after write:", os.getxattr(f.name, XATTR))
    print("current stat-override interpretation still carries mode 04755")
    print("killpriv-aware interpretation must clear privilege bits / capabilities")

# Pure chown state model: current Rust preserves cur_mode if only uid/gid changes.
cur_mode = 0o4755
new_uid = 2000
print("logical chown current override:", f"{new_uid}:1000:{cur_mode:o}")
print("expected killpriv mode at minimum clears S_ISUID:", oct(cur_mode & ~0o4000))
