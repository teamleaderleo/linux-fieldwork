#!/usr/bin/env python3
"""Reduced discriminator for fuse-overlayfs pre-epoch timestamp conversion."""

import os
import tempfile

U64_MASK = (1 << 64) - 1
I64_MAX = (1 << 63) - 1


def current_read_seconds(sec: int) -> int:
    """Model `st.st_*time as u64`."""
    return sec & U64_MASK


def current_set_timespec(sec: int, nsec: int) -> tuple[int, int]:
    """Model `duration_since(UNIX_EPOCH).unwrap_or_default()`."""
    if sec < 0:
        return (0, 0)
    return (sec, nsec)


def signed_system_time_to_timespec(before_epoch_ns: int) -> tuple[int, int]:
    """Normalize signed nanoseconds as POSIX timespec."""
    sec, nsec = divmod(before_epoch_ns, 1_000_000_000)
    return sec, nsec


for sec, nsec in [(-1, 0), (-1, 500_000_000), (0, 0), (1, 0)]:
    widened = current_read_seconds(sec)
    print(
        f"read ({sec},{nsec}): as_u64={widened} "
        f"fits_unix_SystemTime_i64={widened <= I64_MAX}"
    )
    print(
        f"set  ({sec},{nsec}): current={current_set_timespec(sec, nsec)}"
    )

print("candidate -0.5s normalized:", signed_system_time_to_timespec(-500_000_000))
print("candidate -1.2s normalized:", signed_system_time_to_timespec(-1_200_000_000))

# Filesystem prevalence control: create an ordinary file with pre-epoch times.
with tempfile.NamedTemporaryFile() as f:
    os.utime(f.name, ns=(-500_000_000, -500_000_000))
    st = os.stat(f.name)
    print("filesystem control -0.5s:", st.st_atime_ns, st.st_mtime_ns)

    os.utime(f.name, ns=(-1_000_000_000, -1_000_000_000))
    st = os.stat(f.name)
    print("filesystem control -1s:", st.st_atime_ns, st.st_mtime_ns)
