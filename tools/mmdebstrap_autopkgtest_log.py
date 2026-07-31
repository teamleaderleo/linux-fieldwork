#!/usr/bin/env python3
"""Classify the first meaningful failure in an mmdebstrap autopkgtest log."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TEST_RE = re.compile(r"\((?P<index>\d+)/(?P<total>\d+)\)\s+(?P<name>[A-Za-z0-9_.+-]+)")
DETAIL_RE = re.compile(r"\b(?P<key>dist|mode|variant|format):\s*(?P<value>\S+)")
SHELLCHECK_CODE_RE = re.compile(r"\bSC\d{4}\b", re.IGNORECASE)
TOOL_DIAGNOSTIC_RE = re.compile(
    r"\b(?P<tool>perlcritic|pod2man|shellcheck|shfmt)\b"
    r"(?:\s+(?:failed|failure|error)|\s*:)",
    re.IGNORECASE,
)

# Tool names alone are not failure signals. They appear in apt package lists,
# dependency summaries, and version inventories before coverage.py starts.
# Keep only phrases or output shapes that actually establish a failed gate.
PREFLIGHT_PHRASES = (
    ("perltidy failed", "perltidy failed"),
    ("exceeded maximum line length", "exceeded maximum line length"),
    ("black would reformat", "black would reformat"),
)


def _clean(line: str) -> str:
    return ANSI_RE.sub("", line).rstrip("\n")


def _append_signal(signals: list[str], signal: str) -> None:
    if signal not in signals:
        signals.append(signal)


def _preflight_signal(line: str) -> str | None:
    lower = line.lower()
    for phrase, signal in PREFLIGHT_PHRASES:
        if phrase in lower:
            return signal

    # Standard Black output is usually "would reformat PATH" without the
    # executable name. Require the diagnostic verb at the start of the
    # cleaned line so package prose cannot match it accidentally.
    if lower.strip().startswith("would reformat "):
        return "black would reformat"

    # ShellCheck's native output carries SCxxxx identifiers even when the word
    # "shellcheck" is absent. Those codes are substantially more specific than
    # the package name.
    if SHELLCHECK_CODE_RE.search(line):
        return "shellcheck"

    match = TOOL_DIAGNOSTIC_RE.search(line)
    if match is not None:
        return match.group("tool").lower()
    return None


def _record_case_failure(
    *,
    current: dict[str, Any],
    line_number: int,
    signal: str,
    first_failed_test: dict[str, Any] | None,
    failure_events: list[dict[str, Any]],
    signals: list[str],
) -> dict[str, Any]:
    failed = dict(current)
    if first_failed_test is None:
        first_failed_test = failed
        failure_events.append(
            {
                "line": line_number,
                "phase": "coverage-case",
                "signal": signal,
            }
        )
    _append_signal(signals, signal)
    return first_failed_test


def classify_lines(lines: Iterable[str]) -> dict[str, Any]:
    current: dict[str, Any] | None = None
    last_named_test: dict[str, Any] | None = None
    first_failed_test: dict[str, Any] | None = None
    failure_events: list[dict[str, Any]] = []
    signals: list[str] = []
    saw_named_test = False
    saw_pass = False
    saw_mirror_failure = False
    saw_preflight_failure = False
    saw_wrapper_failure = False

    for line_number, raw_line in enumerate(lines, start=1):
        line = _clean(raw_line)

        test_match = TEST_RE.search(line)
        if test_match:
            current = {
                "index": int(test_match.group("index")),
                "total": int(test_match.group("total")),
                "name": test_match.group("name"),
            }
            last_named_test = current
            saw_named_test = True

        if current is not None:
            for detail_match in DETAIL_RE.finditer(line):
                current[detail_match.group("key")] = detail_match.group("value")

        lower = line.lower()
        if "result: failure" in lower and current is not None:
            first_failed_test = _record_case_failure(
                current=current,
                line_number=line_number,
                signal="coverage.py reported FAILURE",
                first_failed_test=first_failed_test,
                failure_events=failure_events,
                signals=signals,
            )
            current = None
        elif "test.sh failed" in lower and current is not None:
            # coverage.sh reports direct shell-test failures with this message
            # rather than coverage.py's "result: FAILURE" spelling. Attribute
            # it only while a named case is active; a stray later diagnostic
            # must not borrow the last completed case.
            first_failed_test = _record_case_failure(
                current=current,
                line_number=line_number,
                signal="coverage.sh reported test.sh failed",
                first_failed_test=first_failed_test,
                failure_events=failure_events,
                signals=signals,
            )
            current = None
        elif "result: success" in lower and current is not None:
            current = None

        if "./make_mirror.sh failed" in line:
            if not saw_mirror_failure:
                failure_events.append(
                    {
                        "line": line_number,
                        "phase": "mirror",
                        "signal": "make_mirror.sh failed",
                    }
                )
            saw_mirror_failure = True
            _append_signal(signals, "make_mirror.sh failed")

        matched_preflight = _preflight_signal(line)
        if matched_preflight is not None and not saw_named_test:
            if not saw_preflight_failure:
                failure_events.append(
                    {
                        "line": line_number,
                        "phase": "coverage-preflight",
                        "signal": matched_preflight,
                    }
                )
            saw_preflight_failure = True
            _append_signal(signals, matched_preflight)

        if "testsuite pass" in lower:
            saw_pass = True
            _append_signal(signals, "autopkgtest reported PASS")
        if "testsuite fail" in lower or "non-zero exit status" in lower:
            saw_wrapper_failure = True
            _append_signal(signals, "autopkgtest wrapper reported failure")

    if failure_events:
        first_failure = min(failure_events, key=lambda event: event["line"])
        phase = first_failure["phase"]
    else:
        first_failure = None
        phase = "pass" if saw_pass and not saw_wrapper_failure else "unknown"

    return {
        "phase": phase,
        "first_failure_line": first_failure["line"] if first_failure else None,
        "first_failure_signal": first_failure["signal"] if first_failure else None,
        "first_failed_test": first_failed_test,
        "last_named_test": dict(last_named_test) if last_named_test else None,
        "saw_named_test": saw_named_test,
        "wrapper_failure_only": saw_wrapper_failure and phase == "unknown",
        "signals": signals,
    }


def classify_text(text: str) -> dict[str, Any]:
    return classify_lines(text.splitlines())


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _print_human(result: dict[str, Any]) -> None:
    print(f"phase: {result['phase']}")
    if result["first_failure_line"] is not None:
        print(f"first failure line: {result['first_failure_line']}")
    failed = result["first_failed_test"]
    if result["phase"] == "coverage-case" and failed:
        details = " ".join(
            f"{key}={failed[key]}"
            for key in ("dist", "mode", "variant", "format")
            if key in failed
        )
        suffix = f" {details}" if details else ""
        print(
            f"first failed test: {failed['index']}/{failed['total']} "
            f"{failed['name']}{suffix}"
        )
    elif result["last_named_test"]:
        last = result["last_named_test"]
        print(f"last named test: {last['index']}/{last['total']} {last['name']}")
    for signal in result["signals"]:
        print(f"signal: {signal}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify an mmdebstrap autopkgtest log and identify its first named failure."
    )
    parser.add_argument("log", help="UTF-8 log path, or - for standard input")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    result = classify_text(_read(args.log))
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
