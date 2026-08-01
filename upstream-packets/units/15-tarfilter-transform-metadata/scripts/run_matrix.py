#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE = ROOT / "upstream/mmdebstrap/tarfilter"
PREDECESSOR = ROOT / "predecessor/upstream/mmdebstrap/tarfilter"
CANDIDATE = ROOT / "candidate/upstream/mmdebstrap/tarfilter"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def archive_bytes(entries: Iterable[tuple[tarfile.TarInfo, bytes | None]]) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for member, payload in entries:
            archive.addfile(member, io.BytesIO(payload) if payload is not None else None)
    return out.getvalue()


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


def symlink(name: str, target: str) -> tuple[tarfile.TarInfo, None]:
    member = tarfile.TarInfo(name)
    member.type = tarfile.SYMTYPE
    member.linkname = target
    member.mtime = 946684800
    return member, None


def run_filter(path: pathlib.Path, data: bytes, *args: str) -> subprocess.CompletedProcess[bytes]:
    return run([sys.executable, str(path), *args], input=data)


def snapshot(data: bytes) -> dict[str, tuple[str, str, dict[str, str]]]:
    result: dict[str, tuple[str, str, dict[str, str]]] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive:
            if member.islnk():
                kind = "hard"
            elif member.issym():
                kind = "sym"
            elif member.isdir():
                kind = "dir"
            else:
                kind = "file"
            result[member.name] = (kind, member.linkname, dict(member.pax_headers))
    return result


def gnu_transform(expression: str, root: pathlib.Path, *, links: bool = False, name: str = "a/a/a/a") -> bytes:
    source = root / "source"
    source.mkdir(parents=True)
    target = source / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"payload\n")
    names = [name]
    if links:
        os.link(target, source / "hard")
        os.symlink(name, source / "sym")
        names += ["hard", "sym"]
    archive = root / "gnu.tar"
    completed = run([
        "tar", "--format=pax", f"--transform={expression}", "-cf", str(archive),
        "-C", str(source), *names,
    ], text=True)
    if completed.returncode != 0:
        raise AssertionError(f"GNU tar failed for {expression}: {completed.stderr}")
    return archive.read_bytes()


def extract(data: bytes, root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    archive = root.parent / f"{root.name}.tar"
    archive.write_bytes(data)
    root.mkdir()
    return run(["tar", "-xf", str(archive), "-C", str(root)], text=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    results: list[dict[str, object]] = []
    require(shutil.which("tar") is not None, "GNU tar required")

    source = BASELINE.read_bytes()
    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    require(blob == "ad776167a8473d5d15dbe22e850f4f6db35cf278", f"wrong baseline blob: {blob}")
    results.append({"case": "source_identity", "result": "pass", "git_blob": blob})

    simple = archive_bytes([regular("a/a")])
    replacement_cases = {
        "s/a/b/": "b/a",
        "s/a/b/g": "b/b",
        "s/a/[&]/": "[a]/a",
        r"s#a#x\#y#": "x#y/a",
    }
    with tempfile.TemporaryDirectory(prefix="unit15-replacement-") as td:
        work = pathlib.Path(td)
        baseline_default = run_filter(BASELINE, simple, "--transform=s/a/b/")
        require(baseline_default.returncode == 0, baseline_default.stderr.decode("utf-8", "replace"))
        require(list(snapshot(baseline_default.stdout)) == ["b/b"], "baseline first-only negative control lost")
        baseline_g = run_filter(BASELINE, simple, "--transform=s/a/b/g")
        require(baseline_g.returncode != 0, "baseline unexpectedly accepted g")
        for index, (expression, expected) in enumerate(replacement_cases.items()):
            candidate = run_filter(CANDIDATE, simple, f"--transform={expression}")
            require(candidate.returncode == 0, candidate.stderr.decode("utf-8", "replace"))
            require(list(snapshot(candidate.stdout)) == [expected], f"candidate {expression}")
            reference = gnu_transform(expression, work / str(index), name="a/a")
            require(list(snapshot(reference)) == [expected], f"GNU {expression}")
            require(snapshot(candidate.stdout).keys() == snapshot(reference).keys(), f"diff {expression}")
    results.append({
        "case": "replacement_language",
        "result": "pass",
        "negative": {"s/a/b/": "b/b", "s/a/b/g": "rejected"},
        "candidate": replacement_cases,
    })

    links_archive = archive_bytes([
        regular("prefix/target"),
        hardlink("prefix/hard", "prefix/target"),
        symlink("prefix/sym", "prefix/target"),
    ])
    with tempfile.TemporaryDirectory(prefix="unit15-scopes-") as td:
        work = pathlib.Path(td)
        baseline = run_filter(BASELINE, links_archive, "--transform=s,^prefix/,,")
        require(baseline.returncode == 0, baseline.stderr.decode("utf-8", "replace"))
        baseline_map = snapshot(baseline.stdout)
        require(baseline_map["hard"][1] == "prefix/target", "baseline hard-link negative control lost")
        require(baseline_map["sym"][1] == "prefix/target", "baseline symlink negative control lost")
        for index, expression in enumerate(("s,^prefix/,,", "s,^prefix/,,S")):
            candidate = run_filter(CANDIDATE, links_archive, f"--transform={expression}")
            require(candidate.returncode == 0, candidate.stderr.decode("utf-8", "replace"))
            reference = gnu_transform(expression, work / f"gnu-{index}", links=True, name="prefix/target")
            c = {k: v[:2] for k, v in snapshot(candidate.stdout).items()}
            r = {k: v[:2] for k, v in snapshot(reference).items()}
            require(c == r, f"scope mismatch {expression}: {c} != {r}")
        default = run_filter(CANDIDATE, links_archive, "--transform=s,^prefix/,,")
        extracted = extract(default.stdout, work / "extract-default")
        require(extracted.returncode == 0, extracted.stderr)
        require(os.stat(work / "extract-default/target").st_ino == os.stat(work / "extract-default/hard").st_ino,
                "hard-link inode identity lost")
        require(os.readlink(work / "extract-default/sym") == "target", "symlink target mismatch")
    results.append({"case": "target_scopes", "result": "pass", "default": "rsh", "S": "symlink target preserved"})

    leaf = "x" * 120
    strip_archive = archive_bytes([
        regular(f"prefix/{leaf}"),
        hardlink("prefix/peer", f"prefix/{leaf}"),
    ])
    with tempfile.TemporaryDirectory(prefix="unit15-strip-") as td:
        work = pathlib.Path(td)
        baseline = run_filter(BASELINE, strip_archive, "--strip-components=1")
        candidate = run_filter(CANDIDATE, strip_archive, "--strip-components=1")
        require(baseline.returncode == 0 and candidate.returncode == 0, "strip filter command failed")
        baseline_names = snapshot(baseline.stdout)
        require(f"prefix/{leaf}" in baseline_names, "baseline stale PAX path negative control lost")
        c = snapshot(candidate.stdout)
        require(leaf in c and "peer" in c, f"candidate names wrong: {list(c)}")
        require(c["peer"][1] == leaf, "candidate hard-link target wrong")
        require(c[leaf][2].get("path") == leaf, "candidate PAX path wrong")
        require(c["peer"][2].get("linkpath") == leaf, "candidate PAX linkpath wrong")
        extracted = extract(candidate.stdout, work / "extract")
        require(extracted.returncode == 0, extracted.stderr)
        require(os.stat(work / f"extract/{leaf}").st_ino == os.stat(work / "extract/peer").st_ino,
                "stripped hard-link inode identity lost")
    results.append({"case": "strip_and_pax", "result": "pass", "long_leaf_bytes": len(leaf)})

    occurrence_archive = archive_bytes([regular("a/a/a/a")])
    occurrence_links_archive = archive_bytes([
        regular("a/a/a/a"),
        hardlink("hard", "a/a/a/a"),
        symlink("sym", "a/a/a/a"),
    ])
    predecessor = run_filter(PREDECESSOR, occurrence_archive, "--transform=s/a/b/2")
    require(predecessor.returncode != 0, "predecessor numeric negative control lost")
    numeric = {
        "s/a/b/2": "a/b/a/a",
        "s/a/b/2g": "a/b/b/b",
        "s/a/b/g2": "a/b/b/b",
        "s/a/b/0": "b/a/a/a",
        "s/a/b/0g": "b/b/b/b",
        "s/a/b/22": "a/a/a/a",
        "s/a/b/2g3": "a/a/b/b",
        "s/A/b/i2g": "a/b/b/b",
    }
    with tempfile.TemporaryDirectory(prefix="unit15-occurrence-") as td:
        work = pathlib.Path(td)
        for index, (expression, expected_name) in enumerate(numeric.items()):
            candidate = run_filter(CANDIDATE, occurrence_archive, f"--transform={expression}")
            require(candidate.returncode == 0, candidate.stderr.decode("utf-8", "replace"))
            c = snapshot(candidate.stdout)
            require(list(c) == [expected_name], f"{expression}: {list(c)}")
            reference = gnu_transform(expression, work / str(index), links=False, name="a/a/a/a")
            require({k: v[:2] for k, v in c.items()} ==
                    {k: v[:2] for k, v in snapshot(reference).items()},
                    f"GNU numeric mismatch {expression}")
        link_expression = "s/a/b/2g"
        link_candidate = run_filter(
            CANDIDATE, occurrence_links_archive, f"--transform={link_expression}"
        )
        require(link_candidate.returncode == 0, link_candidate.stderr.decode("utf-8", "replace"))
        link_snapshot = snapshot(link_candidate.stdout)
        require(
            link_snapshot["hard"][1] == "a/b/b/b"
            and link_snapshot["sym"][1] == "a/b/b/b",
            "numeric selector did not reset independently for link targets",
        )
        link_reference = gnu_transform(
            link_expression, work / "links", links=True, name="a/a/a/a"
        )
        require(
            {k: v[:2] for k, v in link_snapshot.items()}
            == {k: v[:2] for k, v in snapshot(link_reference).items()},
            "GNU numeric link-target mismatch",
        )
        for expression in ("s/a/b/٢", "s/a/b/²", "s/a/b/０"):
            candidate = run_filter(CANDIDATE, occurrence_archive, f"--transform={expression}")
            require(candidate.returncode != 0, f"candidate accepted non-ASCII selector {expression}")
    results.append({
        "case": "numeric_occurrences",
        "result": "pass",
        "predecessor": "rejected numeric selector",
        "candidate": numeric,
        "non_ascii": "rejected",
    })

    print(json.dumps({
        "status": "PASS",
        "python": sys.version.split()[0],
        "tar": run(["tar", "--version"], text=True).stdout.splitlines()[0],
        "baseline_blob": blob,
        "candidate_sha256": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
        "cases": results,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
