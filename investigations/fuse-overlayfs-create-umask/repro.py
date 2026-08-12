#!/usr/bin/env python3
"""Model FUSE_DONT_MASK creation against a fixed daemon process umask."""


def kernel_create_result(mode: int, process_umask: int) -> int:
    return mode & ~process_umask & 0o7777


def current(mode: int, caller_umask: int, daemon_umask: int) -> int:
    # Current Rust ignores the FUSE request umask and passes mode through.
    return kernel_create_result(mode, daemon_umask)


def old_or_candidate(mode: int, caller_umask: int, daemon_umask: int) -> int:
    # Pre-Rust C explicitly applied ctx->umask before the backing syscall.
    return kernel_create_result(mode & ~caller_umask, daemon_umask)


cases = [
    (0o666, 0o077, 0o022),
    (0o777, 0o077, 0o022),
    (0o666, 0o027, 0o022),
    (0o666, 0o022, 0o022),
]

for mode, caller, daemon in cases:
    print(
        f"requested={mode:04o} caller_umask={caller:03o} daemon_umask={daemon:03o} "
        f"current={current(mode, caller, daemon):04o} "
        f"old/candidate={old_or_candidate(mode, caller, daemon):04o}"
    )
