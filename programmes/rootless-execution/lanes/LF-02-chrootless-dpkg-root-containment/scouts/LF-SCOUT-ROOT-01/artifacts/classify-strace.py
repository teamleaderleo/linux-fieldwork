#!/usr/bin/env python3
"""Classify path-bearing strace records for the LF-02 containment probe."""

from __future__ import annotations

import argparse
import ast
import collections
import glob
import os
import re
from pathlib import Path

MUTATING = {
    "creat", "mkdir", "mkdirat", "rmdir", "unlink", "unlinkat",
    "rename", "renameat", "renameat2", "link", "linkat", "symlink",
    "symlinkat", "chmod", "fchmodat", "fchmodat2", "chown", "lchown",
    "fchownat", "truncate", "utime", "utimes", "utimensat", "mknod",
    "mknodat", "mount", "umount2", "pivot_root", "setxattr",
    "lsetxattr", "removexattr", "lremovexattr", "bind",
}
OPEN_NAMES = {"open", "openat", "openat2"}
AT_SINGLE = {
    "openat", "openat2", "mkdirat", "unlinkat", "mknodat", "fchownat",
    "fchmodat", "fchmodat2", "faccessat", "faccessat2", "newfstatat",
    "readlinkat", "utimensat", "statx",
}
SERVICE_EXECUTABLES = {
    "systemctl", "service", "invoke-rc.d", "deb-systemd-invoke",
    "deb-systemd-helper", "start-stop-daemon", "initctl",
}


def decode(value: str) -> str:
    try:
        return ast.literal_eval('"' + value + '"')
    except Exception:
        return value


def strings(line: str) -> list[str]:
    return [decode(value) for value in re.findall(r'"((?:[^"\\]|\\.)*)"', line)]


def syscall(line: str) -> str | None:
    match = re.match(r"(?:\d+\s+)?([A-Za-z0-9_]+)\(", line)
    return match.group(1) if match else None


def result(line: str) -> tuple[bool, str]:
    match = re.search(r"=\s+(.+?)\s*$", line)
    text = match.group(1) if match else "unknown"
    return not text.startswith("-1"), text


def operation(name: str, line: str) -> str:
    if name in {"execve", "execveat"}:
        return "execution"
    if name in MUTATING:
        return "mutation"
    if name in OPEN_NAMES and re.search(r"O_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)", line):
        return "mutation"
    return "read"


def dirfd_base(token: str, cwd: str) -> str | None:
    token = token.strip()
    annotation = re.search(r"<(/[^>]+)>", token)
    if annotation:
        return os.path.normpath(annotation.group(1))
    if token.startswith("AT_FDCWD"):
        return cwd
    return None


def normalize(path: str, base: str | None) -> str:
    if path.startswith("/"):
        return os.path.normpath(path)
    if base is None:
        return f"<relative:{path}>"
    return os.path.normpath(os.path.join(base, path))


def unix_socket_ref(line: str) -> str | None:
    match = re.search(r'sun_path=(@?)"((?:[^"\\]|\\.)*)"', line)
    if not match:
        return None
    path = decode(match.group(2))
    return f"unix:@{path}" if match.group(1) else os.path.normpath(path)


def at_pair(line: str, cwd: str) -> list[tuple[str, str]] | None:
    pattern = (
        r'(?:\d+\s+)?(?:renameat2?|linkat)\(([^,]+),\s*'
        r'"((?:[^"\\]|\\.)*)",\s*([^,]+),\s*'
        r'"((?:[^"\\]|\\.)*)"'
    )
    match = re.match(pattern, line)
    if not match:
        return None
    return [
        ("old", normalize(decode(match.group(2)), dirfd_base(match.group(1), cwd))),
        ("new", normalize(decode(match.group(4)), dirfd_base(match.group(3), cwd))),
    ]


def path_refs(name: str, line: str, cwd: str) -> list[tuple[str, str]]:
    values = strings(line)
    if name in {"connect", "bind"}:
        socket = unix_socket_ref(line)
        return [("socket", socket)] if socket else []
    if not values:
        return []
    if name in {"renameat", "renameat2", "linkat"}:
        refs = at_pair(line, cwd)
        if refs is not None:
            return refs
    if name in {"rename", "link"}:
        refs = [("old", normalize(values[0], cwd))]
        if len(values) > 1:
            refs.append(("new", normalize(values[1], cwd)))
        return refs
    if name == "symlink":
        return [("link", normalize(values[1], cwd))] if len(values) > 1 else []
    if name == "symlinkat":
        match = re.match(
            r'(?:\d+\s+)?symlinkat\("(?:[^"\\]|\\.)*",\s*([^,]+),\s*'
            r'"((?:[^"\\]|\\.)*)"',
            line,
        )
        if match:
            return [("link", normalize(decode(match.group(2)), dirfd_base(match.group(1), cwd)))]
        return []
    if name == "mount":
        refs = [("source", normalize(values[0], cwd))]
        if len(values) > 1:
            refs.append(("target", normalize(values[1], cwd)))
        return refs
    if name == "pivot_root":
        refs = [("newroot", normalize(values[0], cwd))]
        if len(values) > 1:
            refs.append(("putold", normalize(values[1], cwd)))
        return refs
    base = cwd
    if name in AT_SINGLE:
        match = re.match(r"(?:\d+\s+)?[A-Za-z0-9_]+\(([^,]+),", line)
        base = dirfd_base(match.group(1), cwd) if match else None
    return [("path", normalize(values[0], base))]


def beneath(path: str, root: str) -> bool:
    return path == root or path.startswith(root + os.sep)


def outside(path: str, target: str) -> bool:
    return not beneath(path, target)


def needrestart(path: str) -> bool:
    return any(
        beneath(path, root)
        for root in ("/usr/lib/needrestart", "/run/needrestart", "/var/run/needrestart")
    )


def category(
    path: str,
    name: str,
    op: str,
    ok: bool,
    result_text: str,
    target: str,
    runtime: str,
) -> tuple[str, str]:
    basename = os.path.basename(path.rstrip("/"))
    if name in {"execve", "execveat"} and (basename in SERVICE_EXECUTABLES or needrestart(path)):
        return "service action", "host service or restart-management executable"
    if needrestart(path) and (op == "mutation" or name in {"connect", "bind"}):
        return "service action", "host needrestart runtime action outside target"
    if path in {"/run/dbus/system_bus_socket", "/var/run/dbus/system_bus_socket"}:
        return "service action", "host system D-Bus socket"
    if path.startswith("unix:@"):
        return "harmless runtime interaction", "abstract Unix-domain runtime socket"
    if path.startswith("<"):
        return "unresolved", "relative pathname lacked a traceable cwd or dirfd base"
    if any(beneath(path, root) for root in ("/dev", "/proc", "/sys")):
        return "harmless runtime interaction", "device, process, or kernel runtime path"
    if op == "mutation":
        if beneath(path, runtime):
            return "harmless runtime interaction", "probe-owned temporary runtime path"
        if not ok and "EEXIST" in result_text:
            return "harmless runtime interaction", "idempotent path-preparation call found an existing path"
        if not ok and (target.startswith(path.rstrip("/") + "/") or runtime.startswith(path.rstrip("/") + "/")):
            return "harmless runtime interaction", "target or probe ancestor path-preparation call"
        if ok:
            return "unexpected mutation", "successful filesystem mutation outside target"
        return "unresolved", "failed mutation attempt outside target"
    if target.startswith(path.rstrip("/") + "/") or beneath(path, runtime):
        return "required host read", "target traversal or probe input"
    return "required host read", "host executable, library, configuration, locale, identity, or metadata read"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("traces", nargs="+")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    runtime = os.path.abspath(args.runtime)
    initial_cwd = os.path.abspath(args.cwd)
    files: list[str] = []
    for pattern in args.traces:
        files.extend(sorted(glob.glob(pattern)))

    rows: list[dict[str, str]] = []
    for filename in files:
        phase = Path(filename).name.split(".trace", 1)[0]
        cwd = initial_cwd
        with open(filename, encoding="utf-8", errors="replace") as handle:
            for lineno, line in enumerate(handle, 1):
                name = syscall(line)
                if not name:
                    continue
                ok, result_text = result(line)
                op = operation(name, line)
                refs = path_refs(name, line, cwd)
                for role, path in refs:
                    if outside(path, target):
                        kind, rationale = category(path, name, op, ok, result_text, target, runtime)
                        rows.append({
                            "phase": phase,
                            "trace": Path(filename).name,
                            "line": str(lineno),
                            "syscall": name,
                            "operation": op,
                            "role": role,
                            "path": path,
                            "result": result_text,
                            "category": kind,
                            "rationale": rationale,
                        })
                if name == "chdir" and ok:
                    values = strings(line)
                    if values:
                        cwd = normalize(values[0], cwd)

    columns = [
        "phase", "trace", "line", "syscall", "operation", "role",
        "path", "result", "category", "rationale",
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(columns) + "\n")
        for row in rows:
            handle.write("\t".join(row[column].replace("\t", " ") for column in columns) + "\n")

    counts = collections.Counter(row["category"] for row in rows)
    categories = (
        "required host read", "harmless runtime interaction",
        "unexpected mutation", "service action", "unresolved",
    )
    summary = output.with_suffix(".summary.txt")
    with summary.open("w", encoding="utf-8") as handle:
        handle.write(f"target={target}\n")
        handle.write(f"trace_files={len(files)}\n")
        handle.write(f"outside_access_events={len(rows)}\n")
        for kind in categories:
            handle.write(f"category[{kind}]={counts.get(kind, 0)}\n")

    bad = [row for row in rows if row["category"] == "unexpected mutation"]
    print(summary.read_text(encoding="utf-8"), end="")
    for row in bad[:20]:
        print("unexpected mutation:", row)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
