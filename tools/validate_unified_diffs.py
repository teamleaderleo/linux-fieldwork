#!/usr/bin/env python3
"""Validate unified-diff hunk grammar and declared line counts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


HUNK_HEADER = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? "
    r"@@(?: .*)?$"
)
NO_NEWLINE_MARKER = r"\ No newline at end of file"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class ValidationResult:
    path: str
    hunks: int
    findings: tuple[Finding, ...]


def _declared_count(raw_count: str | None) -> int:
    return 1 if raw_count is None else int(raw_count)


def validate_text(text: str, *, path: str = "<memory>") -> ValidationResult:
    """Validate one patch's unified-diff hunk headers and body counts."""

    lines = text.splitlines()
    findings: list[Finding] = []
    hunks = 0
    saw_patch_structure = False
    saw_binary_marker = False
    index = 0

    while index < len(lines):
        line = lines[index]

        if line.startswith("diff --git ") or line.startswith("--- ") or line.startswith("+++ "):
            saw_patch_structure = True
        if line == "GIT binary patch" or (
            line.startswith("Binary files ") and line.endswith(" differ")
        ):
            saw_patch_structure = True
            saw_binary_marker = True

        if not line.startswith("@@"):
            index += 1
            continue

        saw_patch_structure = True
        match = HUNK_HEADER.fullmatch(line)
        if match is None:
            findings.append(
                Finding(path, index + 1, f"malformed unified-diff hunk header: {line!r}")
            )
            index += 1
            continue

        hunks += 1
        old_expected = _declared_count(match.group("old_count"))
        new_expected = _declared_count(match.group("new_count"))
        old_actual = 0
        new_actual = 0
        header_line = index + 1
        index += 1

        while index < len(lines):
            body = lines[index]
            if body.startswith("@@") or body.startswith("diff --git "):
                break
            if body == NO_NEWLINE_MARKER:
                index += 1
                continue
            if not body:
                findings.append(
                    Finding(
                        path,
                        index + 1,
                        "bare empty line inside hunk; an empty context line must start with a space",
                    )
                )
                index += 1
                continue

            prefix = body[0]
            if prefix == " ":
                old_actual += 1
                new_actual += 1
            elif prefix == "-":
                old_actual += 1
            elif prefix == "+":
                new_actual += 1
            else:
                findings.append(
                    Finding(
                        path,
                        index + 1,
                        f"invalid hunk-body prefix {prefix!r}; expected space, '+', '-', or a no-newline marker",
                    )
                )
            index += 1

        if old_actual != old_expected or new_actual != new_expected:
            findings.append(
                Finding(
                    path,
                    header_line,
                    "hunk count mismatch: "
                    f"declared old/new {old_expected}/{new_expected}, "
                    f"observed {old_actual}/{new_actual}",
                )
            )

    if not saw_patch_structure:
        findings.append(
            Finding(path, 1, "no unified-diff or Git binary patch structure found")
        )
    elif hunks == 0 and not saw_binary_marker:
        # Mode-only, rename-only, and copy-only Git patches are valid without hunks.
        pass

    return ValidationResult(path, hunks, tuple(findings))


def _iter_patch_paths(raw_paths: Sequence[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for raw_path in raw_paths:
        path = Path(raw_path)
        if path.is_dir():
            candidates = sorted(path.rglob("*.patch"))
        else:
            candidates = [path]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


def validate_path(path: Path) -> ValidationResult:
    display_path = str(path)
    if not path.exists():
        return ValidationResult(
            display_path,
            0,
            (Finding(display_path, 1, "path does not exist"),),
        )
    if not path.is_file():
        return ValidationResult(
            display_path,
            0,
            (Finding(display_path, 1, "path is not a regular file"),),
        )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ValidationResult(
            display_path,
            0,
            (
                Finding(
                    display_path,
                    1,
                    "patch is not valid UTF-8",
                ),
            ),
        )
    return validate_text(text, path=display_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate unified-diff hunk grammar and declared old/new line counts. "
            "Directories are scanned recursively for *.patch files."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="patch files or directories containing patch files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable summary",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = [validate_path(path) for path in _iter_patch_paths(args.paths)]
    findings = [finding for result in results for finding in result.findings]
    hunk_count = sum(result.hunks for result in results)

    if args.json:
        payload = {
            "schema_version": 1,
            "files_checked": len(results),
            "hunks_checked": hunk_count,
            "findings": [asdict(finding) for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        for finding in findings:
            print(
                f"{finding.path}:{finding.line}: {finding.message}",
                file=sys.stderr,
            )
    else:
        print(
            f"validated {len(results)} patch file(s) and {hunk_count} hunk(s)"
        )

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
