#!/usr/bin/env python3
"""Record LF-02 phase observations and build a versioned summary."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
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
PHASE_ORDER = (
    "direct-install",
    "direct-reinstall",
    "direct-purge",
    "direct-install-after-purge",
    "mmdebstrap-one",
    "mmdebstrap-two",
)
CLASSIFICATION_ORDER = ("direct", "mmdebstrap-one", "mmdebstrap-two")
PHASE_ARTIFACT_KEYS = (
    "command_normalized",
    "command_raw",
    "stdout",
    "stderr",
    "status",
    "trace_glob",
)


def require_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label}: expected non-negative JSON integer")
    return value


def require_nonnegative_number(value: Any, label: str) -> int | float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label}: expected finite non-negative JSON number")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}: expected non-empty JSON string")
    return value


def require_regular_file(path: pathlib.Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label}: missing regular-file artifact {path.name}")


def require_exact_names(actual: set[str], expected: tuple[str, ...], label: str) -> None:
    if actual != set(expected):
        raise ValueError(
            f"{label}: expected {expected}, got {tuple(sorted(actual))}"
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
    started_monotonic_ns: int,
    started_utc: str,
    finished_monotonic_ns: int,
    finished_utc: str,
    exit_status: int,
    artifacts: Mapping[str, str | None],
) -> dict[str, Any]:
    if finished_monotonic_ns < started_monotonic_ns:
        raise ValueError("phase finish precedes phase start")
    return {
        "exit_status": exit_status,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "duration_ms": round(
            (finished_monotonic_ns - started_monotonic_ns) / 1_000_000, 3
        ),
        "artifacts": dict(artifacts),
    }


def start_phase(result_dir: pathlib.Path, name: str) -> None:
    wall_ns = time.time_ns()
    write_json(
        result_dir / f"{name}.phase-start.json",
        {
            "started_monotonic_ns": time.monotonic_ns(),
            "started_utc": utc_from_ns(wall_ns),
        },
    )


def finish_phase(result_dir: pathlib.Path, name: str, exit_status: int) -> None:
    start_path = result_dir / f"{name}.phase-start.json"
    started = read_json(start_path)
    finished_monotonic_ns = time.monotonic_ns()
    finished_wall_ns = time.time_ns()
    record = finish_phase_record(
        started_monotonic_ns=require_nonnegative_int(
            started["started_monotonic_ns"], "started_monotonic_ns"
        ),
        started_utc=require_string(started["started_utc"], "started_utc"),
        finished_monotonic_ns=finished_monotonic_ns,
        finished_utc=utc_from_ns(finished_wall_ns),
        exit_status=require_nonnegative_int(exit_status, "exit_status"),
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
    typed_categories = {
        key: require_nonnegative_int(categories[key], f"{name}: categories.{key}")
        for key in CATEGORY_IDS
    }
    outside_events = require_nonnegative_int(
        value["outside_access_events"], f"{name}: outside_access_events"
    )
    category_total = sum(typed_categories.values())
    if category_total != outside_events:
        raise ValueError(
            f"{name}: category total {category_total} != outside events {outside_events}"
        )
    recorded_total = require_nonnegative_int(
        value["category_total"], f"{name}: category_total"
    )
    if recorded_total != category_total:
        raise ValueError(f"{name}: recorded category total differs")
    if value.get("category_total_matches_events") is not True:
        raise ValueError(f"{name}: category-total match flag must be true")
    trace_files = require_nonnegative_int(
        value["trace_files"], f"{name}: trace_files"
    )
    if trace_files == 0:
        raise ValueError(f"{name}: trace_files must be positive")
    result = {
        "schema_version": 1,
        "target": require_string(value["target"], f"{name}: target"),
        "trace_files": trace_files,
        "outside_access_events": outside_events,
        "categories": typed_categories,
        "category_total": category_total,
        "category_total_matches_events": True,
        "artifacts": value.get("artifacts"),
    }
    if not isinstance(result["artifacts"], dict):
        raise ValueError(f"{name}: artifacts must be an object")
    return result


def load_phases(result_dir: pathlib.Path) -> dict[str, dict[str, Any]]:
    phase_paths = tuple(sorted(result_dir.glob("*.phase.json")))
    phase_names = {
        path.name.removesuffix(".phase.json") for path in phase_paths
    }
    require_exact_names(phase_names, PHASE_ORDER, "phase inventory")
    unfinished = tuple(sorted(result_dir.glob("*.phase-start.json")))
    if unfinished:
        raise ValueError(
            "unfinished phase records: "
            + ", ".join(path.name for path in unfinished)
        )

    phases: dict[str, dict[str, Any]] = {}
    for phase_path in phase_paths:
        name = phase_path.name.removesuffix(".phase.json")
        value = read_json(phase_path)
        status_path = result_dir / f"{name}.status"
        require_regular_file(status_path, f"{name}: status")
        try:
            status_value = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{name}: status must be a JSON integer") from error
        status = require_nonnegative_int(status_value, f"{name}: status")
        phase_status = require_nonnegative_int(
            value["exit_status"], f"{name}: exit_status"
        )
        if phase_status != status:
            raise ValueError(f"{name}: phase/status exit mismatch")
        duration = require_nonnegative_number(
            value["duration_ms"], f"{name}: duration_ms"
        )
        artifacts = value.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ValueError(f"{name}: artifacts must be an object")
        require_exact_names(set(artifacts), PHASE_ARTIFACT_KEYS, f"{name}: artifacts")
        expected_artifacts = {
            "command_normalized": f"{name}.command",
            "command_raw": f"{name}.command.raw",
            "stdout": f"{name}.stdout",
            "stderr": f"{name}.stderr",
            "status": f"{name}.status",
            "trace_glob": f"{name}.trace*",
        }
        for key in PHASE_ARTIFACT_KEYS:
            if artifacts[key] != expected_artifacts[key]:
                raise ValueError(
                    f"{name}: artifact {key} must be {expected_artifacts[key]!r}"
                )
        for key in PHASE_ARTIFACT_KEYS[:-1]:
            require_regular_file(result_dir / artifacts[key], f"{name}: {key}")
        if not tuple(result_dir.glob(artifacts["trace_glob"])):
            raise ValueError(f"{name}: trace artifact set is empty")
        phases[name] = {
            "exit_status": status,
            "started_utc": require_string(value["started_utc"], f"{name}: started_utc"),
            "finished_utc": require_string(
                value["finished_utc"], f"{name}: finished_utc"
            ),
            "duration_ms": duration,
            "artifacts": dict(artifacts),
        }
    return {name: phases[name] for name in PHASE_ORDER}


def load_classifications(result_dir: pathlib.Path) -> dict[str, dict[str, Any]]:
    summary_paths = tuple(sorted(result_dir.glob("*-access.summary.json")))
    names = {
        path.name.removesuffix("-access.summary.json") for path in summary_paths
    }
    require_exact_names(names, CLASSIFICATION_ORDER, "classification inventory")
    classifications: dict[str, dict[str, Any]] = {}
    for summary_path in summary_paths:
        name = summary_path.name.removesuffix("-access.summary.json")
        classification = validate_classification(name, read_json(summary_path))
        expected_artifacts = {
            "events": f"{name}-access.tsv",
            "text_summary": f"{name}-access.summary.txt",
            "structured_summary": f"{name}-access.summary.json",
        }
        if classification["artifacts"] != expected_artifacts:
            raise ValueError(f"{name}: classification artifact mapping differs")
        for filename in expected_artifacts.values():
            require_regular_file(
                result_dir / filename, f"{name}: classification artifact"
            )
        classifications[name] = classification
    return {name: classifications[name] for name in CLASSIFICATION_ORDER}


def load_command_views(result_dir: pathlib.Path) -> dict[str, dict[str, str]]:
    command_paths = tuple(sorted(result_dir.glob("*.command")))
    names = {path.name.removesuffix(".command") for path in command_paths}
    require_exact_names(names, PHASE_ORDER, "command-view inventory")
    result: dict[str, dict[str, str]] = {}
    for command_path in command_paths:
        name = command_path.name.removesuffix(".command")
        raw_path = result_dir / f"{name}.command.raw"
        require_regular_file(command_path, f"{name}: normalized command")
        require_regular_file(raw_path, f"{name}: raw command")
        result[name] = {
            "normalized": command_path.name,
            "raw": raw_path.name,
        }
    return {name: result[name] for name in PHASE_ORDER}


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

    comparison_paths = {
        "host_fingerprint": result_dir / "host-fingerprint.diff",
        "maintainer_script": result_dir / "mmdebstrap-rerun-script.diff",
        "alternatives_state": result_dir / "mmdebstrap-rerun-alternative.diff",
    }
    for name, path in comparison_paths.items():
        require_regular_file(path, f"comparison {name}")
    comparisons = {
        "host_fingerprint_unchanged": (
            comparison_paths["host_fingerprint"].stat().st_size == 0
        ),
        "mmdebstrap_rerun": {
            "maintainer_script_equal": (
                comparison_paths["maintainer_script"].stat().st_size == 0
            ),
            "alternatives_state_equal": (
                comparison_paths["alternatives_state"].stat().st_size == 0
            ),
            "artifacts": {
                "maintainer_script_diff": "mmdebstrap-rerun-script.diff",
                "alternatives_state_diff": "mmdebstrap-rerun-alternative.diff",
            },
        },
    }
    phases_successful = all(
        phase["exit_status"] == 0 for phase in phases.values()
    )
    comparisons_successful = bool(
        comparisons["host_fingerprint_unchanged"]
        and comparisons["mmdebstrap_rerun"]["maintainer_script_equal"]
        and comparisons["mmdebstrap_rerun"]["alternatives_state_equal"]
    )
    receipt_passes = phases_successful and comparisons_successful and unresolved == 0
    if promotion_signal:
        decision = "promote"
    elif unresolved:
        decision = "blocked"
    elif not receipt_passes:
        decision = "invalid-receipt"
    else:
        decision = "retain"

    return {
        "schema_version": 4,
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
            "phases_successful": phases_successful,
            "comparisons_successful": comparisons_successful,
            "rule": (
                "promote on service action or unexpected mutation; block unresolved "
                "evidence; retain only a complete passing receipt"
            ),
        },
        "receipt_status": "passed" if receipt_passes else "failed",
        "decision": decision,
    }


def summary_passes(value: Mapping[str, Any]) -> bool:
    return value.get("receipt_status") == "passed"


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
