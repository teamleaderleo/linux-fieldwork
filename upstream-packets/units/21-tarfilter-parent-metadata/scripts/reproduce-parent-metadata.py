#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

PREFIX_PROG = re.compile(r"^([^*?[\\]*).*")

@dataclass(frozen=True)
class Rule:
    kind: str
    glob: str
    regex: re.Pattern[str]


def rules(*items: tuple[str, str]) -> list[Rule]:
    return [Rule(kind, glob, re.compile(fnmatch.translate(glob))) for kind, glob in items]


def normalized_name(member: tarfile.TarInfo) -> str:
    # Matches current tarfilter's relevant normalization. Dotfile identity is a separate unit.
    return "/" + member.name.lstrip("./")


def baseline_should_skip(member: tarfile.TarInfo, pathfilter: list[Rule]) -> bool:
    name = normalized_name(member)
    skip = False
    for rule in pathfilter:
        if rule.regex.match(name) is not None:
            skip = rule.kind == "path_exclude"
    if skip and (member.isdir() or member.issym()):
        for rule in pathfilter:
            if rule.kind != "path_include":
                continue
            prefix = PREFIX_PROG.sub(r"\1", rule.regex.pattern).rstrip("/")
            if name.startswith(prefix):
                return False
    return skip


def include_can_match_member_or_descendant(name: str, include_glob: str) -> bool:
    """Conservative descendant relation using the original glob's literal prefix.

    The fixed prefix can be above the candidate directory, below it, or empty because
    a wildcard appears first. All comparisons use pathname-component boundaries.
    """
    candidate = name.rstrip("/") or "/"
    prefix = PREFIX_PROG.sub(r"\1", include_glob).rstrip("/") or "/"
    if prefix == "/":
        return True
    return (
        candidate == prefix
        or candidate.startswith(prefix + "/")
        or prefix.startswith(candidate + "/")
    )


def candidate_should_skip(member: tarfile.TarInfo, pathfilter: list[Rule]) -> bool:
    name = normalized_name(member)
    skip = False
    for rule in pathfilter:
        if rule.regex.match(name) is not None:
            skip = rule.kind == "path_exclude"
    if skip and (member.isdir() or member.issym()):
        for rule in pathfilter:
            if rule.kind != "path_include":
                continue
            if include_can_match_member_or_descendant(name, rule.glob):
                return False
    return skip


def add_dir(tf: tarfile.TarFile, name: str, mode: int, uid: int, gid: int, mtime: int, marker: str) -> None:
    ti = tarfile.TarInfo(name)
    ti.type = tarfile.DIRTYPE
    ti.mode = mode
    ti.uid = uid
    ti.gid = gid
    ti.mtime = mtime
    ti.pax_headers = {"SCHILY.xattr.user.unit21": marker}
    tf.addfile(ti)


def add_file(tf: tarfile.TarFile, name: str, data: bytes, mode: int, uid: int, gid: int, mtime: int) -> None:
    ti = tarfile.TarInfo(name)
    ti.type = tarfile.REGTYPE
    ti.mode = mode
    ti.uid = uid
    ti.gid = gid
    ti.mtime = mtime
    ti.size = len(data)
    tf.addfile(ti, io.BytesIO(data))


def add_symlink(tf: tarfile.TarFile, name: str, target: str, mode: int, mtime: int) -> None:
    ti = tarfile.TarInfo(name)
    ti.type = tarfile.SYMTYPE
    ti.linkname = target
    ti.mode = mode
    ti.uid = 44
    ti.gid = 55
    ti.mtime = mtime
    ti.pax_headers = {"SCHILY.xattr.user.unit21": "symlink-parent"}
    tf.addfile(ti)


def make_input(path: Path) -> None:
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as tf:
        add_dir(tf, "usr", 0o700, 11, 21, 1_700_000_001, "usr-parent")
        add_dir(tf, "usr/bin", 0o711, 12, 22, 1_700_000_002, "bin-parent")
        add_file(tf, "usr/bin/tool", b"tool\n", 0o755, 13, 23, 1_700_000_003)
        add_dir(tf, "usr2", 0o750, 14, 24, 1_700_000_004, "boundary-control")
        add_file(tf, "usr2/tool", b"other\n", 0o755, 15, 25, 1_700_000_005)
        add_dir(tf, "opt", 0o705, 16, 26, 1_700_000_006, "unrelated-control")
        add_file(tf, "opt/tool", b"opt\n", 0o755, 17, 27, 1_700_000_007)
        add_symlink(tf, "linkroot", "usr/bin", 0o777, 1_700_000_008)
        add_file(tf, "linkroot/tool", b"linked\n", 0o744, 18, 28, 1_700_000_009)


def filter_tar(src: Path, dst: Path, pathfilter: list[Rule], predicate) -> None:
    with tarfile.open(src, "r") as inf, tarfile.open(dst, "w", format=tarfile.PAX_FORMAT) as outf:
        for member in inf:
            if predicate(member, pathfilter):
                continue
            fileobj = inf.extractfile(member) if member.isfile() else None
            outf.addfile(member, fileobj)


def archive_manifest(path: Path) -> list[dict[str, object]]:
    out = []
    with tarfile.open(path, "r") as tf:
        for m in tf:
            out.append({
                "name": m.name,
                "type": "dir" if m.isdir() else "symlink" if m.issym() else "file",
                "mode": f"{m.mode:04o}",
                "uid": m.uid,
                "gid": m.gid,
                "mtime": m.mtime,
                "linkname": m.linkname,
                "pax": dict(sorted(m.pax_headers.items())),
            })
    return out


def extracted_modes(path: Path) -> dict[str, str]:
    root = path.parent / (path.stem + "-root")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    os.chmod(root, 0o755)
    subprocess.run(
        ["tar", "--no-same-owner", "-xf", str(path.resolve())],
        cwd=root,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    result = {}
    for rel in ("usr", "usr/bin", "usr/bin/tool"):
        p = root / rel
        if p.exists():
            result[rel] = f"{stat.S_IMODE(p.stat().st_mode):04o}"
    shutil.rmtree(root)
    return result


def relation_matrix() -> list[dict[str, object]]:
    cases = [
        ("exact ancestors", "/usr", "/usr/bin/tool", True),
        ("exact immediate parent", "/usr/bin", "/usr/bin/tool", True),
        ("fixed-prefix ancestor", "/usr", "/usr/bin/*", True),
        ("wildcard descendant", "/usr/bin", "/usr/*/tool", True),
        ("character-class descendant", "/usr/bin", "/usr/[bs]in/tool", True),
        ("component boundary", "/usr", "/usr2/tool", False),
        ("unrelated", "/opt", "/usr/bin/tool", False),
        ("leading wildcard conservative", "/opt", "*/tool", True),
        ("symlink parent exact descendant", "/linkroot", "/linkroot/tool", True),
    ]
    rows = []
    for label, name, glob, expected in cases:
        got = include_can_match_member_or_descendant(name, glob)
        if got != expected:
            raise AssertionError((label, name, glob, expected, got))
        rows.append({"case": label, "member": name, "include": glob, "retained": got})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args()
    owned = args.workdir is None
    workdir = Path(tempfile.mkdtemp(prefix="unit21-")) if owned else args.workdir
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        src = workdir / "input.tar"
        baseline = workdir / "baseline.tar"
        candidate = workdir / "candidate.tar"
        make_input(src)
        pathfilter = rules(("path_exclude", "/*"), ("path_include", "/usr/bin/tool"))
        filter_tar(src, baseline, pathfilter, baseline_should_skip)
        filter_tar(src, candidate, pathfilter, candidate_should_skip)

        base_manifest = archive_manifest(baseline)
        cand_manifest = archive_manifest(candidate)
        base_names = [row["name"] for row in base_manifest]
        cand_names = [row["name"] for row in cand_manifest]
        assert base_names == ["usr/bin/tool"], base_names
        assert cand_names == ["usr", "usr/bin", "usr/bin/tool"], cand_names
        assert cand_manifest[0]["mode"] == "0700"
        assert cand_manifest[1]["mode"] == "0711"
        assert cand_manifest[0]["pax"]["SCHILY.xattr.user.unit21"] == "usr-parent"
        assert cand_manifest[1]["pax"]["SCHILY.xattr.user.unit21"] == "bin-parent"

        symlink_baseline = workdir / "symlink-baseline.tar"
        symlink_candidate = workdir / "symlink-candidate.tar"
        symlink_rules = rules(
            ("path_exclude", "/*"), ("path_include", "/linkroot/tool")
        )
        filter_tar(src, symlink_baseline, symlink_rules, baseline_should_skip)
        filter_tar(src, symlink_candidate, symlink_rules, candidate_should_skip)
        symlink_base_manifest = archive_manifest(symlink_baseline)
        symlink_cand_manifest = archive_manifest(symlink_candidate)
        assert [row["name"] for row in symlink_base_manifest] == ["linkroot/tool"]
        assert [row["name"] for row in symlink_cand_manifest] == [
            "linkroot",
            "linkroot/tool",
        ]
        assert symlink_cand_manifest[0]["type"] == "symlink"
        assert symlink_cand_manifest[0]["linkname"] == "usr/bin"
        assert symlink_cand_manifest[0]["uid"] == 44
        assert symlink_cand_manifest[0]["gid"] == 55
        assert symlink_cand_manifest[0]["mtime"] == 1_700_000_008
        assert (
            symlink_cand_manifest[0]["pax"]["SCHILY.xattr.user.unit21"]
            == "symlink-parent"
        )

        result = {
            "python": os.sys.version.split()[0],
            "baseline": {
                "members": base_manifest,
                "extracted_modes": extracted_modes(baseline),
            },
            "candidate": {
                "members": cand_manifest,
                "extracted_modes": extracted_modes(candidate),
            },
            "symlink_case": {
                "baseline": symlink_base_manifest,
                "candidate": symlink_cand_manifest,
            },
            "relation_matrix": relation_matrix(),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        if owned:
            shutil.rmtree(workdir)


if __name__ == "__main__":
    raise SystemExit(main())
