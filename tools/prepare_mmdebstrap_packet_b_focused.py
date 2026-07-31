#!/usr/bin/env python3
"""Prepare the mmdebstrap package testsuite for one focused Packet B run."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Sequence


BROAD_MARKER = "# now run the script\n"
HOOK_MARKER = (
    "# run hook-free tests whose failures remain authoritative for the package test\n"
)
SOFT_MARKER = (
    "# run only those tests that were skipped because of USE_HOST_APT_CONFIG=yes but\n"
)
STOP_BLOCK = (
    "# focused-only Packet B carrier stops after the authoritative hook-free phase\n"
    "exit 0\n\n"
)
EXPECTED_SELECTOR = (
    'HOOK_FREE_HARD_TESTS="create-directory\n'
    '$HOOK_FREE_HARD_CONSUMERS"\n'
)


class PreparationError(ValueError):
    """Raised when the exact package-test source shape is not present."""


@dataclasses.dataclass(frozen=True)
class PreparationReceipt:
    schema_version: int
    original_sha256: str
    prepared_sha256: str
    original_order: tuple[str, ...]
    prepared_order: tuple[str, ...]
    focused_stop_count: int


def _single_position(text: str, marker: str, label: str) -> int:
    count = text.count(marker)
    if count != 1:
        raise PreparationError(
            f"expected exactly one {label} marker, found {count}: {marker!r}"
        )
    return text.index(marker)


def _order(text: str, *, include_stop: bool) -> tuple[str, ...]:
    positions = [
        (_single_position(text, HOOK_MARKER, "hook-free hard-phase"), "hook-free-hard"),
        (_single_position(text, BROAD_MARKER, "broad phase"), "broad"),
        (_single_position(text, SOFT_MARKER, "soft transition phase"), "soft-transition"),
    ]
    if include_stop:
        positions.append(
            (_single_position(text, STOP_BLOCK, "focused stop"), "focused-stop")
        )
    return tuple(label for _offset, label in sorted(positions))


def prepare_focused_testsuite(text: str) -> tuple[str, PreparationReceipt]:
    """Move the hard phase first and stop after it, or fail closed."""

    if STOP_BLOCK in text:
        raise PreparationError("testsuite already contains the focused stop block")

    broad = _single_position(text, BROAD_MARKER, "broad phase")
    hook = _single_position(text, HOOK_MARKER, "hook-free hard-phase")
    soft = _single_position(text, SOFT_MARKER, "soft transition phase")
    if not broad < hook < soft:
        raise PreparationError(
            "expected unprepared order broad < hook-free-hard < soft-transition; "
            f"observed broad={broad}, hook={hook}, soft={soft}"
        )

    hook_block = text[hook:soft]
    required_fragments = (
        "Needs-Hook-Free-APT-Config",
        EXPECTED_SELECTOR,
        'CMD="mmdebstrap"',
        '"$SRC/coverage.py" --exitfirst $HOOK_FREE_HARD_TESTS',
        'exit "$ret"',
        "exit 77",
    )
    for fragment in required_fragments:
        if fragment not in hook_block:
            raise PreparationError(
                f"hook-free block is missing required fragment: {fragment!r}"
            )

    without_hook = text[:hook] + text[soft:]
    broad_after_removal = _single_position(
        without_hook, BROAD_MARKER, "broad phase after extraction"
    )
    reordered = (
        without_hook[:broad_after_removal]
        + hook_block
        + without_hook[broad_after_removal:]
    )

    hook_after = _single_position(reordered, HOOK_MARKER, "reordered hard phase")
    broad_after = _single_position(reordered, BROAD_MARKER, "reordered broad phase")
    soft_after = _single_position(reordered, SOFT_MARKER, "reordered soft phase")
    if not hook_after < broad_after < soft_after:
        raise PreparationError(
            "reordered testsuite does not satisfy hook-free-hard < broad < soft"
        )

    prepared = reordered[:broad_after] + STOP_BLOCK + reordered[broad_after:]
    stop = _single_position(prepared, STOP_BLOCK, "focused stop")
    hook_final = _single_position(prepared, HOOK_MARKER, "final hard phase")
    broad_final = _single_position(prepared, BROAD_MARKER, "final broad phase")
    soft_final = _single_position(prepared, SOFT_MARKER, "final soft phase")
    if not hook_final < stop < broad_final < soft_final:
        raise PreparationError(
            "focused testsuite does not satisfy hard < stop < broad < soft"
        )
    if prepared.count(EXPECTED_SELECTOR) != 1:
        raise PreparationError("focused producer/consumer selector is not unique")

    original_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    prepared_sha256 = hashlib.sha256(prepared.encode("utf-8")).hexdigest()
    if original_sha256 == prepared_sha256:
        raise PreparationError("preparation produced identical bytes")

    receipt = PreparationReceipt(
        schema_version=1,
        original_sha256=original_sha256,
        prepared_sha256=prepared_sha256,
        original_order=_order(text, include_stop=False),
        prepared_order=_order(prepared, include_stop=True),
        focused_stop_count=prepared.count(STOP_BLOCK),
    )
    return prepared, receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move the exact hook-free hard phase ahead of broad coverage and "
            "insert an explicit focused-only stop after it."
        )
    )
    parser.add_argument("testsuite", type=pathlib.Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--receipt", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        original = args.testsuite.read_text(encoding="utf-8")
        prepared, receipt = prepare_focused_testsuite(original)
        if not args.check:
            args.testsuite.write_text(prepared, encoding="utf-8")
        encoded = json.dumps(
            dataclasses.asdict(receipt), indent=2, sort_keys=True
        ) + "\n"
        if args.receipt is not None:
            args.receipt.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
    except (OSError, UnicodeError, PreparationError) as error:
        print(f"Packet B focused preparation error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
