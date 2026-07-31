#!/usr/bin/env python3
"""Move the retained hook-free hard phase ahead of the broad mmdebstrap matrix."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
from dataclasses import dataclass
from typing import Sequence


BROAD_MARKER = "# now run the script\n"
HOOK_MARKER = (
    "# run hook-free tests whose failures remain authoritative for the package test\n"
)
SOFT_MARKER = (
    "# run only those tests that were skipped because of USE_HOST_APT_CONFIG=yes but\n"
)


class OrderingError(RuntimeError):
    """Raised when the exact integration-only source boundary is not present."""


@dataclass(frozen=True)
class OrderingResult:
    text: str
    original_sha256: str
    reordered_sha256: str


def _single_position(text: str, marker: str, label: str) -> int:
    count = text.count(marker)
    if count != 1:
        raise OrderingError(
            f"expected exactly one {label} marker, found {count}: {marker!r}"
        )
    return text.index(marker)


def reorder_hook_free_phase(text: str) -> OrderingResult:
    """Return a testsuite with the exact retained hook-free block moved earlier."""

    broad = _single_position(text, BROAD_MARKER, "broad-phase")
    hook = _single_position(text, HOOK_MARKER, "hook-free hard-phase")
    soft = _single_position(text, SOFT_MARKER, "soft transition-phase")

    if not broad < hook < soft:
        raise OrderingError(
            "expected product ordering broad < hook-free hard < soft transition; "
            f"observed offsets broad={broad}, hook={hook}, soft={soft}"
        )

    hook_block = text[hook:soft]
    if "Needs-Hook-Free-APT-Config" not in hook_block:
        raise OrderingError(
            "hook-free block does not contain its metadata selector"
        )
    if 'CMD="mmdebstrap"' not in hook_block:
        raise OrderingError("hook-free block does not use the hook-free command")
    if "exit \"$ret\"" not in hook_block:
        raise OrderingError("hook-free block does not preserve hard child failures")

    without_block = text[:hook] + text[soft:]
    broad_after_removal = _single_position(
        without_block,
        BROAD_MARKER,
        "broad-phase after extraction",
    )
    reordered = (
        without_block[:broad_after_removal]
        + hook_block
        + without_block[broad_after_removal:]
    )

    reordered_hook = _single_position(
        reordered,
        HOOK_MARKER,
        "reordered hook-free hard-phase",
    )
    reordered_broad = _single_position(
        reordered,
        BROAD_MARKER,
        "reordered broad-phase",
    )
    reordered_soft = _single_position(
        reordered,
        SOFT_MARKER,
        "reordered soft transition-phase",
    )
    if not reordered_hook < reordered_broad < reordered_soft:
        raise OrderingError(
            "integration ordering verification failed: expected "
            "hook-free hard < broad < soft transition"
        )

    original_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    reordered_digest = hashlib.sha256(reordered.encode("utf-8")).hexdigest()
    if original_digest == reordered_digest:
        raise OrderingError("reordering produced identical bytes")

    return OrderingResult(
        text=reordered,
        original_sha256=original_digest,
        reordered_sha256=reordered_digest,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move the exact retained hook-free hard-failure block ahead of the "
            "broad mmdebstrap matrix for the disposable integration carrier."
        )
    )
    parser.add_argument("testsuite", type=pathlib.Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and report the transformation without writing it",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.testsuite
    try:
        original = path.read_text(encoding="utf-8")
        result = reorder_hook_free_phase(original)
        if not args.check:
            path.write_text(result.text, encoding="utf-8")
    except (OSError, UnicodeError, OrderingError) as error:
        print(f"hook-free phase reorder failed: {error}", file=sys.stderr)
        return 2

    print(f"original_sha256={result.original_sha256}")
    print(f"reordered_sha256={result.reordered_sha256}")
    print("integration_order=hook-free-hard,broad,soft-transition")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
