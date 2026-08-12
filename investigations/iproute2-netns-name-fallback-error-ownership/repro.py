#!/usr/bin/env python3

"""Compare current and ENOENT-only name->PID fallback classifiers.

This helper expects one numeric PID argument. The surrounding fixture should
make /run/netns/<PID> exist but fail to open, while /proc/<PID>/ns/net remains
readable by the caller. See README.md for a disposable user+mount namespace
setup.
"""

import errno
import os
import sys


def current_style(text: str) -> tuple[str, int | None, int | None]:
    named = f"/run/netns/{text}"
    try:
        return ("named", os.open(named, os.O_RDONLY), None)
    except OSError as exc:
        named_errno = exc.errno

    try:
        int(text, 10)
    except ValueError:
        return ("error", None, named_errno)

    proc = f"/proc/{text}/ns/net"
    try:
        return ("pid", os.open(proc, os.O_RDONLY), named_errno)
    except OSError as exc:
        return ("error", None, exc.errno)


def enoent_only(text: str) -> tuple[str, int | None, int | None]:
    named = f"/run/netns/{text}"
    try:
        return ("named", os.open(named, os.O_RDONLY), None)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            return ("error", None, exc.errno)

    try:
        int(text, 10)
    except ValueError:
        return ("error", None, errno.ENOENT)

    proc = f"/proc/{text}/ns/net"
    try:
        return ("pid", os.open(proc, os.O_RDONLY), errno.ENOENT)
    except OSError as exc:
        return ("error", None, exc.errno)


def describe(label: str, result: tuple[str, int | None, int | None]) -> None:
    owner, fd, observed_errno = result
    target = None
    if fd is not None:
        target = os.readlink(f"/proc/self/fd/{fd}")
        os.close(fd)

    err_text = "none" if observed_errno is None else f"{observed_errno}:{os.strerror(observed_errno)}"
    print(f"{label}: owner={owner} prior_errno={err_text} target={target}")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} PID", file=sys.stderr)
        return 2

    text = sys.argv[1]
    describe("current", current_style(text))
    describe("enoent-only", enoent_only(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
