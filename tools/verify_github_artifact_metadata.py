#!/usr/bin/env python3
"""Verify one GitHub Actions artifact metadata response against exact expectations."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any, Sequence


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ArtifactMetadataError(ValueError):
    """Raised when artifact metadata is malformed or contradicts expectations."""


def _positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ArtifactMetadataError(f"{field} must be a positive integer")
    return value


def _expected_positive_int(value: str, field: str) -> int:
    if not value.isdecimal() or int(value) <= 0:
        raise ArtifactMetadataError(f"{field} must be a positive decimal string")
    return int(value)


def _exact_string(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise ArtifactMetadataError(f"{field} must be a nonempty exact string")
    return value


def verify_metadata(
    payload: Any,
    *,
    expected_id: str,
    expected_name: str,
    expected_run_id: str,
    expected_digest: str,
) -> dict[str, object]:
    if type(payload) is not dict:
        raise ArtifactMetadataError("artifact metadata must be an object")

    expected_id_int = _expected_positive_int(expected_id, "expected_id")
    expected_run_id_int = _expected_positive_int(
        expected_run_id, "expected_run_id"
    )
    expected_name = _exact_string(expected_name, "expected_name")
    if DIGEST_RE.fullmatch(expected_digest) is None:
        raise ArtifactMetadataError(
            "expected_digest must be sha256:<64 lowercase hex>"
        )

    artifact_id = _positive_int(payload.get("id"), "artifact id")
    name = _exact_string(payload.get("name"), "artifact name")
    digest = _exact_string(payload.get("digest"), "artifact digest")
    expired = payload.get("expired")
    if type(expired) is not bool:
        raise ArtifactMetadataError("artifact expired must be a boolean")

    workflow_run = payload.get("workflow_run")
    if type(workflow_run) is not dict:
        raise ArtifactMetadataError("artifact workflow_run must be an object")
    run_id = _positive_int(workflow_run.get("id"), "artifact workflow run id")

    if artifact_id != expected_id_int:
        raise ArtifactMetadataError(
            f"artifact id mismatch: expected {expected_id_int}, observed {artifact_id}"
        )
    if name != expected_name:
        raise ArtifactMetadataError(
            f"artifact name mismatch: expected {expected_name!r}, observed {name!r}"
        )
    if run_id != expected_run_id_int:
        raise ArtifactMetadataError(
            "artifact workflow run mismatch: "
            f"expected {expected_run_id_int}, observed {run_id}"
        )
    if digest != expected_digest:
        raise ArtifactMetadataError(
            f"artifact digest mismatch: expected {expected_digest}, observed {digest}"
        )
    if expired:
        raise ArtifactMetadataError("artifact is expired")

    return {
        "schema_version": 1,
        "verified": True,
        "artifact": {
            "id": artifact_id,
            "name": name,
            "digest": digest,
            "expired": expired,
            "workflow_run_id": run_id,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify exact GitHub Actions artifact identity metadata."
    )
    parser.add_argument("metadata", type=pathlib.Path)
    parser.add_argument("--expected-id", required=True)
    parser.add_argument("--expected-name", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-digest", required=True)
    parser.add_argument("--output", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(args.metadata.read_text(encoding="utf-8"))
        receipt = verify_metadata(
            payload,
            expected_id=args.expected_id,
            expected_name=args.expected_name,
            expected_run_id=args.expected_run_id,
            expected_digest=args.expected_digest,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ArtifactMetadataError) as error:
        print(f"GitHub artifact metadata error: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
