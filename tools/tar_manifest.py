#!/usr/bin/env python3
"""Create a deterministic JSON Lines manifest for a tar archive.

The manifest records archive metadata before extraction can discard or rewrite it.
It is intended for root filesystem and VM root build research.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import PurePosixPath
from typing import BinaryIO, Iterable, Iterator

BLOCK_SIZE = 1024 * 1024
PAX_FIELDS_REPRESENTED_DIRECTLY = frozenset(
    {
        "path",
        "linkpath",
        "size",
        "uid",
        "gid",
        "uname",
        "gname",
        "mtime",
    }
)


def normalized_name(name: str) -> str:
    """Return a stable relative POSIX path without a leading './'."""
    while name.startswith("./"):
        name = name[2:]
    if name == ".":
        return ""
    return str(PurePosixPath(name))


def member_type(member: tarfile.TarInfo) -> str:
    if member.isfile():
        return "file"
    if member.isdir():
        return "directory"
    if member.issym():
        return "symlink"
    if member.islnk():
        return "hardlink"
    if member.ischr():
        return "character-device"
    if member.isblk():
        return "block-device"
    if member.isfifo():
        return "fifo"
    raw_type = member.type
    if isinstance(raw_type, bytes):
        raw_type = raw_type.decode("ascii", errors="backslashreplace")
    return f"other:{raw_type}"


def sha256_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = stream.read(BLOCK_SIZE)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def extra_pax_headers(member: tarfile.TarInfo) -> dict[str, str]:
    """Return PAX metadata that is not already represented by a top-level field."""
    return {
        key: value
        for key, value in sorted(member.pax_headers.items())
        if key not in PAX_FIELDS_REPRESENTED_DIRECTLY
    }


def manifest_entries(archive: tarfile.TarFile) -> Iterator[dict[str, object]]:
    seen_paths: set[str] = set()
    for member in archive:
        path = normalized_name(member.name)
        if path in seen_paths:
            raise ValueError(f"archive contains duplicate path: {path!r}")
        seen_paths.add(path)

        entry: dict[str, object] = {
            "path": path,
            "type": member_type(member),
            "mode": f"{member.mode & 0o7777:04o}",
            "uid": member.uid,
            "gid": member.gid,
            "size": member.size,
            "mtime": member.mtime,
        }

        if member.uname:
            entry["uname"] = member.uname
        if member.gname:
            entry["gname"] = member.gname
        if member.linkname:
            entry["linkname"] = normalized_name(member.linkname)
        if member.ischr() or member.isblk():
            entry["device_major"] = member.devmajor
            entry["device_minor"] = member.devminor
        pax_headers = extra_pax_headers(member)
        if pax_headers:
            entry["pax_headers"] = pax_headers

        if member.isfile():
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to read regular file: {path!r}")
            with extracted:
                entry["sha256"] = sha256_stream(extracted)

        yield entry


def write_manifest(entries: Iterable[dict[str, object]], output: BinaryIO) -> None:
    for entry in sorted(entries, key=lambda item: str(item["path"])):
        line = json.dumps(
            entry,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        output.write(line.encode("utf-8") + b"\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "archive",
        help="tar archive path; compressed tar formats are detected automatically",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output JSONL path; defaults to standard output",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        with tarfile.open(args.archive, mode="r:*") as archive:
            entries = list(manifest_entries(archive))
        if args.output:
            with open(args.output, "wb") as output:
                write_manifest(entries, output)
        else:
            write_manifest(entries, sys.stdout.buffer)
    except (OSError, tarfile.TarError, ValueError) as exc:
        print(f"tar_manifest: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
