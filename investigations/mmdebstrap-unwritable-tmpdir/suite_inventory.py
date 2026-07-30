#!/usr/bin/env python3
"""Inventory mmdebstrap's source and coverage matrix without running it."""

from __future__ import annotations

import json
import os
from collections import Counter
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "upstream" / "mmdebstrap"
RESULTS = ROOT / "investigations" / "mmdebstrap-unwritable-tmpdir" / "results"

ALL_VALUES = {
    "Dists": ["oldstable", "stable", "testing", "unstable"],
    "Modes": ["auto", "root", "unshare", "fakechroot", "chrootless"],
    "Variants": [
        "extract",
        "custom",
        "essential",
        "apt",
        "minbase",
        "buildd",
        "-",
        "standard",
    ],
    "Formats": ["auto", "directory", "tar", "squashfs", "ext2", "ext4", "null"],
}
DEFAULTS = {
    "Dists": ["unstable"],
    "Modes": ["auto"],
    "Variants": ["apt"],
    "Formats": ["auto"],
}


def parse_deb822_like(path: Path) -> list[dict[str, str]]:
    paragraphs: list[dict[str, str]] = []
    current: dict[str, str] = {}
    last_key: str | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            if current:
                paragraphs.append(current)
                current = {}
                last_key = None
            continue
        if raw[0].isspace():
            if last_key is None:
                raise ValueError(f"continuation without a field: {raw!r}")
            current[last_key] += "\n" + raw.strip()
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            raise ValueError(f"field without a colon: {raw!r}")
        last_key = key
        current[key] = value.strip()

    if current:
        paragraphs.append(current)
    return paragraphs


def values(test: dict[str, str], field: str) -> list[str]:
    raw = test.get(field)
    if raw is None:
        return DEFAULTS[field]
    if raw == "any":
        return ALL_VALUES[field]
    return raw.split()


def skip_reason(
    condition: str | None,
    *,
    dist: str,
    mode: str,
    variant: str,
    fmt: str,
    hostarch: str,
) -> str | None:
    if not condition:
        return None
    context = {
        "dist": dist,
        "mode": mode,
        "variant": variant,
        "fmt": fmt,
        "hostarch": hostarch,
        "run_ma_same_tests": True,
        "have_binfmt": True,
    }
    for line in condition.splitlines():
        line = line.strip()
        if line and bool(eval(line, {"__builtins__": {}}, context)):
            return line
    return None


def main() -> None:
    tests = parse_deb822_like(SOURCE / "coverage.txt")
    test_names = [test["Test"] for test in tests]
    test_files = sorted(
        path.name
        for path in (SOURCE / "tests").iterdir()
        if path.is_file() and not path.name.startswith(".")
    )

    missing_from_registry = sorted(set(test_files) - set(test_names))
    missing_from_directory = sorted(set(test_names) - set(test_files))

    hostarch = os.uname().machine
    if hostarch == "x86_64":
        hostarch = "amd64"
    elif hostarch == "aarch64":
        hostarch = "arm64"

    total_cases = 0
    skipped_cases = 0
    cases_by_mode: Counter[str] = Counter()
    cases_by_format: Counter[str] = Counter()
    cases_by_test: Counter[str] = Counter()

    for test in tests:
        for dist, mode, variant, fmt in product(
            values(test, "Dists"),
            values(test, "Modes"),
            values(test, "Variants"),
            values(test, "Formats"),
        ):
            total_cases += 1
            cases_by_mode[mode] += 1
            cases_by_format[fmt] += 1
            cases_by_test[test["Test"]] += 1
            if skip_reason(
                test.get("Skip-If"),
                dist=dist,
                mode=mode,
                variant=variant,
                fmt=fmt,
                hostarch=hostarch,
            ):
                skipped_cases += 1

    source_lines = (SOURCE / "mmdebstrap").read_text(encoding="utf-8").splitlines()
    try:
        code_lines = source_lines.index("__END__")
    except ValueError:
        code_lines = len(source_lines)

    test_line_count = sum(
        len((SOURCE / "tests" / name).read_text(encoding="utf-8").splitlines())
        for name in test_files
    )

    data = {
        "source_revision": "6fde999741f4fe1e7bf38079acf29432ef87a35e",
        "candidate_main": "c7f586470c34ca21a94a15ff340b3eca067f6ce5",
        "hostarch_for_skip_evaluation": hostarch,
        "source": {
            "mmdebstrap_total_lines": len(source_lines),
            "mmdebstrap_code_lines_before_pod": code_lines,
        },
        "tests": {
            "registered_test_definitions": len(tests),
            "test_files": len(test_files),
            "test_script_lines": test_line_count,
            "generated_matrix_cases": total_cases,
            "statically_skipped_cases_on_this_arch": skipped_cases,
            "potentially_runnable_cases_on_this_arch": total_cases - skipped_cases,
            "definitions_needing_root": sum(
                test.get("Needs-Root", "false") == "true" for test in tests
            ),
            "definitions_needing_qemu": sum(
                test.get("Needs-QEMU", "false") == "true" for test in tests
            ),
            "definitions_needing_apt_config": sum(
                test.get("Needs-APT-Config", "false") == "true" for test in tests
            ),
            "cases_by_mode": dict(sorted(cases_by_mode.items())),
            "cases_by_format": dict(sorted(cases_by_format.items())),
            "largest_expansions": cases_by_test.most_common(10),
            "missing_from_registry": missing_from_registry,
            "missing_from_test_directory": missing_from_directory,
        },
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "suite-inventory.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )

    t = data["tests"]
    report = f"""# mmdebstrap suite inventory

- Registered test definitions: {t['registered_test_definitions']}
- Test files: {t['test_files']}
- Generated matrix cases: {t['generated_matrix_cases']}
- Statically skipped cases on {hostarch}: {t['statically_skipped_cases_on_this_arch']}
- Potentially runnable cases on {hostarch}: {t['potentially_runnable_cases_on_this_arch']}
- Definitions needing root: {t['definitions_needing_root']}
- Definitions needing QEMU: {t['definitions_needing_qemu']}
- Definitions needing an isolated apt configuration: {t['definitions_needing_apt_config']}
- Main executable lines before embedded POD: {data['source']['mmdebstrap_code_lines_before_pod']}
- Main executable total lines including embedded documentation: {data['source']['mmdebstrap_total_lines']}
- Aggregate lines across test scripts: {t['test_script_lines']}

The matrix count is the cartesian expansion performed by `coverage.py` before runtime skips and command-line filters. It is not a count of distinct test files and it does not predict wall-clock time by itself.
"""
    (RESULTS / "suite-inventory.md").write_text(report, encoding="utf-8")
    print(json.dumps(data, indent=2))

    if missing_from_registry or missing_from_directory:
        raise SystemExit("coverage registry and tests directory disagree")


if __name__ == "__main__":
    main()
