#!/usr/bin/env python3
"""Audit explicit carrier-state fields on pull-request metadata.

The classifier reads a JSON list compatible with `gh pr list --json
number,title,body,url,state`. It intentionally ignores narrative words such as
"superseded" and "stopped" unless they appear in exact declaration fields.
Markdown fenced examples are excluded from declaration parsing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

FIELD_RE = re.compile(
    r"^[ \t]*(Carrier[ \t]+state|Successor)[ \t]*:[ \t]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})(.*)$")
SUCCESSOR_RE = re.compile(r"^#([1-9][0-9]*)$")
ALLOWED_STATES = {"active", "component-evidence", "superseded", "stopped"}
TERMINAL_STATES = {"superseded", "stopped"}


@dataclass(frozen=True)
class Finding:
    number: int
    title: str
    kind: str
    carrier_state: str | None
    successor: str | None
    explanation: str
    url: str


def _exact_int(value: Any) -> bool:
    return type(value) is int


def _without_fenced_code(body: str) -> str:
    """Remove Markdown fenced blocks while preserving ordinary lines.

    A fence closes only with the same marker character, at least the opening
    marker length, and no trailing content other than whitespace. Unterminated
    fences remain excluded through end of body.
    """

    output: list[str] = []
    marker_character: str | None = None
    marker_length = 0
    for line in body.splitlines():
        match = FENCE_RE.match(line)
        if marker_character is None:
            if match is None:
                output.append(line)
                continue
            marker = match.group(1)
            marker_character = marker[0]
            marker_length = len(marker)
            output.append("")
            continue

        output.append("")
        if match is None:
            continue
        marker = match.group(1)
        suffix = match.group(2)
        if (
            marker[0] == marker_character
            and len(marker) >= marker_length
            and suffix.strip() == ""
        ):
            marker_character = None
            marker_length = 0
    return "\n".join(output)


def _field_values(body: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {"carrier_state": [], "successor": []}
    for label, raw_value in FIELD_RE.findall(_without_fenced_code(body)):
        normalized_label = "".join(label.lower().split())
        key = "carrier_state" if normalized_label == "carrierstate" else "successor"
        values[key].append(raw_value.strip())
    return values


def _malformed(
    *,
    number: int,
    title: str,
    url: str,
    carrier_state: str | None,
    successor: str | None,
    explanation: str,
) -> Finding:
    return Finding(
        number=number,
        title=title,
        kind="malformed-declaration",
        carrier_state=carrier_state,
        successor=successor,
        explanation=explanation,
        url=url,
    )


def classify_pull_request(item: Any) -> list[Finding]:
    """Classify one pull-request object.

    Pull requests with neither field are outside the first adoption probe and
    pass. Once either field appears, both fields and their relationship become
    authoritative.
    """

    if not isinstance(item, dict):
        return [
            _malformed(
                number=0,
                title="<invalid item>",
                url="",
                carrier_state=None,
                successor=None,
                explanation="pull-request entry must be an object",
            )
        ]

    number = item.get("number")
    title = item.get("title")
    body = item.get("body")
    url = item.get("url", "")
    state_value = item.get("state", "OPEN")

    if not _exact_int(number) or number <= 0:
        return [
            _malformed(
                number=0,
                title=title if isinstance(title, str) else "<invalid title>",
                url=url if isinstance(url, str) else "",
                carrier_state=None,
                successor=None,
                explanation="number must be a positive exact integer",
            )
        ]
    if not isinstance(title, str):
        return [
            _malformed(
                number=number,
                title="<invalid title>",
                url=url if isinstance(url, str) else "",
                carrier_state=None,
                successor=None,
                explanation="title must be a string",
            )
        ]
    if not isinstance(body, str):
        return [
            _malformed(
                number=number,
                title=title,
                url=url if isinstance(url, str) else "",
                carrier_state=None,
                successor=None,
                explanation="body must be a string",
            )
        ]
    if not isinstance(url, str):
        return [
            _malformed(
                number=number,
                title=title,
                url="",
                carrier_state=None,
                successor=None,
                explanation="url must be a string",
            )
        ]
    if not isinstance(state_value, str):
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=None,
                successor=None,
                explanation="state must be a string when present",
            )
        ]
    if state_value.upper() != "OPEN":
        return []

    fields = _field_values(body)
    state_values = fields["carrier_state"]
    successor_values = fields["successor"]
    if not state_values and not successor_values:
        return []

    preview_state = state_values[0].lower() if len(state_values) == 1 else None
    preview_successor = successor_values[0].lower() if len(successor_values) == 1 else None

    if len(state_values) != 1 or len(successor_values) != 1:
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=preview_state,
                successor=preview_successor,
                explanation=(
                    "an opted-in open pull request must declare exactly one "
                    "Carrier state and exactly one Successor field"
                ),
            )
        ]

    state = state_values[0].lower()
    successor = successor_values[0].lower()
    if state not in ALLOWED_STATES:
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=state,
                successor=successor,
                explanation=f"unsupported carrier state: {state!r}",
            )
        ]

    successor_is_none = successor == "none"
    successor_match = SUCCESSOR_RE.fullmatch(successor)
    if not successor_is_none and successor_match is None:
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=state,
                successor=successor,
                explanation="Successor must be 'none' or an exact #NUMBER",
            )
        ]
    if successor_match is not None and int(successor_match.group(1)) == number:
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=state,
                successor=successor,
                explanation="a pull request cannot name itself as successor",
            )
        ]

    if state in {"active", "stopped"} and not successor_is_none:
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=state,
                successor=successor,
                explanation=f"{state} requires Successor: none",
            )
        ]
    if state in {"component-evidence", "superseded"} and successor_match is None:
        return [
            _malformed(
                number=number,
                title=title,
                url=url,
                carrier_state=state,
                successor=successor,
                explanation=f"{state} requires an exact successor pull request",
            )
        ]

    if state in TERMINAL_STATES:
        return [
            Finding(
                number=number,
                title=title,
                kind="terminal-carrier-open",
                carrier_state=state,
                successor=successor,
                explanation=(
                    f"open pull request explicitly declares terminal carrier "
                    f"state {state!r}"
                ),
                url=url,
            )
        ]
    return []


def audit(items: Any) -> list[Finding]:
    if not isinstance(items, list):
        return [
            _malformed(
                number=0,
                title="<invalid document>",
                url="",
                carrier_state=None,
                successor=None,
                explanation="input JSON must be a list",
            )
        ]
    findings: list[Finding] = []
    for item in items:
        findings.extend(classify_pull_request(item))
    return findings


def _load_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _render_text(findings: Iterable[Finding]) -> str:
    lines = []
    for finding in findings:
        state = finding.carrier_state or "unknown"
        successor = finding.successor or "unknown"
        lines.append(
            f"PR #{finding.number}: {finding.kind}: state={state} "
            f"successor={successor}: {finding.explanation}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit explicit carrier-state fields on open pull requests."
    )
    parser.add_argument("input", help="JSON path, or - for stdin")
    parser.add_argument("--json", action="store_true", help="emit JSON findings")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document = _load_json(args.input)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"carrier-state audit input error: {exc}", file=sys.stderr)
        return 2

    findings = audit(document)
    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2, sort_keys=True))
    else:
        rendered = _render_text(findings)
        if rendered:
            print(rendered)
        else:
            print("carrier-state audit: no findings")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
