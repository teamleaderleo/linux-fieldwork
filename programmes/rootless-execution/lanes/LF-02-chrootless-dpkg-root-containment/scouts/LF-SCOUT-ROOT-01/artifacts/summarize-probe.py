#!/usr/bin/env python3
"""Record LF-02 phase observations and build a versioned summary."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from typing import Any

CATEGORY_IDS = (
    "required_host_read",
    "harmless_runtime_interaction",
    "unexpected_mutation",
    "service_action",
    "unresolved",
)


def utc_from_ns(value: int) -> str:
    return (
        dt.datetime.fromtimestamp(value / 1_000_000_000, tz=dt.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def write_json(path: pathlib.Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def phase_artifacts(result_dir: pathlib.Path, name: str) -> dict[str, str | None]:
    candidates = {
        "command_normalized": f"{name}.command",
        "command_raw": f"{name}.command.raw",
        "stdout": f"{name}.stdout",
        "stderr": f"{name}.stderr",
        "status": f"{name}.status",
    }
    artifacts: dict[str, str | None] = {
        key: filename if result_dir.joinpath(filename).exists() else None
        for key, filename in candidates.items()
    }
    artifacts["trace_glob"] = f"{name}.trace*"
    return artifacts


def finish_phase_record(
    *,
    started_ns: int,
    started_utc: str,
    finished_ns: int,
    finished_utc: str,
    exit_status: int,
    artifacts: Mapping[str, str | None],
) -> dict[str, Any]:
    if finished_ns < started_ns:
        raise ValueError("phase finish precedes phase start")
    return {
        "exit_status": exit_status,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "duration_ms": round((finished_ns - started_ns) / 1_000_000, 3),
        "artifacts": dict(artifacts),
    }


def start_phase(result_dir: pathlib.Path, name: str) -> None:
    now_ns = time.time_ns()
    write_json(
        result_dir / f"{name}.phase-start.json",
        {"started_ns": now_ns, "started_utc": utc_from_ns(now_ns)},
    )


def finish_phase(result_dir: pathlib.Path, name: str, exit_status: int) -> None:
    start_path = result_dir / f"{name}.phase-start.json"
    started = read_json(start_path)
    finished_ns = time.time_ns()
    record = finish_phase_record(
        started_ns=int(started["started_ns"]),
        started_utc=str(started["started_utc"]),
        finished_ns=finished_ns,
        finished_utc=utc_from_ns(finished_ns),
        exit_status=exit_status,
        artifacts=phase_artifacts(result_dir, name),
    )
    write_json(result_dir / f"{name}.phase.json", record)
    start_path.unlink()


def command_output(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}"
        )
    return completed.stdout.strip()


def first_line(value: str) -> str:
    return value.splitlines()[0] if value.splitlines() else ""


def version_from(pattern: str, raw: str) -> str | None:
    match = re.search(pattern, raw)
    return match.group(1) if match else None


def capture_tool_versions(source_root: pathlib.Path) -> dict[str, dict[str, str | None]]:
    dpkg_raw = first_line(command_output(["dpkg", "--version"]))
    apt_raw = first_line(command_output(["apt-get", "--version"]))
    alternatives_raw = first_line(command_output(["update-alternatives", "--version"]))
    strace_raw = first_line(command_output(["strace", "--version"]))
    perl_raw = command_output(["perl", "-e", "print $^V"])
    source_text = source_root.joinpath("mmdebstrap").read_text(
        encoding="utf-8", errors="replace"
    )
    mmdebstrap_match = re.search(r"our \$VERSION = ['\"]([^'\"]+)['\"]", source_text)
    mmdebstrap_version = mmdebstrap_match.group(1) if mmdebstrap_match else None

    return {
        "dpkg": {
            "version": version_from(r"version\s+([^\s]+)", dpkg_raw),
            "raw": dpkg_raw,
        },
        "apt": {
            "version": version_from(r"^apt\s+([^\s]+)", apt_raw),
            "raw": apt_raw,
        },
        "update_alternatives": {
            "version": version_from(r"version\s+([^\s]+)", alternatives_raw),
            "raw": alternatives_raw,
        },
        "strace": {
            "version": version_from(r"strace -- version\s+([^\s]+)", strace_raw),
            "raw": strace_raw,
        },
        "perl": {"version": perl_raw.removeprefix("v"), "raw": perl_raw},
        "mmdebstrap": {
            "version": mmdebstrap_version,
            "raw": f"source VERSION={mmdebstrap_version}"
            if mmdebstrap_version
            else "source VERSION not found",
        },
    }


def package_field(package: pathlib.Path, field: str) -> str:
    return command_output(["dpkg-deb", "-f", str(package), field])


def fixture_metadata(package: pathlib.Path) -> dict[str, Any]:
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    stat = package.stat()
    return {
        "package": package_field(package, "Package"),
        "version": package_field(package, "Version"),
        "architecture": package_field(package, "Architecture"),
        "archive_name": package.name,
        "size_bytes": stat.st_size,
        "sha256": digest,
    }


def validate_classification(name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != 1:
        raise ValueError(f"{name}: unsupported classification schema")
    categories = value.get("categories")
    if not isinstance(categories, dict):
        raise ValueError(f"{name}: categories must be an object")
    if set(categories) != set(CATEGORY_IDS):
        raise ValueError(
            f"{name}: categories differ: expected {CATEGORY_IDS}, got {tuple(categories)}"
        )
    typed_categories = {key: int(categories[key]) for key in CATEGORY_IDS}
    outside_events = int(value["outside_access_events"])
    category_total = sum(typed_categories.values())
    if category_total != outside_events:
        raise ValueError(
            f"{name}: category total {category_total} != outside events {outside_events}"
        )
    result = {
        "schema_version": 1,
        "target": str(value["target"]),
        "trace_files": int(value["trace_files"]),
        "outside_access_events": outside_events,
        "categories": typed_categories,
        "category_total": category_total,
        "category_total_matches_events": True,
        "artifacts": dict(value.get("artifacts", {})),
    }
    return result


def load_phases(result_dir: pathlib.Path) -> dict[str, dict[str, Any]]:
    phases: dict[str, dict[str, Any]] = {}
    for phase_path in sorted(result_dir.glob("*.phase.json")):
        name = phase_path.name.removesuffix(".phase.json")
        value = read_json(phase_path)
        status_path = result_dir / f"{name}.status"
        if not status_path.exists():
            raise ValueError(f"{name}: missing status artifact")
        status = int(status_path.read_text(encoding="utf-8").strip())
        if int(value["exit_status"]) != status:
            raise ValueError(f"{name}: phase/status exit mismatch")
        duration = float(value["duration_ms"])
        if duration < 0:
            raise ValueError(f"{name}: negative duration")
        phases[name] = {
            "exit_status": status,
            "started_utc": str(value["started_utc"]),
            "finished_utc": str(value["finished_utc"]),
            "duration_ms": duration,
            "artifacts": dict(value["artifacts"]),
        }
    if not phases:
        raise ValueError("no phase records found")
    return phases


def load_classifications(result_dir: pathlib.Path) -> dict[str, dict[str, Any]]:
    classifications: dict[str, dict[str, Any]] = {}
    for summary_path in sorted(result_dir.glob("*-access.summary.json")):
        name = summary_path.name.removesuffix("-access.summary.json")
        classifications[name] = validate_classification(name, read_json(summary_path))
    if not classifications:
        raise ValueError("no classification summaries found")
    return classifications


def load_command_views(result_dir: pathlib.Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for command_path in sorted(result_dir.glob("*.command")):
        name = command_path.name.removesuffix(".command")
        raw_path = result_dir / f"{name}.command.raw"
        if not raw_path.exists():
            raise ValueError(f"{name}: missing raw command view")
        result[name] = {
            "normalized": command_path.name,
            "raw": raw_path.name,
        }
    return result


def build_summary(
    result_dir: pathlib.Path,
    *,
    fixture: Mapping[str, Any],
    tools: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = read_json(result_dir / "provenance.json")
    phases = load_phases(result_dir)
    classifications = load_classifications(result_dir)
    command_views = load_command_views(result_dir)

    service_actions = sum(
        value["categories"]["service_action"] for value in classifications.values()
    )
    unexpected_mutations = sum(
        value["categories"]["unexpected_mutation"]
        for value in classifications.values()
    )
    unresolved = sum(
        value["categories"]["unresolved"] for value in classifications.values()
    )
    promotion_signal = service_actions > 0 or unexpected_mutations > 0

    comparisons = {
        "host_fingerprint_unchanged": (
            result_dir.joinpath("host-fingerprint.diff").stat().st_size == 0
        ),
        "mmdebstrap_rerun": {
            "maintainer_script_equal": (
                result_dir.joinpath("mmdebstrap-rerun-script.diff").stat().st_size
                == 0
            ),
            "alternatives_state_equal": (
                result_dir.joinpath(
                    "mmdebstrap-rerun-alternative.diff"
                ).stat().st_size
                == 0
            ),
            "artifacts": {
                "maintainer_script_diff": "mmdebstrap-rerun-script.diff",
                "alternatives_state_diff": "mmdebstrap-rerun-alternative.diff",
            },
        },
    }

    return {
        "schema_version": 3,
        "provenance": provenance,
        "fixture": dict(fixture),
        "tools": dict(tools),
        "phases": phases,
        "classifications": classifications,
        "command_views": command_views,
        "comparisons": comparisons,
        "decision_inputs": {
            "service_actions": service_actions,
            "unexpected_mutations": unexpected_mutations,
            "unresolved": unresolved,
            "promotion_signal": promotion_signal,
            "rule": (
                "promote when any service action or unexpected mutation is observed"
            ),
        },
        "decision": "promote" if promotion_signal else "retain",
    }


def summary_passes(value: Mapping[str, Any]) -> bool:
    phases = value["phases"]
    comparisons = value["comparisons"]
    return bool(
        all(phase["exit_status"] == 0 for phase in phases.values())
        and comparisons["host_fingerprint_unchanged"]
        and comparisons["mmdebstrap_rerun"]["maintainer_script_equal"]
        and comparisons["mmdebstrap_rerun"]["alternatives_state_equal"]
        and all(
            classification["category_total_matches_events"]
            for classification in value["classifications"].values()
        )
    )


def build_command(args: argparse.Namespace) -> int:
    result_dir = pathlib.Path(args.result_dir)
    summary = build_summary(
        result_dir,
        fixture=fixture_metadata(pathlib.Path(args.package)),
        tools=capture_tool_versions(pathlib.Path(args.source_root)),
    )
    write_json(result_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary_passes(summary) else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)

    start = commands.add_parser("phase-start")
    start.add_argument("--result-dir", required=True)
    start.add_argument("--name", required=True)
    start.set_defaults(
        handler=lambda args: (start_phase(pathlib.Path(args.result_dir), args.name) or 0)
    )

    finish = commands.add_parser("phase-finish")
    finish.add_argument("--result-dir", required=True)
    finish.add_argument("--name", required=True)
    finish.add_argument("--exit-status", required=True, type=int)
    finish.set_defaults(
        handler=lambda args: (
            finish_phase(
                pathlib.Path(args.result_dir), args.name, args.exit_status
            )
            or 0
        )
    )

    build = commands.add_parser("build")
    build.add_argument("--result-dir", required=True)
    build.add_argument("--package", required=True)
    build.add_argument("--source-root", required=True)
    build.set_defaults(handler=build_command)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (KeyError, OSError, ValueError, RuntimeError) as error:
        print(f"summary error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
