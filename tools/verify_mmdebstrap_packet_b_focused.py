#!/usr/bin/env python3
"""Verify one focused mmdebstrap Packet B autopkgtest console."""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
from typing import Sequence

from tools.mmdebstrap_autopkgtest_log import ANSI_RE, DETAIL_RE, TEST_RE


PRODUCER = "create-directory"
CONSUMER = "root-without-cap-sys-admin"


class VerificationError(ValueError):
    """Raised when the focused console does not establish the exact contract."""


@dataclasses.dataclass(frozen=True)
class TestOccurrence:
    line: int
    index: int
    total: int
    name: str
    outcome: str | None
    outcome_line: int | None
    dimensions: dict[str, str]


@dataclasses.dataclass(frozen=True)
class VerificationReceipt:
    schema_version: int
    raw_status: int
    producer: TestOccurrence
    consumer: TestOccurrence
    named_test_count: int
    testsuite_pass_line: int
    later_named_tests: tuple[TestOccurrence, ...]


def parse_occurrences(text: str) -> list[TestOccurrence]:
    records: list[TestOccurrence] = []
    current: dict[str, object] | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = ANSI_RE.sub("", raw_line)
        match = TEST_RE.search(line)
        if match:
            if current is not None:
                records.append(TestOccurrence(**current))
            current = {
                "line": line_number,
                "index": int(match.group("index")),
                "total": int(match.group("total")),
                "name": match.group("name"),
                "outcome": None,
                "outcome_line": None,
                "dimensions": {},
            }
        if current is not None:
            dimensions = current["dimensions"]
            assert isinstance(dimensions, dict)
            for detail in DETAIL_RE.finditer(line):
                dimensions[detail.group("key")] = detail.group("value")
            lower = line.lower()
            if "result: success" in lower:
                current["outcome"] = "success"
                current["outcome_line"] = line_number
                records.append(TestOccurrence(**current))
                current = None
            elif "result: failure" in lower or "test.sh failed" in lower:
                current["outcome"] = "failure"
                current["outcome_line"] = line_number
                records.append(TestOccurrence(**current))
                current = None
    if current is not None:
        records.append(TestOccurrence(**current))
    return records


def verify_console(text: str, *, raw_status: int) -> VerificationReceipt:
    if type(raw_status) is not int or raw_status < 0:
        raise VerificationError("raw status must be a nonnegative integer")
    if raw_status != 0:
        raise VerificationError(f"focused autopkgtest status is not zero: {raw_status}")

    records = parse_occurrences(text)
    producers = [record for record in records if record.name == PRODUCER]
    consumers = [record for record in records if record.name == CONSUMER]
    if len(producers) != 1:
        raise VerificationError(
            f"expected exactly one {PRODUCER}, found {len(producers)}"
        )
    if len(consumers) != 1:
        raise VerificationError(
            f"expected exactly one {CONSUMER}, found {len(consumers)}"
        )
    producer = producers[0]
    consumer = consumers[0]
    if producer.outcome != "success":
        raise VerificationError(f"producer did not succeed: {producer.outcome}")
    if consumer.outcome != "success":
        raise VerificationError(f"consumer did not succeed: {consumer.outcome}")
    if producer.outcome_line is None or consumer.outcome_line is None:
        raise VerificationError("focused outcomes lack exact result lines")
    if not producer.line < producer.outcome_line < consumer.line < consumer.outcome_line:
        raise VerificationError(
            "expected completed producer before completed consumer; observed "
            f"producer={producer.line}/{producer.outcome_line}, "
            f"consumer={consumer.line}/{consumer.outcome_line}"
        )

    later = tuple(record for record in records if record.line > consumer.outcome_line)
    if later:
        names = ", ".join(record.name for record in later[:5])
        raise VerificationError(f"named tests executed after focused consumer: {names}")

    lines = text.splitlines()
    fail_lines = [
        index
        for index, line in enumerate(lines, start=1)
        if "testsuite fail" in line.lower()
    ]
    if fail_lines:
        raise VerificationError(f"testsuite FAIL appears at line {fail_lines[0]}")
    pass_lines = [
        index
        for index, line in enumerate(lines, start=1)
        if "testsuite pass" in line.lower()
    ]
    if len(pass_lines) != 1:
        raise VerificationError(
            f"expected exactly one testsuite PASS, found {len(pass_lines)}"
        )
    if pass_lines[0] <= consumer.outcome_line:
        raise VerificationError("testsuite PASS precedes the consumer result")

    return VerificationReceipt(
        schema_version=1,
        raw_status=raw_status,
        producer=producer,
        consumer=consumer,
        named_test_count=len(records),
        testsuite_pass_line=pass_lines[0],
        later_named_tests=(),
    )


def _read_status(path: pathlib.Path) -> int:
    value = path.read_text(encoding="utf-8").strip()
    if not value.isdecimal():
        raise VerificationError(f"status is not decimal: {path}")
    return int(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Require one successful create-directory followed by one successful "
            "root-without-cap-sys-admin and no later named case."
        )
    )
    parser.add_argument("console", type=pathlib.Path)
    parser.add_argument("--status-file", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        receipt = verify_console(
            args.console.read_text(encoding="utf-8", errors="replace"),
            raw_status=_read_status(args.status_file),
        )
        encoded = json.dumps(
            dataclasses.asdict(receipt), indent=2, sort_keys=True
        ) + "\n"
        if args.output is not None:
            args.output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
    except (OSError, UnicodeError, VerificationError) as error:
        print(f"Packet B focused verification error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
