#!/usr/bin/env python3
"""Classify the commit identity exercised by a pull-request workflow checkout."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CLASSIFICATIONS = {"exact-head", "synthetic-merge-ref", "other-checkout"}


class IdentityError(ValueError):
    """Raised when an identity receipt is malformed or contradictory."""


@dataclass(frozen=True)
class IdentityReceipt:
    schema_version: int
    classification: str
    checkout_sha: str
    head_sha: str
    base_sha: str
    event_sha: str
    parents: tuple[str, ...]
    event_name: str
    ref: str
    head_ref: str
    base_ref: str
    run_id: str
    run_attempt: str


def _require_string(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise IdentityError(f"{field} must be an exact string")
    if not allow_empty and not value:
        raise IdentityError(f"{field} must be nonempty")
    return value


def _require_sha(value: Any, field: str) -> str:
    text = _require_string(value, field)
    if SHA_RE.fullmatch(text) is None:
        raise IdentityError(f"{field} must be a lowercase 40-hex commit SHA")
    return text


def classify_identity(
    *,
    checkout_sha: Any,
    head_sha: Any,
    base_sha: Any,
    event_sha: Any,
    parents: Any,
) -> str:
    checkout = _require_sha(checkout_sha, "checkout_sha")
    head = _require_sha(head_sha, "head_sha")
    base = _require_sha(base_sha, "base_sha")
    event = _require_sha(event_sha, "event_sha")
    if type(parents) not in {list, tuple}:
        raise IdentityError("parents must be an exact list or tuple")
    parent_values = tuple(
        _require_sha(parent, f"parents[{index}]")
        for index, parent in enumerate(parents)
    )
    if len(parent_values) != len(set(parent_values)):
        raise IdentityError("parents must be unique")
    if checkout in parent_values:
        raise IdentityError("checkout commit cannot be its own parent")

    if checkout == head:
        return "exact-head"
    if (
        checkout == event
        and len(parent_values) == 2
        and parent_values[0] == base
        and parent_values[1] == head
    ):
        return "synthetic-merge-ref"
    return "other-checkout"


def build_receipt(data: Any) -> IdentityReceipt:
    if type(data) is not dict:
        raise IdentityError("receipt input must be an exact object")

    checkout_sha = _require_sha(data.get("checkout_sha"), "checkout_sha")
    head_sha = _require_sha(data.get("head_sha"), "head_sha")
    base_sha = _require_sha(data.get("base_sha"), "base_sha")
    event_sha = _require_sha(data.get("event_sha"), "event_sha")
    parents_value = data.get("parents")
    classification = classify_identity(
        checkout_sha=checkout_sha,
        head_sha=head_sha,
        base_sha=base_sha,
        event_sha=event_sha,
        parents=parents_value,
    )
    parents = tuple(parents_value)

    event_name = _require_string(data.get("event_name"), "event_name")
    ref = _require_string(data.get("ref"), "ref")
    head_ref = _require_string(data.get("head_ref"), "head_ref", allow_empty=True)
    base_ref = _require_string(data.get("base_ref"), "base_ref", allow_empty=True)
    run_id = _require_string(data.get("run_id"), "run_id")
    run_attempt = _require_string(data.get("run_attempt"), "run_attempt")
    if not run_id.isdecimal() or int(run_id) <= 0:
        raise IdentityError("run_id must be a positive decimal string")
    if not run_attempt.isdecimal() or int(run_attempt) <= 0:
        raise IdentityError("run_attempt must be a positive decimal string")
    if event_name == "pull_request" and (not head_ref or not base_ref):
        raise IdentityError("pull_request receipts require head_ref and base_ref")

    expected = data.get("expected")
    if expected is not None:
        expected_value = _require_string(expected, "expected")
        if expected_value not in CLASSIFICATIONS:
            raise IdentityError(f"unsupported expected classification: {expected_value}")
        if classification != expected_value:
            raise IdentityError(
                f"expected {expected_value}, observed {classification}"
            )

    return IdentityReceipt(
        schema_version=1,
        classification=classification,
        checkout_sha=checkout_sha,
        head_sha=head_sha,
        base_sha=base_sha,
        event_sha=event_sha,
        parents=parents,
        event_name=event_name,
        ref=ref,
        head_ref=head_ref,
        base_ref=base_ref,
        run_id=run_id,
        run_attempt=run_attempt,
    )


def _read_input(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify a GitHub pull-request checkout identity receipt."
    )
    parser.add_argument("input", help="JSON input path, or - for stdin")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        receipt = build_receipt(_read_input(args.input))
    except (OSError, UnicodeError, json.JSONDecodeError, IdentityError) as error:
        print(f"PR evidence identity error: {error}", file=sys.stderr)
        return 2

    encoded = json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
