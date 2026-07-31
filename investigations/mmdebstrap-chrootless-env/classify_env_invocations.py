#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Sequence


_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_OPTIONS_WITH_VALUE = {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}
_OPTIONS_WITHOUT_VALUE = {"-i", "--ignore-environment", "-0", "--null", "-v", "--debug"}
_OPTIONS_WITH_EQUALS = ("--unset=", "--chdir=", "--split-string=")


class ReceiptError(ValueError):
    pass


def command_from_env_argv(argv: Sequence[str]) -> str | None:
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--":
            index += 1
            return argv[index] if index < len(argv) else None
        if item in _OPTIONS_WITH_VALUE:
            index += 2
            continue
        if item in _OPTIONS_WITHOUT_VALUE or item.startswith(_OPTIONS_WITH_EQUALS):
            index += 1
            continue
        if _ASSIGNMENT.match(item):
            index += 1
            continue
        if item.startswith("-"):
            raise ReceiptError(f"unsupported env option spelling: {item!r}")
        return item
    return None


def read_receipts(path: pathlib.Path) -> list[list[str]]:
    if not path.exists():
        return []
    records: list[list[str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReceiptError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ReceiptError(f"{path}:{number}: argv must be a list of strings")
        records.append(value)
    return records


def classify(records: Sequence[Sequence[str]]) -> dict[str, object]:
    version_probes = 0
    governed_dpkg = 0
    other: list[list[str]] = []
    for argv in records:
        if list(argv) == ["--version"]:
            version_probes += 1
            continue
        command = command_from_env_argv(argv)
        if command is not None and os.path.basename(command) == "dpkg":
            governed_dpkg += 1
            continue
        other.append(list(argv))
    return {
        "schema_version": 1,
        "invocation_count": len(records),
        "version_probe_count": version_probes,
        "governed_dpkg_count": governed_dpkg,
        "other_invocations": other,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify lossless fake-env argv receipts from the chrootless authority matrix."
    )
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument(
        "--governed-dpkg",
        choices=("forbid", "require"),
        required=True,
        help="whether caller-PATH env may launch the governed dpkg command",
    )
    parser.add_argument("--summary", type=pathlib.Path)
    args = parser.parse_args()

    try:
        summary = classify(read_receipts(args.log))
    except ReceiptError as exc:
        print(f"env receipt validation failed: {exc}", file=sys.stderr)
        return 2

    count = int(summary["governed_dpkg_count"])
    if args.governed_dpkg == "forbid" and count:
        print(
            f"caller-PATH env launched governed dpkg {count} time(s): {args.log}",
            file=sys.stderr,
        )
        return 1
    if args.governed_dpkg == "require" and count == 0:
        print(
            f"caller-PATH env did not launch governed dpkg: {args.log}",
            file=sys.stderr,
        )
        return 1

    rendered = json.dumps(summary, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if args.summary is not None:
        args.summary.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
