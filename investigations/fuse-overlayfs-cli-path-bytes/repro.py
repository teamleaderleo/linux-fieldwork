#!/usr/bin/env python3
"""Linux path byte-name control and Rust env::args semantic model."""

import os
import tempfile

with tempfile.TemporaryDirectory() as root:
    raw_root = os.fsencode(root)
    raw_dir = raw_root + b"/\xff-layer"
    os.mkdir(raw_dir)
    print("linux mkdir raw path: OK", raw_dir)
    print("linux stat raw path inode:", os.stat(raw_dir).st_ino)
    print("linux list raw:", os.listdir(raw_root))
    os.rmdir(raw_dir)

arg = b"/tmp/\xff-layer"
try:
    arg.decode("utf-8")
    gate = "accepted"
except UnicodeDecodeError:
    gate = "std::env::args String conversion would panic during iteration"
print("current Rust argv gate:", gate)
