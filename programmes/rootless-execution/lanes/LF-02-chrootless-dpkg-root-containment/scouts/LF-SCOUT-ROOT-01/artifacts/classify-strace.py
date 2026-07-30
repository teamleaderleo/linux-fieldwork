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
SERVICE_NAMES = {
    "systemctl", "service", "invoke-rc.d", "deb-systemd-invoke",
    "deb-systemd-helper", "start-stop-daemon", "initctl",
}
OPEN_NAMES = {"open", "openat", "openat2"}
TWO_PATH = {"rename", "renameat", "renameat2", "link", "linkat"}
SINGLE_AT_PATH = {
    "openat", "openat2", "mkdirat", "unlinkat", "mknodat", "fchownat",
    "fchmodat", "fchmodat2", "faccessat", "faccessat2", "newfstatat",
    "readlinkat", "utimensat", "statx",
}


def decode_quoted(token: str) -> str:
    try:
        return ast.literal_eval('"' + token + '"')
    except Exception:
        return token


def quoted(line: str) -> list[str]:
    return [decode_quoted(value) for value in re.findall(r'"((?:[^"\\]|\\.)*)"', line)]


def result_state(line: str) -> tuple[bool, str]:
    match = re.search(r"=\s+([^\s]+)(?:\s|$)", line)
    if not match:
        return False, "unknown"
    value = match.group(1)
    return not value.startswith("-1"), value


def syscall_name(line: str) -> str | None:
    match = re.match(r"(?:\d+\s+)?([a-zA-Z0-9_]+)\(", line)
    return match.group(1) if match else None


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
    if token == "AT_FDCWD":
        return cwd
    match = re.search(r"<([^>]+)>", token)
    if match:
        value = match.group(1)
        if value.startswith("/"):
            return os.path.normpath(value)
    return None


def normalize(path: str, base: str | None) -> str:
    if path.startswith("/"):
        return os.path.normpath(path)
    if path.startswith("@"):
        return "unix:" + path
    if path.startswith("<"):
        return path
    if base is None:
        return f"<relative:{path}>"
    return os.path.normpath(os.path.join(base, path))


def single_at_base(line: str, cwd: str) -> str | None:
    match = re.match(r"(?:\d+\s+)?[a-zA-Z0-9_]+\(([^,]+),\s*", line)
    return dirfd_base(match.group(1), cwd) if match else None


def two_at_refs(line: str, cwd: str) -> list[tuple[str, str]] | None:
    match = re.match(
        r'(?:\d+\s+)?(?:renameat2?|linkat)\(([^,]+),\s*"((?:[^"\\]|\\.)*)",\s*([^,]+),\s*"((?:[^"\\]|\\.)*)"',
        line,
    )
    if not match:
        return None
    old_base = dirfd_base(match.group(1), cwd)
    new_base = dirfd_base(match.group(3), cwd)
    return [
        ("old", normalize(decode_quoted(match.group(2)), old_base)),
        ("new", normalize(decode_quoted(match.group(4)), new_base)),
    ]


def path_refs(name: str, line: str, values: list[str], cwd: str) -> list[tuple[str, str]]:
    if not values:
        return []
    if name in {"renameat", "renameat2", "linkat"}:
        parsed = two_at_refs(line, cwd)
        if parsed is not None:
            return parsed
    if name in {"rename", "link"}:
        refs = [("old", normalize(values[0], cwd))]
        if len(values) > 1:
            refs.append(("new", normalize(values[1], cwd)))
        return refs
    if name == "symlink":
        return [("link", normalize(values[1], cwd))] if len(values) > 1 else []
    if name == "symlinkat":
        match = re.match(
            r'(?:\d+\s+)?symlinkat\("(?:[^"\\]|\\.)*",\s*([^,]+),\s*"((?:[^"\\]|\\.)*)"',
            line,
        )
        if match:
            return [("link", normalize(decode_quoted(match.group(2)), dirfd_base(match.group(1), cwd)))]
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
    if name in {"connect", "bind"}:
        return [("path", normalize(values[-1], cwd))]
    base = single_at_base(line, cwd) if name in SINGLE_AT_PATH else cwd
    return [("path", normalize(values[0], base))]


def is_outside(path: str, target: str) -> bool:
    return path != target and not path.startswith(target + os.sep)


def is_needrestart(path: str) -> bool:
    return (
        path == "/usr/lib/needrestart"
        or path.startswith("/usr/lib/needrestart/")
        or path == "/run/needrestart"
        or path.startswith("/run/needrestart/")
        or path == "/var/run/needrestart"
        or path.startswith("/var/run/needrestart/")
    )


def classify(
    path: str,
    name: str,
    op: str,
    success: bool,
    result: str,
    target: str,
    runtime: str,
) -> tuple[str, str]:
    base = os.path.basename(path.rstrip("/"))
    if name in {"execve", "execveat"} and (base in SERVICE_NAMES or is_needrestart(path)):
        return "service action", "host service or restart-management executable"
    if is_needrestart(path) and (op == "mutation" or name in {"connect", "bind"}):
        return "service action", "host needrestart runtime action outside target"
    if path.startswith("unix:"):
        if any(word in path for word in ("systemd", "dbus", "init", "service")):
            return "service action", "service-related Unix socket"
        return "harmless runtime interaction", "Unix-domain runtime socket"
    if path.startswith("<"):
        return "unresolved", "relative pathname lacked a traceable cwd or dirfd base"
    if path == "/dev" or path.startswith("/dev/") or path == "/proc" or path.startswith("/proc/") or path == "/sys" or path.startswith("/sys/"):
        return "harmless runtime interaction", "device, process, or kernel runtime path"
    if op == "mutation":
        if not success and "EEXIST" in result:
            return "harmless runtime interaction", "idempotent path-preparation call found an existing path"
        if not success and (target.startswith(path.rstrip("/") + "/") or runtime.startswith(path.rstrip("/") + "/")):
            return "harmless runtime interaction", "failed path-preparation call on a target or probe ancestor"
        if success:
            return "unexpected mutation", "successful filesystem mutation outside target"
        return "unresolved", "failed mutation attempt outside target"
    if target.startswith(path.rstrip("/") + "/") or path.startswith(runtime + "/"):
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
                name = syscall_name(line)
                if not name:
                    continue
                values = quoted(line)
                success, result = result_state(line)
                refs = path_refs(name, line, values, cwd)
                op = operation(name, line)
                for role, path in refs:
                    if not is_outside(path, target):
                        continue
                    category, rationale = classify(path, name, op, success, result, target, runtime)
                    rows.append({
                        "phase": phase,
                        "trace": Path(filename).name,
                        "line": str(lineno),
                        "syscall": name,
                        "operation": op,
                        "role": role,
                        "path": path,
                        "result": result,
                        "category": category,
                        "rationale": rationale,
                    })
                if name == "chdir" and success and values:
                    cwd = normalize(values[0], cwd)

    columns = ["phase", "trace", "line", "syscall", "operation", "role", "path", "result", "category", "rationale"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(columns) + "\n")
        for row in rows:
            handle.write("\t".join(row[column].replace("\t", " ") for column in columns) + "\n")

    counts = collections.Counter(row["category"] for row in rows)
    summary = output.with_suffix(".summary.txt")
    with summary.open("w", encoding="utf-8") as handle:
        handle.write(f"target={target}\n")
        handle.write(f"trace_files={len(files)}\n")
        handle.write(f"outside_access_events={len(rows)}\n")
        for category in ("required host read", "harmless runtime interaction", "unexpected mutation", "service action", "unresolved"):
            handle.write(f"category[{category}]={counts.get(category, 0)}\n")

    bad = [row for row in rows if row["category"] == "unexpected mutation"]
    print(summary.read_text(encoding="utf-8"), end="")
    if bad:
        for row in bad[:20]:
            print("unexpected mutation:", row)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
