#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import pathlib
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
from typing import Any

EPOCH = 946684800
CASES = [
    "traversal", "absolute", "symlink", "hardlink", "sparse",
    "numeric-owner", "mode-bits", "timestamps", "xattr",
]

def find_repo_root(start: pathlib.Path) -> pathlib.Path:
    for candidate in [start, *start.parents]:
        if (candidate / "upstream/mmdebstrap/tarfilter").is_file():
            return candidate
    raise RuntimeError("cannot find repository root")

def member_manifest(path: pathlib.Path) -> list[dict[str, Any]]:
    rows = []
    try:
        with tarfile.open(path, "r:*") as tf:
            for m in tf:
                rows.append({
                    "name": m.name,
                    "type": m.type.decode("ascii", "replace") if isinstance(m.type, bytes) else str(m.type),
                    "size": m.size,
                    "uid": m.uid,
                    "gid": m.gid,
                    "mode": oct(m.mode),
                    "mtime": m.mtime,
                    "linkname": m.linkname,
                    "pax_headers": dict(sorted(m.pax_headers.items())),
                    "sparse": m.sparse,
                })
    except Exception as exc:
        cp = subprocess.run(["tar", "-tvf", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rows.append({
            "manifest_error": f"{type(exc).__name__}: {exc}",
            "gnu_tar_list_status": cp.returncode,
            "gnu_tar_list_stdout": cp.stdout.decode("utf-8", "replace"),
            "gnu_tar_list_stderr": cp.stderr.decode("utf-8", "replace"),
            "sparse": None,
        })
    return rows

def file_info(path: pathlib.Path) -> dict[str, Any]:
    st = path.lstat()
    info = {
        "exists": True,
        "mode": oct(stat.S_IMODE(st.st_mode)),
        "uid": st.st_uid,
        "gid": st.st_gid,
        "mtime": int(st.st_mtime),
        "size": st.st_size,
        "blocks_512": st.st_blocks,
        "allocated_bytes": st.st_blocks * 512,
        "inode": st.st_ino,
        "nlink": st.st_nlink,
        "kind": "symlink" if path.is_symlink() else "directory" if path.is_dir() else "file",
    }
    if path.is_symlink():
        info["link_target"] = os.readlink(path)
    try:
        info["user.lf14"] = os.getxattr(path, b"user.lf14").decode("utf-8", "replace")
    except OSError:
        info["user.lf14"] = None
    return info

def safe_info(path: pathlib.Path) -> dict[str, Any]:
    try:
        return file_info(path)
    except FileNotFoundError:
        return {"exists": False}

def evaluate(case: str, target: pathlib.Path, base: pathlib.Path, status: int, archive_manifest: list[dict[str, Any]], direct_sparse_alloc: int | None) -> tuple[bool, dict[str, Any], str]:
    details: dict[str, Any] = {"status": status}
    if case == "traversal":
        outside = base / "lf14-traversal-escape"
        inside = target / "lf14-traversal-escape"
        details.update(outside=safe_info(outside), inside=safe_info(inside))
        return not outside.exists() and not inside.exists() and status != 0, details, "reject ../ member and create no file outside target"
    if case == "absolute":
        rooted = pathlib.Path("/lf14-absolute-escape")
        inside = target / "lf14-absolute-escape"
        details.update(rooted=safe_info(rooted), inside=safe_info(inside))
        return not rooted.exists() and inside.is_file() and status == 0, details, "strip leading slash and extract beneath target"
    if case == "symlink":
        outside_payload = base / "lf14-symlink-outside/payload"
        pivot = target / "pivot"
        details.update(outside_payload=safe_info(outside_payload), pivot=safe_info(pivot))
        return not outside_payload.exists() and status != 0, details, "do not follow archive-created symlink outside target"
    if case == "hardlink":
        a, b = target / "hard/base", target / "hard/peer"
        details.update(base=safe_info(a), peer=safe_info(b))
        ok = a.is_file() and b.is_file() and a.stat().st_ino == b.stat().st_ino and a.stat().st_nlink >= 2 and status == 0
        return ok, details, "preserve hard-link inode relationship"
    if case == "sparse":
        p = target / ".sparse-source"
        details.update(file=safe_info(p), archive_sparse=archive_manifest[0].get("sparse"))
        logical = p.stat().st_size if p.exists() else 0
        alloc = p.stat().st_blocks * 512 if p.exists() else logical
        if direct_sparse_alloc is None:
            ok = p.is_file() and logical >= 8 * 1024 * 1024 and alloc < logical // 4 and status == 0
        else:
            ok = p.is_file() and logical >= 8 * 1024 * 1024 and alloc <= max(direct_sparse_alloc * 4, logical // 4) and status == 0
        return ok, details, "preserve logical bytes and sparse allocation"
    if case == "numeric-owner":
        p = target / "owner/file"
        hdr = archive_manifest[0]
        details.update(file=safe_info(p), header_uid=hdr["uid"], header_gid=hdr["gid"])
        ok = p.is_file() and hdr["uid"] == 12345 and hdr["gid"] == 23456 and status == 0
        return ok, details, "preserve numeric uid/gid in archive; extraction follows caller privilege"
    if case == "mode-bits":
        p = target / "mode/file"
        details.update(file=safe_info(p))
        return p.is_file() and stat.S_IMODE(p.stat().st_mode) == 0o751 and status == 0, details, "preserve mode 0751"
    if case == "timestamps":
        p = target / "time/file"
        details.update(file=safe_info(p))
        return p.is_file() and int(p.stat().st_mtime) == EPOCH and status == 0, details, "preserve mtime 2000-01-01T00:00:00Z"
    if case == "xattr":
        p = target / "xattr/file"
        details.update(file=safe_info(p))
        try:
            val = os.getxattr(p, b"user.lf14")
        except OSError:
            val = None
        return p.is_file() and val == b"corpus" and status == 0, details, "preserve ordinary user.lf14 xattr"
    raise AssertionError(case)

def main() -> int:
    ap = argparse.ArgumentParser(description="Generate and exercise the LF-14 archive corpus")
    ap.add_argument("--repo-root", type=pathlib.Path)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ns = ap.parse_args()
    script = pathlib.Path(__file__).resolve()
    repo = ns.repo_root.resolve() if ns.repo_root else find_repo_root(script)
    out = ns.output.resolve()
    if out.exists():
        shutil.rmtree(out)
    fixtures, filtered, extracts, logs = (out / n for n in ("fixtures", "filtered", "extracts", "logs"))
    for d in (fixtures, filtered, extracts, logs):
        d.mkdir(parents=True, exist_ok=True)

    generator = script.with_name("generate-fixtures.py")
    subprocess.run([sys.executable, str(generator), str(fixtures)], check=True)
    tarfilter = repo / "upstream/mmdebstrap/tarfilter"
    env = {
        "platform": platform.platform(),
        "python": sys.version,
        "euid": os.geteuid(),
        "egid": os.getegid(),
        "tar": subprocess.check_output(["tar", "--version"], text=True).splitlines()[0],
        "tarfilter": str(tarfilter.relative_to(repo)),
    }
    (out / "environment.json").write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")

    manifests: dict[str, Any] = {}
    commands = [f"{sys.executable} {generator.relative_to(repo)} {fixtures}"]
    for case in CASES:
        src = fixtures / f"{case}.tar"
        dst = filtered / f"{case}.tar"
        commands.append(f"python3 upstream/mmdebstrap/tarfilter --path-exclude=/__lf14_never_match__ < {src} > {dst}")
        with src.open("rb") as inp, dst.open("wb") as op:
            cp = subprocess.run([sys.executable, str(tarfilter), "--path-exclude=/__lf14_never_match__"], stdin=inp, stdout=op, stderr=subprocess.PIPE)
        if cp.returncode:
            raise RuntimeError(f"tarfilter failed for {case}: {cp.stderr.decode()}")
        manifests[case] = {"original": member_manifest(src), "filtered": member_manifest(dst)}
    (out / "archive-manifests.json").write_text(json.dumps(manifests, indent=2, sort_keys=True) + "\n")

    results: list[dict[str, Any]] = []
    sparse_direct_alloc: int | None = None
    for path_name, archive_dir in (("gnu-tar-direct", fixtures), ("mmdebstrap-tarfilter", filtered)):
        for case in CASES:
            base = extracts / path_name / case
            target = base / "target"
            (base / "lf14-symlink-outside").mkdir(parents=True, exist_ok=True)
            target.mkdir(parents=True, exist_ok=True)
            archive = archive_dir / f"{case}.tar"
            cmd = ["tar", "--xattrs", "--xattrs-include=user.*", "-xf", str(archive), "-C", str(target)]
            commands.append(" ".join(cmd))
            cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (logs / f"{path_name}-{case}.stdout").write_bytes(cp.stdout)
            (logs / f"{path_name}-{case}.stderr").write_bytes(cp.stderr)
            direct_ref = sparse_direct_alloc if path_name == "mmdebstrap-tarfilter" and case == "sparse" else None
            ok, details, expected = evaluate(case, target, base, cp.returncode, manifests[case]["filtered" if path_name == "mmdebstrap-tarfilter" else "original"], direct_ref)
            if path_name == "gnu-tar-direct" and case == "sparse" and (target / ".sparse-source").exists():
                sparse_direct_alloc = (target / ".sparse-source").stat().st_blocks * 512
            results.append({"path": path_name, "case": case, "pass": ok, "expected": expected, "details": details, "stderr": cp.stderr.decode("utf-8", "replace")})

    (out / "extraction-results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    (out / "commands.txt").write_text("\n".join(commands) + "\n")
    lines = ["# Extraction matrix", "", "| Path | Fixture | Expected behavior | Result | Key observation |", "|---|---|---|---|---|"]
    for r in results:
        d = r["details"]
        obs = "exit=" + str(d["status"])
        if r["case"] == "sparse" and d.get("file", {}).get("exists"):
            obs += f", logical={d['file']['size']}, allocated={d['file']['allocated_bytes']}"
        elif r["case"] == "hardlink" and d.get("base", {}).get("exists"):
            obs += f", inode_equal={d['base']['inode'] == d['peer']['inode']}"
        elif r["case"] == "numeric-owner":
            obs += f", header={d['header_uid']}:{d['header_gid']}, extracted={d['file'].get('uid')}:{d['file'].get('gid')}"
        elif r["case"] in ("mode-bits", "timestamps", "xattr"):
            f = d.get("file", {})
            obs += f", mode={f.get('mode')}, mtime={f.get('mtime')}, xattr={f.get('user.lf14')}"
        elif r["case"] == "absolute":
            obs += f", inside={d['inside']['exists']}, rooted={d['rooted']['exists']}"
        elif r["case"] == "traversal":
            obs += f", outside={d['outside']['exists']}"
        elif r["case"] == "symlink":
            obs += f", outside_payload={d['outside_payload']['exists']}"
        lines.append(f"| {r['path']} | {r['case']} | {r['expected']} | {'PASS' if r['pass'] else 'FAIL'} | {obs} |")
    (out / "extraction-matrix.md").write_text("\n".join(lines) + "\n")

    comparisons = ["# Metadata comparison", ""]
    for case in CASES:
        a, b = manifests[case]["original"], manifests[case]["filtered"]
        comparisons.extend([f"## {case}", "", f"Archive member count: original `{len(a)}`, filtered `{len(b)}`."])
        if case == "sparse":
            comparisons.append(f"Original sparse map: `{a[0].get('sparse')}`")
            comparisons.append(f"Filtered sparse map: `{b[0].get('sparse')}`")
            if b[0].get("manifest_error"):
                comparisons.append(f"Filtered manifest error: `{b[0]['manifest_error']}`")
                comparisons.append(f"GNU tar list status: `{b[0]['gnu_tar_list_status']}`")
        elif case == "xattr":
            comparisons.append(f"Original pax headers: `{a[0].get('pax_headers')}`")
            comparisons.append(f"Filtered pax headers: `{b[0].get('pax_headers')}`")
        else:
            fields = ("name", "type", "size", "uid", "gid", "mode", "mtime", "linkname")
            same = all(all(k in x for k in fields) for x in a + b) and [{k: x[k] for k in fields} for x in a] == [{k: x[k] for k in fields} for x in b]
            comparisons.append(f"Core member fields equal: `{same}`")
        comparisons.append("")
    (out / "metadata-comparison.md").write_text("\n".join(comparisons))

    failed = [r for r in results if not r["pass"]]
    print(json.dumps({"failures": [{"path": r["path"], "case": r["case"]} for r in failed]}, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
