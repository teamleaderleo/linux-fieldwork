#!/usr/bin/env python3
"""Capture process ownership evidence at mmdebstrap's final archive boundary.

This probe is evidence-only. It reports several independent ownership signals
instead of collapsing them into an invented guarantee:

* descendant ancestry from the mmdebstrap worker;
* shared process group and session;
* shared cgroup membership;
* live references to the temporary root through cwd/root/exe/open fds;
* zombie versus live state.

The probe labels and excludes its own PID from candidate results. A caller should
run it synchronously immediately after setup() and again immediately before the
root/chrootless tar exec, using the same worker PID and temporary root.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DELETED_SUFFIX = " (deleted)"


@dataclass(frozen=True)
class ProcRecord:
    pid: int
    comm: str
    state: str
    ppid: int
    pgrp: int
    session: int
    starttime_ticks: int
    uid: int | None
    cgroups: tuple[str, ...]
    cwd: str | None
    root: str | None
    exe: str | None
    fd_targets: tuple[str, ...]
    namespaces: tuple[tuple[str, str], ...]


def parse_proc_stat(text: str) -> tuple[int, str, str, int, int, int, int]:
    """Parse fields needed from /proc/PID/stat, including names with spaces."""
    left = text.find("(")
    right = text.rfind(")")
    if left <= 0 or right <= left:
        raise ValueError("malformed /proc stat record")
    pid = int(text[:left].strip())
    comm = text[left + 1 : right]
    fields = text[right + 1 :].strip().split()
    if len(fields) < 20:
        raise ValueError("short /proc stat record")
    return (
        pid,
        comm,
        fields[0],
        int(fields[1]),
        int(fields[2]),
        int(fields[3]),
        int(fields[19]),
    )


def read_link(path: Path) -> str | None:
    try:
        return os.readlink(path)
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
        return None


def read_uid(status_path: Path) -> int | None:
    try:
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Uid:"):
                return int(line.split()[1])
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError, ValueError):
        return None
    return None


def read_cgroups(path: Path) -> tuple[str, ...]:
    try:
        return tuple(
            line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
        return ()


def read_fd_targets(fd_dir: Path) -> tuple[str, ...]:
    targets: list[str] = []
    try:
        entries = sorted(fd_dir.iterdir(), key=lambda p: int(p.name))
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError, ValueError):
        return ()
    for entry in entries:
        target = read_link(entry)
        if target is not None:
            targets.append(target)
    return tuple(targets)


def read_namespaces(ns_dir: Path) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    try:
        entries = sorted(ns_dir.iterdir(), key=lambda p: p.name)
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
        return ()
    for entry in entries:
        target = read_link(entry)
        if target is not None:
            result.append((entry.name, target))
    return tuple(result)


def read_process(proc_dir: Path) -> ProcRecord | None:
    try:
        stat_text = (proc_dir / "stat").read_text(encoding="utf-8")
        pid, comm, state, ppid, pgrp, session, starttime = parse_proc_stat(stat_text)
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError, ValueError):
        return None
    return ProcRecord(
        pid=pid,
        comm=comm,
        state=state,
        ppid=ppid,
        pgrp=pgrp,
        session=session,
        starttime_ticks=starttime,
        uid=read_uid(proc_dir / "status"),
        cgroups=read_cgroups(proc_dir / "cgroup"),
        cwd=read_link(proc_dir / "cwd"),
        root=read_link(proc_dir / "root"),
        exe=read_link(proc_dir / "exe"),
        fd_targets=read_fd_targets(proc_dir / "fd"),
        namespaces=read_namespaces(proc_dir / "ns"),
    )


def strip_deleted_suffix(value: str) -> str:
    if value.endswith(DELETED_SUFFIX):
        return value[: -len(DELETED_SUFFIX)]
    return value


def path_is_beneath(value: str | None, root: Path) -> bool:
    if value is None or not value.startswith("/"):
        return False
    candidate = Path(strip_deleted_suffix(value))
    try:
        return os.path.commonpath((str(candidate), str(root))) == str(root)
    except ValueError:
        return False


def root_references(record: ProcRecord, root: Path) -> tuple[str, ...]:
    refs: list[str] = []
    for label, value in (("cwd", record.cwd), ("root", record.root), ("exe", record.exe)):
        if path_is_beneath(value, root):
            refs.append(f"{label}:{value}")
    for target in record.fd_targets:
        if path_is_beneath(target, root):
            refs.append(f"fd:{target}")
    return tuple(refs)


def is_descendant(pid: int, ancestor: int, records: dict[int, ProcRecord]) -> bool:
    seen: set[int] = set()
    current = pid
    while current > 0 and current not in seen:
        seen.add(current)
        record = records.get(current)
        if record is None:
            return False
        if record.ppid == ancestor:
            return True
        current = record.ppid
    return False


def capture_snapshot(
    *,
    root: Path,
    worker_pid: int,
    phase: str,
    proc_root: Path = Path("/proc"),
    probe_pid: int | None = None,
) -> dict[str, object]:
    root = root.resolve(strict=True)
    probe_pid = os.getpid() if probe_pid is None else probe_pid

    records: dict[int, ProcRecord] = {}
    unreadable: list[int] = []
    for entry in sorted(proc_root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else -1):
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        record = read_process(entry)
        if record is None:
            unreadable.append(pid)
        else:
            records[pid] = record

    worker = records.get(worker_pid)
    if worker is None:
        raise RuntimeError(f"worker PID {worker_pid} is absent or unreadable")
    probe = records.get(probe_pid)

    relevant: list[dict[str, object]] = []
    live_owned: list[int] = []
    zombie_owned: list[int] = []
    group_affiliates: list[int] = []

    for pid, record in sorted(records.items()):
        if pid in {worker_pid, probe_pid}:
            continue
        descendant = is_descendant(pid, worker_pid, records)
        refs = root_references(record, root)
        same_pgrp = record.pgrp == worker.pgrp
        same_session = record.session == worker.session
        same_cgroup = bool(worker.cgroups) and record.cgroups == worker.cgroups
        reasons: list[str] = []
        if descendant:
            reasons.append("descendant")
        if same_pgrp:
            reasons.append("same_process_group")
        if same_session:
            reasons.append("same_session")
        if same_cgroup:
            reasons.append("same_cgroup")
        if refs:
            reasons.append("temporary_root_reference")
        if not reasons:
            continue

        direct_owned_evidence = descendant or bool(refs)
        if direct_owned_evidence:
            if record.state == "Z":
                zombie_owned.append(pid)
            else:
                live_owned.append(pid)
        elif same_pgrp or same_session:
            group_affiliates.append(pid)

        item = asdict(record)
        item["cgroups"] = list(record.cgroups)
        item["fd_targets"] = list(record.fd_targets)
        item["namespaces"] = dict(record.namespaces)
        item["reasons"] = reasons
        item["temporary_root_references"] = list(refs)
        item["direct_owned_evidence"] = direct_owned_evidence
        relevant.append(item)

    return {
        "schema": "linux-fieldwork.archive-boundary-process-probe.v1",
        "captured_unix_ns": time.time_ns(),
        "phase": phase,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "temporary_root": str(root),
        "worker_pid": worker_pid,
        "worker": asdict(worker),
        "probe_pid": probe_pid,
        "probe": asdict(probe) if probe is not None else None,
        "excluded_pids": sorted({worker_pid, probe_pid}),
        "process_count_readable": len(records),
        "unreadable_or_raced_pids": unreadable,
        "live_owned_candidates": live_owned,
        "zombie_owned_candidates": zombie_owned,
        "group_affiliates_without_direct_evidence": group_affiliates,
        "relevant_processes": relevant,
        "interpretation": {
            "direct_owned_evidence": "descendant ancestry or a live /proc reference beneath the temporary root",
            "group_signals": "shared process group/session/cgroup are reported independently and do not prove ownership alone",
            "quiescent_observation": len(live_owned) == 0,
            "quiescence_claim_limit": "one snapshot cannot establish the repeated root/chrootless lifecycle premise",
        },
    }


def write_json_atomic(output: Path, payload: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--worker-pid", required=True, type=int)
    parser.add_argument("--phase", required=True, choices=("after-setup", "before-tar"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"))
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not sys.platform.startswith("linux"):
        raise SystemExit("this probe requires Linux /proc")
    payload = capture_snapshot(
        root=args.root,
        worker_pid=args.worker_pid,
        phase=args.phase,
        proc_root=args.proc_root,
    )
    write_json_atomic(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
