#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import tarfile
import tempfile


def tar_bytes(entries, *, gzip: bool = False) -> bytes:
    output = io.BytesIO()
    mode = "w:gz" if gzip else "w"
    with tarfile.open(fileobj=output, mode=mode, format=tarfile.GNU_FORMAT) as archive:
        for name, payload, member_type in entries:
            member = tarfile.TarInfo(name)
            member.mode = 0o755 if member_type == tarfile.DIRTYPE else 0o640
            member.uid = 0
            member.gid = 0
            member.mtime = 946684800
            member.type = member_type
            member.size = 0 if member_type == tarfile.DIRTYPE else len(payload)
            archive.addfile(
                member,
                None if member_type == tarfile.DIRTYPE else io.BytesIO(payload),
            )
    return output.getvalue()


def build_deb(case: pathlib.Path, package: str, name: str) -> pathlib.Path:
    control = (
        f"Package: {package}\n"
        "Version: 1\n"
        "Architecture: all\n"
        "Maintainer: Linux Fieldwork <nobody@example.invalid>\n"
        "Description: path-filter probe\n"
    ).encode()
    (case / "debian-binary").write_bytes(b"2.0\n")
    (case / "control.tar.gz").write_bytes(
        tar_bytes([("./control", control, tarfile.REGTYPE)], gzip=True)
    )
    (case / "data.tar").write_bytes(
        tar_bytes([(name, (name + "\n").encode(), tarfile.REGTYPE)])
    )
    result = subprocess.run(
        ["ar", "rc", f"{package}.deb", "debian-binary", "control.tar.gz", "data.tar"],
        cwd=case,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return case / f"{package}.deb"


def run_case(base: pathlib.Path, index: int, name: str, pattern: str):
    case = base / f"case-{index}"
    case.mkdir()
    package = f"unit20probe{index}"
    package_path = build_deb(case, package, name)
    root = case / "root"
    admindir = root / "var/lib/dpkg"
    admindir.mkdir(parents=True)
    (admindir / "status").write_text("")
    result = subprocess.run(
        [
            "dpkg",
            f"--root={root}",
            f"--admindir={admindir}",
            f"--path-exclude={pattern}",
            "--unpack",
            str(package_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    payload_paths = []
    for path in sorted(case.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(case)
        if relative.parts[0] != "root" or relative.parts[:4] == ("root", "var", "lib", "dpkg"):
            continue
        payload_paths.append(str(relative))
    return {
        "name": name,
        "pattern": pattern,
        "status": result.returncode,
        "payload_paths": payload_paths,
        "stderr": result.stderr.splitlines(),
    }


cases = (
    ("./.config", "/.config"),
    ("./.config", "/config"),
    ("./config", "/config"),
    ("./config", "/.config"),
    ("./..name", "/..name"),
    ("./...name", "/...name"),
    (".config", "/.config"),
    ("././.config", "/.config"),
)

with tempfile.TemporaryDirectory(prefix="unit20-dpkg-") as temporary:
    base = pathlib.Path(temporary)
    rows = [run_case(base, index, name, pattern) for index, (name, pattern) in enumerate(cases)]

for row in rows:
    assert row["status"] == 0, row
by_case = {(row["name"], row["pattern"]): row for row in rows}
assert by_case[("./.config", "/.config")]["payload_paths"] == []
assert by_case[("./.config", "/config")]["payload_paths"] == ["root/.config"]
assert by_case[("./config", "/config")]["payload_paths"] == []
assert by_case[("./config", "/.config")]["payload_paths"] == ["root/config"]
assert by_case[("./..name", "/..name")]["payload_paths"] == []
assert by_case[("./...name", "/...name")]["payload_paths"] == []
assert by_case[(".config", "/.config")]["payload_paths"] == ["root/.config"]
assert by_case[("././.config", "/.config")]["payload_paths"] == ["root/.config"]

print(
    json.dumps(
        {
            "dpkg": subprocess.check_output(["dpkg", "--version"], text=True).splitlines()[0],
            "interpretation": {
                "native_member_form": "dpkg path filters match the ordinary ./path package-member spelling",
                "boundary": "bare and repeated ./ prefixes extract to the same consumer pathname but are outside dpkg's native filter match",
            },
            "rows": rows,
        },
        indent=2,
        sort_keys=True,
    )
)
