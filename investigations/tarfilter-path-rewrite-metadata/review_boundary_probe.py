#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


def regular(name: str, payload: bytes = b"payload\n") -> tuple[tarfile.TarInfo, bytes]:
    member = tarfile.TarInfo(name)
    member.size = len(payload)
    member.mtime = 946684800
    return member, payload


def hardlink(name: str, target: str) -> tuple[tarfile.TarInfo, None]:
    member = tarfile.TarInfo(name)
    member.type = tarfile.LNKTYPE
    member.linkname = target
    member.mtime = 946684800
    return member, None


def archive_bytes(entries: list[tuple[tarfile.TarInfo, bytes | None]]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for member, payload in entries:
            archive.addfile(member, io.BytesIO(payload) if payload is not None else None)
    return output.getvalue()


def extract(archive: Path, target: Path, *options: str) -> dict[str, object]:
    target.mkdir()
    completed = subprocess.run(
        ["tar", *options, "-xf", str(archive), "-C", str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rows = []
    for path in sorted(target.rglob("*")):
        relative = str(path.relative_to(target))
        stat = path.lstat()
        rows.append(
            {
                "path": relative,
                "kind": "dir" if path.is_dir() else "symlink" if path.is_symlink() else "file",
                "inode": stat.st_ino,
                "nlink": stat.st_nlink,
                "size": stat.st_size,
            }
        )
    return {
        "status": completed.returncode,
        "stderr": completed.stderr,
        "tree": rows,
    }


def manifest(data: bytes) -> list[dict[str, object]]:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        return [
            {
                "name": member.name,
                "type": member.type.decode("ascii", "replace"),
                "linkname": member.linkname,
                "pax_headers": member.pax_headers,
            }
            for member in archive
        ]


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    source = repo / "upstream/mmdebstrap/tarfilter"
    patch = Path(__file__).with_name("tarfilter-path-rewrite-metadata.patch")
    cases = {
        "standard": [
            regular("prefix/base"),
            hardlink("prefix/peer", "prefix/base"),
        ],
        "link-leading-dot": [
            regular("prefix/base"),
            hardlink("prefix/peer", "./prefix/base"),
        ],
        "member-and-link-leading-dot": [
            regular("./prefix/base"),
            hardlink("./prefix/peer", "./prefix/base"),
        ],
        "link-repeated-slash": [
            regular("prefix/base"),
            hardlink("prefix/peer", "prefix//base"),
        ],
    }

    with tempfile.TemporaryDirectory(prefix="tarfilter-path-boundary-") as td:
        root = Path(td)
        candidate_repo = root / "candidate"
        candidate = candidate_repo / "upstream/mmdebstrap/tarfilter"
        candidate.parent.mkdir(parents=True)
        shutil.copy2(source, candidate)
        applied = subprocess.run(
            ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            print(applied.stdout + applied.stderr, file=sys.stderr)
            return 2

        results: dict[str, object] = {}
        for label, entries in cases.items():
            case = root / label
            case.mkdir()
            original_data = archive_bytes(entries)
            original = case / "original.tar"
            original.write_bytes(original_data)

            direct_plain = extract(original, case / "direct-plain")
            direct_strip = extract(
                original, case / "direct-strip", "--strip-components=1"
            )

            filtered = subprocess.run(
                [sys.executable, str(candidate), "--strip-components=1"],
                input=original_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            filtered_path = case / "filtered.tar"
            filtered_path.write_bytes(filtered.stdout)
            filtered_extract = (
                extract(filtered_path, case / "filtered-extract")
                if filtered.returncode == 0
                else None
            )
            results[label] = {
                "original_manifest": manifest(original_data),
                "direct_plain": direct_plain,
                "direct_strip": direct_strip,
                "filter_status": filtered.returncode,
                "filter_stderr": filtered.stderr.decode("utf-8", "replace"),
                "filtered_manifest": manifest(filtered.stdout)
                if filtered.returncode == 0
                else None,
                "filtered_extract": filtered_extract,
            }

        print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
