#!/usr/bin/env python3
"""Linux xattr byte-name control and Rust-rewrite semantic model."""

import os
import tempfile

NAME = b"user.\xff"
VALUE = b"fieldwork"


def current_rust_name_gate(name: bytes) -> str:
    try:
        name.decode("utf-8")
    except UnicodeDecodeError:
        return "EINVAL / omitted"
    return "accepted"


print("current Rust gate:", current_rust_name_gate(NAME))

with tempfile.NamedTemporaryFile() as f:
    os.setxattr(f.name, NAME, VALUE)
    print("linux setxattr bytes: OK")
    print("linux getxattr bytes:", os.getxattr(f.name, NAME))
    listed = os.listxattr(f.name)
    print("linux listxattr display:", listed)
    # Python decodes arbitrary OS bytes with surrogateescape. Recover the raw bytes.
    recovered = [os.fsencode(n) for n in listed]
    print("linux listxattr raw contains name:", NAME in recovered)
    os.removexattr(f.name, NAME)
    print("linux removexattr bytes: OK")
