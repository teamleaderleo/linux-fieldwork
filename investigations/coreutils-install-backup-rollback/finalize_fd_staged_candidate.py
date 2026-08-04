#!/usr/bin/env python3
"""Apply exact post-transform portability adjustments to the fd-staged model."""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: finalize_fd_staged_candidate.py COREUTILS_ROOT")

    path = Path(sys.argv[1]).resolve() / "src/uu/install/src/install.rs"
    text = path.read_text(encoding="utf-8")
    old = "use tempfile::{Builder as TempfileBuilder, NamedTempFile};\n"
    new = "#[cfg(unix)]\nuse tempfile::{Builder as TempfileBuilder, NamedTempFile};\n"
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one tempfile import, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("finalized fd-staged candidate portability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
