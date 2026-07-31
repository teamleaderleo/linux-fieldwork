#!/usr/bin/env python3
"""Classify lossless argv records captured by a caller-path env wrapper."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
CLASSIFICATIONS = (
    "host-version-probe",
    "host-shell-hook",
    "sanitizer-dpkg",
    "other-host",
)
CHROOTLESS_DPKG_FLAG = "--force-script-chrootless"


@dataclass(frozen=True)
class ArgvRecord:
    path: str
    argv: tuple[str, ...]
    command_index: int | None
    command: str | None
    ignore_environment: bool
    classification: str


class ArgvReceiptError(ValueError):
    """Raised when a retained argv record is malformed or unsafe to read."""


def read_argv_record(path: pathlib.Path) -> tuple[str, ...]:
    if path.is_symlink():
        raise ArgvReceiptError(f"argv record is a symbolic link: {path}")
    if not path.is_file():
        raise ArgvReceiptError(f"argv record is not a regular file: {path}")
    raw = path.read_bytes()
    if not raw:
        raise ArgvReceiptError(f"argv record is empty: {path}")
    if not raw.endswith(b"\0"):
        raise ArgvReceiptError(f"argv record lacks a trailing NUL: {path}")
    fields = raw[:-1].split(b"\0")
    return tuple(field.decode("utf-8", errors="surrogateescape") for field in fields)


def _next_command(argv: Sequence[str]) -> tuple[int | None, bool]:
    ignore_environment = False
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--":
            index += 1
            break
        if value in ("-i", "--ignore-environment"):
            ignore_environment = True
            index += 1
            continue
        if value in ("-u", "--unset", "-C", "--chdir"):
            if index + 1 >= len(argv):
                return None, ignore_environment
            index += 2
            continue
        if value.startswith("--unset=") or value.startswith("--chdir="):
            index += 1
            continue
        if value.startswith("-u") and value != "-u":
            index += 1
            continue
        if value.startswith("-C") and value != "-C":
            index += 1
            continue
        if value in ("-S", "--split-string") or value.startswith(
            "--split-string="
        ):
            # A second parsing layer owns command identity here. Keep it as an
            # explicit other-host record instead of guessing.
            return None, ignore_environment
        if value.startswith("-"):
            return None, ignore_environment
        if ASSIGNMENT.match(value):
            index += 1
            continue
        break
    if index >= len(argv):
        return None, ignore_environment
    return index, ignore_environment


def classify_argv(argv: Sequence[str], *, path: str = "<memory>") -> ArgvRecord:
    values = tuple(argv)
    if values == ("--version",):
        return ArgvRecord(
            path=path,
            argv=values,
            command_index=None,
            command=None,
            ignore_environment=False,
            classification="host-version-probe",
        )

    command_index, ignore_environment = _next_command(values)
    command = values[command_index] if command_index is not None else None
    basename = os.path.basename(command) if command else None
    command_argv = values[command_index + 1 :] if command_index is not None else ()

    if (
        ignore_environment
        and basename == "dpkg"
        and CHROOTLESS_DPKG_FLAG in command_argv
    ):
        classification = "sanitizer-dpkg"
    elif (
        basename == "sh"
        and command_index is not None
        and len(values) >= command_index + 5
        and values[command_index + 1] == "-c"
        and values[command_index + 3] == "exec"
    ):
        classification = "host-shell-hook"
    else:
        classification = "other-host"

    return ArgvRecord(
        path=path,
        argv=values,
        command_index=command_index,
        command=command,
        ignore_environment=ignore_environment,
        classification=classification,
    )


def iter_record_paths(paths: Sequence[pathlib.Path]) -> Iterable[pathlib.Path]:
    seen: set[pathlib.Path] = set()
    for path in paths:
        if path.is_symlink():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(candidate for candidate in path.iterdir())
        else:
            candidates = [path]
        for candidate in candidates:
            identity = candidate.absolute()
            if identity in seen:
                continue
            seen.add(identity)
            yield candidate


def classify_paths(paths: Sequence[pathlib.Path]) -> dict[str, object]:
    records = [
        classify_argv(read_argv_record(path), path=str(path))
        for path in iter_record_paths(paths)
    ]
    counts = Counter(record.classification for record in records)
    return {
        "schema_version": 1,
        "files_checked": len(records),
        "counts": {name: counts[name] for name in CLASSIFICATIONS},
        "records": [asdict(record) for record in records],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Classify NUL-delimited argv records from a caller-path env wrapper. "
            "Directories are scanned non-recursively in lexical order."
        )
    )
    parser.add_argument("paths", nargs="+", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = classify_paths(args.paths)
    except (OSError, UnicodeError, ArgvReceiptError) as error:
        print(f"env argv receipt invalid: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
