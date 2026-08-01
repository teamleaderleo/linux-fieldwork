#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import tarfile
import tempfile


def tar_version() -> str:
    return subprocess.check_output(["tar", "--version"], text=True).splitlines()[0]


def archive(path: pathlib.Path, name: str, *, directory: bool = False) -> None:
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as handle:
        member = tarfile.TarInfo(name)
        member.mode = 0o751 if directory else 0o640
        member.mtime = 946684800
        if directory:
            member.type = tarfile.DIRTYPE
            handle.addfile(member)
        else:
            payload = (name + "\n").encode()
            member.size = len(payload)
            handle.addfile(member, io.BytesIO(payload))


def extract_case(base: pathlib.Path, index: int, name: str, *, directory: bool = False):
    source = base / f"case-{index}.tar"
    target = base / f"target-{index}"
    target.mkdir(mode=0o755)
    archive(source, name, directory=directory)
    result = subprocess.run(
        ["tar", "-xf", str(source), "-C", str(target)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    paths = []
    for path in sorted(target.rglob("*")):
        paths.append(
            {
                "path": str(path.relative_to(target)),
                "kind": "directory" if path.is_dir() else "file",
                "mode": oct(path.stat().st_mode & 0o777),
            }
        )
    return {
        "name": name,
        "status": result.returncode,
        "target_mode": oct(target.stat().st_mode & 0o777),
        "paths": paths,
        "stderr": result.stderr.splitlines(),
    }


leading_aliases = (
    ".config",
    "./.config",
    "././.config",
    "/./.config",
    "//./.config",
    ".//.config",
    "/.//.config",
)
root_aliases = (".", "./", "./.", "/.", "/./", "//./.")
internal_aliases = ("foo/./.config", "foo/.config")
traversal = ("..", "../config", "./../config")

with tempfile.TemporaryDirectory(prefix="unit20-gnu-tar-") as temporary:
    base = pathlib.Path(temporary)
    rows = []
    index = 0
    for name in leading_aliases:
        rows.append(extract_case(base, index, name))
        index += 1
    for name in root_aliases:
        rows.append(extract_case(base, index, name, directory=True))
        index += 1
    for name in internal_aliases + traversal:
        rows.append(extract_case(base, index, name))
        index += 1

by_name = {row["name"]: row for row in rows}
for name in leading_aliases:
    row = by_name[name]
    assert row["status"] == 0, row
    assert row["paths"] == [{"path": ".config", "kind": "file", "mode": "0o640"}], row
for name in root_aliases:
    row = by_name[name]
    assert row["status"] == 0, row
    assert row["paths"] == [], row
    assert row["target_mode"] == "0o751", row
for name in internal_aliases:
    row = by_name[name]
    assert row["status"] == 0, row
    assert row["paths"][-1]["path"] == "foo/.config", row
for name in traversal:
    row = by_name[name]
    assert row["status"] != 0, row
    assert row["paths"] == [], row

print(
    json.dumps(
        {
            "tar": tar_version(),
            "leading_aliases": list(leading_aliases),
            "root_aliases": list(root_aliases),
            "internal_dot_segment_successor": list(internal_aliases),
            "rejected_parent_components": list(traversal),
            "rows": rows,
        },
        indent=2,
        sort_keys=True,
    )
)
