#!/usr/bin/env python3
"""Summarize one retained mmdebstrap autopkgtest reproduction artifact."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Sequence

try:
    from tools.audit_pr_evidence_identity import IdentityError, build_receipt
    from tools.mmdebstrap_autopkgtest_log import DETAIL_RE, TEST_RE, classify_text
except ModuleNotFoundError:  # direct script execution from tools/
    from audit_pr_evidence_identity import IdentityError, build_receipt
    from mmdebstrap_autopkgtest_log import DETAIL_RE, TEST_RE, classify_text


FOCUS_TEST = "root-without-cap-sys-admin"
STATUS_RE = re.compile(r"^[0-9]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ArtifactSummaryError(ValueError):
    """Raised when the artifact layout or receipt is ambiguous."""


def _one(root: pathlib.Path, basename: str) -> pathlib.Path:
    matches = sorted(path for path in root.rglob(basename) if path.name == basename)
    if len(matches) != 1:
        raise ArtifactSummaryError(
            f"expected exactly one {basename}, found {len(matches)}"
        )
    path = matches[0]
    if path.is_symlink():
        raise ArtifactSummaryError(f"required artifact path is a symlink: {path}")
    if not path.is_file():
        raise ArtifactSummaryError(f"required artifact path is not a file: {path}")
    return path


def _read_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ArtifactSummaryError(f"invalid JSON at {path}: {error}") from error


def _read_status(path: pathlib.Path) -> int:
    value = path.read_text(encoding="utf-8").strip()
    if STATUS_RE.fullmatch(value) is None:
        raise ArtifactSummaryError(f"status is not a nonnegative decimal integer: {path}")
    return int(value)


def _require_string(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise ArtifactSummaryError(f"{field} must be a nonempty exact string")
    return value


def _require_sha(value: Any, field: str) -> str:
    text = _require_string(value, field)
    if SHA_RE.fullmatch(text) is None:
        raise ArtifactSummaryError(f"{field} must be a lowercase 40-hex SHA")
    return text


def _parse_named_tests(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = TEST_RE.search(line)
        if match:
            if current is not None:
                records.append(current)
            current = {
                "line": line_number,
                "index": int(match.group("index")),
                "total": int(match.group("total")),
                "name": match.group("name"),
                "outcome": None,
                "outcome_line": None,
            }
        if current is not None:
            for detail in DETAIL_RE.finditer(line):
                current[detail.group("key")] = detail.group("value")
            lower = line.lower()
            if "result: success" in lower:
                current["outcome"] = "success"
                current["outcome_line"] = line_number
                records.append(current)
                current = None
            elif "result: failure" in lower:
                current["outcome"] = "failure"
                current["outcome_line"] = line_number
                records.append(current)
                current = None
    if current is not None:
        records.append(current)
    return records


def _context(lines: list[str], line_number: int | None, radius: int = 5) -> list[str]:
    if line_number is None:
        return lines[-min(len(lines), 30) :]
    start = max(0, line_number - radius - 1)
    end = min(len(lines), line_number + radius)
    return [f"{index + 1}: {lines[index]}" for index in range(start, end)]


def summarize_artifact(
    root: pathlib.Path,
    *,
    expected_head: str,
    expected_base: str,
    expected_checkout: str,
    expected_run_id: str,
    expected_run_attempt: str,
    artifact_id: str,
    artifact_digest: str,
) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ArtifactSummaryError(f"artifact root is not a directory: {root}")

    expected_head = _require_sha(expected_head, "expected_head")
    expected_base = _require_sha(expected_base, "expected_base")
    expected_checkout = _require_sha(expected_checkout, "expected_checkout")
    if not expected_run_id.isdecimal() or int(expected_run_id) <= 0:
        raise ArtifactSummaryError("expected_run_id must be a positive decimal string")
    if not expected_run_attempt.isdecimal() or int(expected_run_attempt) <= 0:
        raise ArtifactSummaryError("expected_run_attempt must be a positive decimal string")
    if not artifact_id.isdecimal() or int(artifact_id) <= 0:
        raise ArtifactSummaryError("artifact_id must be a positive decimal string")
    if DIGEST_RE.fullmatch(artifact_digest) is None:
        raise ArtifactSummaryError("artifact_digest must be sha256:<64 lowercase hex>")

    identity_input_path = _one(root, "repository-identity-input.json")
    identity_output_path = _one(root, "repository-identity.json")
    revision_path = _one(root, "repository-rev-list.txt")
    console_path = _one(root, "autopkgtest-console.log")
    exit_status_path = _one(root, "exit-status")
    container_status_path = _one(root, "container-exit-status")
    result_path = _one(root, "result.md")
    phase_order_path = _one(root, "phase-order.stdout")

    identity_input = _read_json(identity_input_path)
    try:
        rebuilt = build_receipt(identity_input)
    except (IdentityError, KeyError, TypeError) as error:
        raise ArtifactSummaryError(f"identity input is invalid: {error}") from error
    rebuilt_json = json.loads(json.dumps(dataclasses.asdict(rebuilt)))
    identity_output = _read_json(identity_output_path)
    if identity_output != rebuilt_json:
        raise ArtifactSummaryError("typed identity receipt does not match its retained input")

    if rebuilt.classification != "synthetic-merge-ref":
        raise ArtifactSummaryError(
            f"expected synthetic-merge-ref, observed {rebuilt.classification}"
        )
    if rebuilt.head_sha != expected_head:
        raise ArtifactSummaryError(
            f"head mismatch: expected {expected_head}, observed {rebuilt.head_sha}"
        )
    if rebuilt.base_sha != expected_base:
        raise ArtifactSummaryError(
            f"base mismatch: expected {expected_base}, observed {rebuilt.base_sha}"
        )
    if rebuilt.checkout_sha != expected_checkout:
        raise ArtifactSummaryError(
            "checkout mismatch: "
            f"expected {expected_checkout}, observed {rebuilt.checkout_sha}"
        )
    if rebuilt.parents != (expected_base, expected_head):
        raise ArtifactSummaryError(
            f"ordered parent mismatch: {rebuilt.parents!r}"
        )
    if rebuilt.run_id != expected_run_id:
        raise ArtifactSummaryError(
            f"run id mismatch: expected {expected_run_id}, observed {rebuilt.run_id}"
        )
    if rebuilt.run_attempt != expected_run_attempt:
        raise ArtifactSummaryError(
            "run attempt mismatch: "
            f"expected {expected_run_attempt}, observed {rebuilt.run_attempt}"
        )

    revision_fields = revision_path.read_text(encoding="utf-8").strip().split()
    expected_revision = [expected_checkout, expected_base, expected_head]
    if revision_fields != expected_revision:
        raise ArtifactSummaryError(
            f"raw revision line mismatch: expected {expected_revision!r}, "
            f"observed {revision_fields!r}"
        )

    exit_status = _read_status(exit_status_path)
    container_status = _read_status(container_status_path)
    if exit_status != container_status:
        raise ArtifactSummaryError(
            f"status mismatch: script={exit_status}, container={container_status}"
        )

    result_text = result_path.read_text(encoding="utf-8", errors="replace")
    if f"Exit status: `{exit_status}`" not in result_text:
        raise ArtifactSummaryError("result.md does not carry the retained exit status")
    if "Repository checkout classification: `synthetic-merge-ref`" not in result_text:
        raise ArtifactSummaryError("result.md does not carry the checkout classification")

    console_text = console_path.read_text(encoding="utf-8", errors="replace")
    console_sha256 = hashlib.sha256(console_path.read_bytes()).hexdigest()
    classifier = classify_text(console_text)
    named_tests = _parse_named_tests(console_text)
    focus_records = [record for record in named_tests if record["name"] == FOCUS_TEST]
    focus_outcomes = [record["outcome"] for record in focus_records]
    if not focus_records:
        focus_state = "absent"
    elif "failure" in focus_outcomes:
        focus_state = "failed"
    elif "success" in focus_outcomes:
        focus_state = "passed"
    else:
        focus_state = "unresolved"

    first_failure_line = classifier["first_failure_line"]
    focus_first_line = focus_records[0]["line"] if focus_records else None
    focus_before_first_failure = (
        focus_first_line is not None
        and first_failure_line is not None
        and focus_first_line < first_failure_line
    )
    focus_completed_before_first_failure = (
        focus_state == "passed"
        and focus_records[0]["outcome_line"] is not None
        and first_failure_line is not None
        and focus_records[0]["outcome_line"] < first_failure_line
    )

    console_lines = console_text.splitlines()
    phase_order_text = phase_order_path.read_text(
        encoding="utf-8", errors="replace"
    ).strip()

    return {
        "schema_version": 1,
        "artifact": {
            "id": artifact_id,
            "digest": artifact_digest,
            "root": str(root),
        },
        "repository_identity": rebuilt_json,
        "statuses": {
            "script": exit_status,
            "container": container_status,
        },
        "console": {
            "path": str(console_path.relative_to(root)),
            "sha256": console_sha256,
            "line_count": len(console_lines),
            "named_test_count": len(named_tests),
            "classifier": classifier,
            "failure_context": _context(console_lines, first_failure_line),
            "tail": console_lines[-min(len(console_lines), 30) :],
        },
        "focus_case": {
            "name": FOCUS_TEST,
            "state": focus_state,
            "occurrences": focus_records,
            "before_first_failure": focus_before_first_failure,
            "completed_before_first_failure": focus_completed_before_first_failure,
        },
        "phase_order_receipt": phase_order_text,
        "result_markdown": result_text,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and summarize one extracted mmdebstrap reproduction artifact."
        )
    )
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-base", required=True)
    parser.add_argument("--expected-checkout", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-run-attempt", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--output", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = summarize_artifact(
            args.root,
            expected_head=args.expected_head,
            expected_base=args.expected_base,
            expected_checkout=args.expected_checkout,
            expected_run_id=args.expected_run_id,
            expected_run_attempt=args.expected_run_attempt,
            artifact_id=args.artifact_id,
            artifact_digest=args.artifact_digest,
        )
    except (OSError, UnicodeError, ArtifactSummaryError) as error:
        print(f"mmdebstrap artifact receipt error: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
