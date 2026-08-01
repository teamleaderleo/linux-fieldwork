#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import tarfile

LARGE_UID = 1_000_000_000
LARGE_GID = 1_000_000_001
SMALL_UID = 1000
SMALL_GID = 1001
SHIFT = 7


def build_fixture() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, uid, gid, payload in (
            ("large", LARGE_UID, LARGE_GID, b"large\n"),
            ("small", SMALL_UID, SMALL_GID, b"small\n"),
        ):
            member = tarfile.TarInfo(name)
            member.uid = uid
            member.gid = gid
            member.mode = 0o640
            member.pax_headers["comment"] = f"keep-{name}"
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def rewrite(data: bytes, shift: int, *, repair: bool) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as source, tarfile.open(
        fileobj=output, mode="w", format=tarfile.PAX_FORMAT
    ) as destination:
        for member in source:
            extracted = source.extractfile(member)
            payload = None if extracted is None else extracted.read()
            if shift < 0 and -shift > member.uid:
                raise ValueError("uid cannot be negative")
            if shift < 0 and -shift > member.gid:
                raise ValueError("gid cannot be negative")
            member.uid += shift
            member.gid += shift
            if repair:
                member.pax_headers.pop("uid", None)
                member.pax_headers.pop("gid", None)
            destination.addfile(
                member,
                None if payload is None else io.BytesIO(payload),
            )
    return output.getvalue()


def inspect(data: bytes) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive:
            extracted = archive.extractfile(member)
            payload = b"" if extracted is None else extracted.read()
            result[member.name] = {
                "uid": member.uid,
                "gid": member.gid,
                "pax": dict(member.pax_headers),
                "payload": payload.decode(),
            }
    return result


def main() -> None:
    fixture = build_fixture()
    original = inspect(fixture)
    baseline = inspect(rewrite(fixture, SHIFT, repair=False))
    candidate_bytes = rewrite(fixture, SHIFT, repair=True)
    candidate = inspect(candidate_bytes)
    roundtrip = inspect(rewrite(candidate_bytes, -SHIFT, repair=True))

    assert original["large"]["pax"]["uid"] == str(LARGE_UID)
    assert original["large"]["pax"]["gid"] == str(LARGE_GID)
    assert baseline["large"]["uid"] == LARGE_UID
    assert baseline["large"]["gid"] == LARGE_GID
    assert baseline["small"]["uid"] == SMALL_UID + SHIFT
    assert baseline["small"]["gid"] == SMALL_GID + SHIFT
    assert candidate["large"]["uid"] == LARGE_UID + SHIFT
    assert candidate["large"]["gid"] == LARGE_GID + SHIFT
    assert candidate["large"]["pax"]["uid"] == str(LARGE_UID + SHIFT)
    assert candidate["large"]["pax"]["gid"] == str(LARGE_GID + SHIFT)
    assert candidate["small"]["uid"] == SMALL_UID + SHIFT
    assert candidate["small"]["gid"] == SMALL_GID + SHIFT
    assert "uid" not in candidate["small"]["pax"]
    assert "gid" not in candidate["small"]["pax"]
    assert candidate["large"]["pax"]["comment"] == "keep-large"
    assert candidate["small"]["pax"]["comment"] == "keep-small"
    assert roundtrip["large"]["uid"] == LARGE_UID
    assert roundtrip["large"]["gid"] == LARGE_GID
    assert roundtrip["small"]["uid"] == SMALL_UID
    assert roundtrip["small"]["gid"] == SMALL_GID
    assert roundtrip["large"]["payload"] == original["large"]["payload"]
    assert roundtrip["small"]["payload"] == original["small"]["payload"]

    print(
        json.dumps(
            {
                "python": __import__("sys").version.split()[0],
                "baseline_large": [
                    baseline["large"]["uid"],
                    baseline["large"]["gid"],
                ],
                "baseline_small": [
                    baseline["small"]["uid"],
                    baseline["small"]["gid"],
                ],
                "candidate_large": [
                    candidate["large"]["uid"],
                    candidate["large"]["gid"],
                ],
                "candidate_large_pax": [
                    candidate["large"]["pax"]["uid"],
                    candidate["large"]["pax"]["gid"],
                ],
                "candidate_small": [
                    candidate["small"]["uid"],
                    candidate["small"]["gid"],
                ],
                "unrelated_pax_preserved": [
                    candidate["large"]["pax"]["comment"],
                    candidate["small"]["pax"]["comment"],
                ],
                "roundtrip": {
                    "large": [
                        roundtrip["large"]["uid"],
                        roundtrip["large"]["gid"],
                    ],
                    "small": [
                        roundtrip["small"]["uid"],
                        roundtrip["small"]["gid"],
                    ],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
