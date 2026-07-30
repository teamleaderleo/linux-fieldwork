#!/usr/bin/env python3
"""Compare two JSON Lines manifests produced by tar_manifest.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_IGNORED_FIELDS: tuple[str, ...] = ()


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise ValueError(
                    f"{path}:{line_number}: entry requires a string 'path'"
                )
            item_path = entry["path"]
            if item_path in entries:
                raise ValueError(
                    f"{path}:{line_number}: duplicate path {item_path!r}"
                )
            entries[item_path] = entry
    return entries


def filtered(entry: dict[str, Any], ignored_fields: set[str]) -> dict[str, Any]:
    return {
        key: value for key, value in entry.items() if key not in ignored_fields
    }


def compare(
    left: dict[str, dict[str, Any]],
    right: dict[str, dict[str, Any]],
    ignored_fields: set[str],
) -> dict[str, Any]:
    left_paths = set(left)
    right_paths = set(right)
    added = sorted(right_paths - left_paths)
    removed = sorted(left_paths - right_paths)
    changed: list[dict[str, Any]] = []

    for path in sorted(left_paths & right_paths):
        left_entry = filtered(left[path], ignored_fields)
        right_entry = filtered(right[path], ignored_fields)
        if left_entry == right_entry:
            continue
        fields = sorted(
            key
            for key in set(left_entry) | set(right_entry)
            if left_entry.get(key) != right_entry.get(key)
        )
        changed.append(
            {
                "path": path,
                "fields": fields,
                "left": {
                    field: left_entry.get(field) for field in fields
                },
                "right": {
                    field: right_entry.get(field) for field in fields
                },
            }
        )

    return {
        "equal": not added and not removed and not changed,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
        "added": added,
        "removed": removed,
        "changed": changed,
        "ignored_fields": sorted(ignored_fields),
    }


def print_text(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print(
        f"added={summary['added']} "
        f"removed={summary['removed']} "
        f"changed={summary['changed']}"
    )
    for path in result["added"]:
        print(f"+ {path}")
    for path in result["removed"]:
        print(f"- {path}")
    for item in result["changed"]:
        print(f"~ {item['path']}: {', '.join(item['fields'])}")
        for field in item["fields"]:
            print(
                f"    {field}: "
                f"{item['left'][field]!r} -> {item['right'][field]!r}"
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument(
        "--ignore-field",
        action="append",
        default=list(DEFAULT_IGNORED_FIELDS),
        help="manifest field to ignore; may be repeated (for example: mtime)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable JSON result",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        left = load_manifest(args.left)
        right = load_manifest(args.right)
        result = compare(left, right, set(args.ignore_field))
    except (OSError, ValueError) as exc:
        print(f"manifest_diff: {exc}", file=sys.stderr)
        return 2

    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print_text(result)
    return 0 if result["equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
