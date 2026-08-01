#!/usr/bin/env python3
"""Transform the disposable mmdebstrap package-test execution order."""

from __future__ import annotations

import argparse
import hashlib
import os
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
FOCUS_END_MARKER = (
    "\nfi\n\n# subtract 10 seconds to account for the inaccuracy in measuring time\n"
)


class OrderingError(RuntimeError):
    """Raised when the exact integration-only source boundary is absent."""


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


def _result(original: str, transformed: str) -> OrderingResult:
    original_digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
    transformed_digest = hashlib.sha256(transformed.encode("utf-8")).hexdigest()
    if original_digest == transformed_digest:
        raise OrderingError("transformation produced identical bytes")
    return OrderingResult(
        text=transformed,
        original_sha256=original_digest,
        reordered_sha256=transformed_digest,
    )


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
        raise OrderingError("hook-free block does not contain its metadata selector")
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

    return _result(text, reordered)


def focus_named_case(text: str, case_name: str) -> OrderingResult:
    """Replace the broad matrix with one named case and exit after its result."""

    if case_name != "dev-ptmx":
        raise OrderingError(f"unsupported focused case: {case_name!r}")

    broad = _single_position(text, BROAD_MARKER, "broad-phase")
    hook = _single_position(text, HOOK_MARKER, "hook-free hard-phase")
    soft = _single_position(text, SOFT_MARKER, "soft transition-phase")
    if not broad < hook < soft:
        raise OrderingError(
            "focused carrier expects product ordering broad < hook-free hard < "
            f"soft transition; observed broad={broad}, hook={hook}, soft={soft}"
        )

    old_invocation = '"$SRC/coverage.sh" --exitfirst || ret=$?'
    new_invocation = '"$SRC/coverage.py" --exitfirst dev-ptmx || ret=$?'
    if text.count(old_invocation) != 1:
        raise OrderingError(
            "expected exactly one broad coverage invocation before focusing"
        )
    focused = text.replace(old_invocation, new_invocation, 1)

    focused_broad = _single_position(focused, BROAD_MARKER, "focused broad-phase")
    end = focused.find(FOCUS_END_MARKER, focused_broad)
    if end < 0:
        raise OrderingError("focused broad result boundary was not found")
    insertion = end + len("\nfi\n")
    focused = focused[:insertion] + "exit 0\n" + focused[insertion:]

    if focused.count("--exitfirst dev-ptmx") != 1:
        raise OrderingError("focused case invocation is not unique")
    if focused.index("exit 0\n", focused_broad) > focused.index(HOOK_MARKER):
        raise OrderingError("focused exit does not precede the unrelated hook-free phase")

    return _result(text, focused)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move the retained hook-free block ahead of the broad matrix, or "
            "focus the disposable carrier when UNIT09_FOCUS is set."
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
    focus = os.environ.get("UNIT09_FOCUS", "")
    try:
        original = path.read_text(encoding="utf-8")
        if focus:
            result = focus_named_case(original, focus)
            mode = f"focused-{focus}"
        else:
            result = reorder_hook_free_phase(original)
            mode = "hook-free-hard,broad,soft-transition"
        if not args.check:
            path.write_text(result.text, encoding="utf-8")
    except (OSError, UnicodeError, OrderingError) as error:
        print(f"package-test transformation failed: {error}", file=sys.stderr)
        return 2

    print(f"original_sha256={result.original_sha256}")
    print(f"reordered_sha256={result.reordered_sha256}")
    print(f"integration_order={mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
