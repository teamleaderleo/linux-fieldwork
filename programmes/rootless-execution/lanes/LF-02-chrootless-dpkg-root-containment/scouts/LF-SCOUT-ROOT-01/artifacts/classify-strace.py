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


def path_roles(name: str, values: list[str]) -> list[tuple[str, str]]:
    if not values:
        return []
    if name in TWO_PATH:
        return [("old", values[0]), ("new", values[1])] if len(values) > 1 else [("old", values[0])]
    if name in {"symlink", "symlinkat"}:
        return [("link", values[1])] if len(values) > 1 else []
    if name == "mount":
        return [("source", values[0]), ("target", values[1])] if len(values) > 1 else [("source", values[0])]
    if name == "pivot_root":
        return [("newroot", values[0]), ("putold", values[1])] if len(values) > 1 else [("newroot", values[0])]
    if name in {"connect", "bind"}:
        unix = re.search(r"sun_path=\"((?:[^\"\\]|\\.)*)\"", " ".join(values) if False else "")
        return [("path", values[-1])]
    return [("path", values[0])]


def normalize(path: str, cwd: str) -> str:
    if path.startswith("/"):
        return os.path.normpath(path)
    if path.startswith("@"):
        return "unix:" + path
    if path.startswith("<"):
        return path
    return os.path.normpath(os.path.join(cwd, path))


def is_outside(path: str, target: str) -> bool:
    return path != target and not path.startswith(target + os.sep)


def classify(path: str, name: str, op: str, success: bool, target: str, runtime: str) -> tuple[str, str]:
    base = os.path.basename(path.rstrip("/"))
    if name in {"execve", "execveat"} and base in SERVICE_NAMES:
        return "service action", "service-control executable"
    if path.startswith("unix:"):
        if any(word in path for word in ("systemd", "dbus", "init", "service")):
            return "service action", "service-related Unix socket"
        return "harmless runtime interaction", "Unix-domain runtime socket"
    if path.startswith("<"):
        return "unresolved", "pathname could not be resolved"
    if path == "/dev" or path.startswith("/dev/") or path == "/proc" or path.startswith("/proc/") or path == "/sys" or path.startswith("/sys/"):
        return "harmless runtime interaction", "device, process, or kernel runtime path"
    if op == "mutation":
        if not success and (target.startswith(path.rstrip("/") + "/") or runtime.startswith(path.rstrip("/") + "/")):
            return "harmless runtime interaction", "failed path-preparation call on an existing target ancestor"
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
    cwd = os.path.abspath(args.cwd)
    files: list[str] = []
    for pattern in args.traces:
        files.extend(sorted(glob.glob(pattern)))

    rows: list[dict[str, str]] = []
    for filename in files:
        phase = Path(filename).name.split(".trace", 1)[0]
        with open(filename, encoding="utf-8", errors="replace") as handle:
            for lineno, line in enumerate(handle, 1):
                name = syscall_name(line)
                if not name:
                    continue
                values = quoted(line)
                roles = path_roles(name, values)
                if not roles:
                    continue
                success, result = result_state(line)
                op = operation(name, line)
                for role, raw in roles:
                    path = normalize(raw, cwd)
                    if not is_outside(path, target):
                        continue
                    category, rationale = classify(path, name, op, success, target, runtime)
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
