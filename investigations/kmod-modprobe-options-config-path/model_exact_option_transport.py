#!/usr/bin/env python3
"""Model a versioned exact argv transport for recursive modprobe options.

This is a policy/mechanism model, not a transcription of kmod C. The current
legacy parser remains outside the model: its already-parsed argv is supplied as
``legacy_argv``. When an exact internal record is present, it is authoritative;
otherwise the current parser's argv is used. The exact record is consumed and
rebuilt once per invocation, preventing recursive duplication.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Iterable

PREFIX = b"KMOD1;"


class DecodeError(ValueError):
    pass


def encode_exact(argv: Iterable[bytes]) -> bytes:
    out = bytearray(PREFIX)
    for arg in argv:
        if b"\0" in arg:
            raise ValueError("argv values cannot contain NUL")
        out.extend(str(len(arg)).encode("ascii"))
        out.extend(b":")
        out.extend(arg)
        out.extend(b",")
    return bytes(out)


def decode_exact(record: bytes) -> list[bytes]:
    if not record.startswith(PREFIX):
        raise DecodeError("unsupported exact-record version")
    pos = len(PREFIX)
    argv: list[bytes] = []
    while pos < len(record):
        colon = record.find(b":", pos)
        if colon < 0:
            raise DecodeError("missing length separator")
        digits = record[pos:colon]
        if not digits or not digits.isdigit():
            raise DecodeError("invalid length")
        if len(digits) > 1 and digits.startswith(b"0"):
            raise DecodeError("non-canonical length")
        length = int(digits)
        start = colon + 1
        end = start + length
        if end >= len(record) or record[end : end + 1] != b",":
            raise DecodeError("truncated value or missing terminator")
        value = record[start:end]
        if b"\0" in value:
            raise DecodeError("NUL is not representable in argv")
        argv.append(value)
        pos = end + 1
    return argv


def legacy_mirror(argv: Iterable[bytes]) -> bytes:
    """Produce a diagnostic/private compatibility mirror, not parse authority."""
    pieces: list[bytes] = []
    escaped = set(b" \t\n\r\v\f\\\"'")
    for arg in argv:
        if not arg:
            pieces.append(b"''")
            continue
        piece = bytearray()
        for byte in arg:
            if byte in escaped:
                piece.append(ord("\\"))
            piece.append(byte)
        pieces.append(bytes(piece))
    return b" ".join(pieces)


def resolve_ingress(*, exact_record: bytes | None, legacy_argv: list[bytes]) -> tuple[list[bytes], str]:
    if exact_record is not None:
        return decode_exact(exact_record), "exact"
    return list(legacy_argv), "legacy"


def canonicalize(argv: list[bytes]) -> tuple[bytes, bytes]:
    return encode_exact(argv), legacy_mirror(argv)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    rng = random.Random(0x4B4D4F44)

    generated_cases = [
        b"",
        b"/config dir",
        b"/tab\tpath",
        b"/line\npath",
        b"/quote'\"path",
        b"/back\\slash",
        bytes(range(1, 256)),
    ]
    for _ in range(10_000):
        size = rng.randrange(0, 65)
        generated_cases.append(bytes(rng.randrange(1, 256) for _ in range(size)))

    roundtrip_record = encode_exact(generated_cases)
    assert decode_exact(roundtrip_record) == generated_cases

    malformed = [
        b"",
        b"KMOD0;",
        b"KMOD1;:",
        b"KMOD1;x:a,",
        b"KMOD1;01:a,",
        b"KMOD1;2:a,",
        b"KMOD1;1:a",
        b"KMOD1;1:\0,",
        b"KMOD1;1:a,trailing",
    ]
    rejected = 0
    for record in malformed:
        try:
            decode_exact(record)
        except DecodeError:
            rejected += 1
        else:
            raise AssertionError(f"malformed record accepted: {record!r}")

    legacy_cases = [
        [b"-C", b"/foo\\bar"],
        [b"-C", b"/foo\\"],
        [b"-C", b"/foo\\'bar"],
    ]
    for legacy_argv in legacy_cases:
        resolved, source = resolve_ingress(exact_record=None, legacy_argv=legacy_argv)
        assert source == "legacy"
        assert resolved == legacy_argv

    exact_args = [b"-C", b"/config dir", b"-C", b"", b"-q"]
    exact_record, mirror = canonicalize(exact_args)
    resolved, source = resolve_ingress(
        exact_record=exact_record,
        legacy_argv=[b"-C", b"/legacy\\path"],
    )
    assert source == "exact"
    assert resolved == exact_args

    recursion = []
    record = exact_record
    for level in range(1, 21):
        inherited, source = resolve_ingress(exact_record=record, legacy_argv=[])
        assert source == "exact"
        assert inherited == exact_args
        next_record, next_mirror = canonicalize(inherited)
        assert next_record == record
        assert next_mirror == mirror
        recursion.append(
            {
                "level": level,
                "argc": len(inherited),
                "exact_bytes": len(next_record),
                "mirror_bytes": len(next_mirror),
            }
        )
        record = next_record

    source_bytes = Path(__file__).read_bytes()
    result = {
        "model": "versioned-length-delimited-recursive-option-transport",
        "evidence_class": "model-executed",
        "source_sha256": sha256(source_bytes),
        "record_prefix": PREFIX.decode("ascii"),
        "generated_roundtrip_cases": len(generated_cases),
        "generated_record_sha256": sha256(roundtrip_record),
        "malformed_records_rejected": rejected,
        "legacy_raw_backslash_cases_preserved": len(legacy_cases),
        "exact_precedence_when_both_present": True,
        "canonical_exact_record_hex": exact_record.hex(),
        "canonical_exact_record_sha256": sha256(exact_record),
        "canonical_legacy_mirror_hex": mirror.hex(),
        "recursion": recursion,
        "recursion_stable": len({(r["argc"], r["exact_bytes"], r["mirror_bytes"]) for r in recursion}) == 1,
        "policy_boundary": (
            "Current legacy parsing is used only when no exact internal record exists. "
            "An exact record is consumed and rebuilt once per invocation. The legacy "
            "mirror is not parse authority when an exact record is present."
        ),
        "not_established": [
            "compiled C behavior",
            "environment-size limits on supported platforms",
            "maintainer acceptance of a second private environment variable",
            "ordering when hostile callers inject both variables",
            "integration with every install/remove command topology",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
