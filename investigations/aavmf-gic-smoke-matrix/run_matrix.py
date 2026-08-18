#!/usr/bin/env python3
"""Run an AAVMF boot matrix with one pinned x86_64 QEMU under TCG."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
CASE_NIX = pathlib.Path(__file__).with_name("case.nix")
MODES = ("default", "2", "3", "max")
DEFAULT_REVISIONS = {
    "known-good": "d41f19d0a8017b17cc4d527938bcf94a3e0b0a81",
    "known-bad": "45788a75f5dbf0f449f6168b2fd647d49135e841",
    "current": "396e6226eab2fd092b1690abcd33ea522fde16dc",
}
DEFAULT_QEMU_REVISION = "396e6226eab2fd092b1690abcd33ea522fde16dc"


class MatrixError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixError(message)


def run_command(
    command: list[str],
    *,
    cwd: pathlib.Path,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> tuple[int, str, bool, int]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        return (
            completed.returncode,
            completed.stdout,
            False,
            round((time.monotonic() - started) * 1000),
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if not isinstance(output, str):
            output = output.decode(errors="replace")
        output += f"\nFIELDWORK infrastructure timeout after {timeout} seconds\n"
        return 124, output, True, round((time.monotonic() - started) * 1000)


def build_case_app(
    *,
    label: str,
    firmware_revision: str,
    qemu_revision: str,
    results: pathlib.Path,
    timeout: int,
) -> dict[str, Any]:
    log_path = results / f"build-{label}.log"
    environment = os.environ.copy()
    environment.update(
        {
            "FIELDWORK_CASE_NIX": str(CASE_NIX),
            "FIELDWORK_FIRMWARE_REV": firmware_revision,
            "FIELDWORK_QEMU_REV": qemu_revision,
        }
    )
    expression = """
      (import (builtins.toPath (builtins.getEnv "FIELDWORK_CASE_NIX"))) {
        firmwareRev = builtins.getEnv "FIELDWORK_FIRMWARE_REV";
        qemuRev = builtins.getEnv "FIELDWORK_QEMU_REV";
      }
    """
    status, output, timed_out, duration_ms = run_command(
        [
            "nix",
            "build",
            "--impure",
            "--no-link",
            "--print-out-paths",
            "--print-build-logs",
            "--expr",
            expression,
        ],
        cwd=ROOT,
        environment=environment,
        timeout=timeout,
    )
    log_path.write_text(output, encoding="utf-8")
    store_paths = [line.strip() for line in output.splitlines() if line.startswith("/nix/store/")]
    app = pathlib.Path(store_paths[-1]) if status == 0 and store_paths else None
    executable = app / "bin/aavmf-gic-case" if app is not None else None
    validation_error: str | None = None
    if status == 0 and app is None:
        status = 2
        validation_error = "Nix reported success without a store path"
    elif status == 0 and (executable is None or not executable.is_file()):
        status = 2
        validation_error = "case executable is absent from the returned store path"
    elif status == 0 and executable is not None and not os.access(executable, os.X_OK):
        status = 2
        validation_error = "case executable is not executable"
    return {
        "schema_version": 1,
        "revision_label": label,
        "firmware_revision": firmware_revision,
        "qemu_revision": qemu_revision,
        "exit_status": status,
        "infrastructure_timeout": timed_out,
        "duration_ms": duration_ms,
        "log": log_path.name,
        "app_store_path": str(app) if app is not None else None,
        "executable": str(executable) if executable is not None else None,
        "validation_error": validation_error,
    }


def log_symptoms(log: str) -> dict[str, bool]:
    lowered = log.lower()
    return {
        "firmware_banner": "uefi firmware" in lowered,
        "systemd_boot": "systemd-boot" in lowered or "boot in 5 s." in lowered,
        "pxe": "pxe" in lowered,
        "assertion": "assert" in lowered,
        "qemu_error": "qemu-system-aarch64:" in lowered,
    }


def run_case(
    *,
    build: dict[str, Any],
    mode: str,
    results: pathlib.Path,
    timeout: int,
    qemu_timeout: int,
) -> dict[str, Any]:
    label = str(build["revision_label"])
    case_name = f"{label}--gic-{mode}"
    case_dir = results / case_name
    executable = build.get("executable")
    require(isinstance(executable, str) and executable, f"{label}: no executable for case")
    environment = os.environ.copy()
    environment["AAVMF_CASE_TIMEOUT"] = str(qemu_timeout)
    status, output, timed_out, duration_ms = run_command(
        [executable, mode, str(case_dir)],
        cwd=ROOT,
        environment=environment,
        timeout=timeout,
    )
    wrapper_log = results / f"{case_name}.wrapper.log"
    wrapper_log.write_text(output, encoding="utf-8")
    qemu_log_path = case_dir / "qemu.log"
    qemu_log = qemu_log_path.read_text(encoding="utf-8", errors="replace") if qemu_log_path.is_file() else ""
    outcome_path = case_dir / "outcome.txt"
    outcome = outcome_path.read_text(encoding="utf-8").strip() if outcome_path.is_file() else "missing"
    return {
        "schema_version": 1,
        "case": case_name,
        "revision_label": label,
        "firmware_revision": build["firmware_revision"],
        "qemu_revision": build["qemu_revision"],
        "gic_mode": mode,
        "exit_status": status,
        "passed": status == 0 and outcome == "pass",
        "outcome": outcome,
        "infrastructure_timeout": timed_out,
        "duration_ms": duration_ms,
        "wrapper_log": wrapper_log.name,
        "qemu_log": str(qemu_log_path.relative_to(results)) if qemu_log_path.is_file() else None,
        "symptoms": log_symptoms(qemu_log),
    }


def classify(cases: dict[str, dict[str, Any]]) -> str:
    passed = {mode for mode, record in cases.items() if record["passed"] is True}
    if passed == set(MODES):
        return "all-gic-modes-reach-systemd-boot"
    if "default" in passed and "max" not in passed:
        if "2" in passed and "3" not in passed:
            return "gicv3-and-max-fail"
        if "3" in passed:
            return "max-only-fails"
        return "default-passes-max-fails-with-additional-gic-failures"
    if "default" not in passed:
        return "default-mode-does-not-reach-systemd-boot"
    return "mixed-gic-results"


def build_summary(
    builds: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    revisions: dict[str, str],
    qemu_revision: str,
) -> dict[str, Any]:
    require(set(revisions) == {"known-good", "known-bad", "current"}, "unexpected revision labels")
    require(len(builds) == len(revisions), "incomplete build set")
    build_by_label = {str(record["revision_label"]): record for record in builds}
    require(set(build_by_label) == set(revisions), "build labels do not match revisions")

    by_revision: dict[str, dict[str, dict[str, Any]]] = {label: {} for label in revisions}
    for record in cases:
        label = str(record["revision_label"])
        mode = str(record["gic_mode"])
        require(label in by_revision, f"unknown revision label: {label}")
        require(mode in MODES, f"unknown GIC mode: {mode}")
        require(mode not in by_revision[label], f"duplicate case: {label}/{mode}")
        by_revision[label][mode] = record

    build_success = all(record["exit_status"] == 0 for record in builds)
    no_infrastructure_timeout = not any(record["infrastructure_timeout"] for record in builds + cases)
    complete_case_set = all(set(records) == set(MODES) for records in by_revision.values())
    complete_execution = (
        build_success
        and no_infrastructure_timeout
        and complete_case_set
        and len(cases) == len(revisions) * len(MODES)
    )
    good_default = by_revision["known-good"].get("default")
    good_default_passed = good_default is not None and good_default["passed"] is True
    valid_environment = complete_execution and good_default_passed

    classifications: dict[str, str] = {}
    for label, records in by_revision.items():
        if build_by_label[label]["exit_status"] != 0:
            classifications[label] = "case-app-build-failed"
        elif set(records) != set(MODES):
            classifications[label] = "incomplete-execution"
        else:
            classifications[label] = classify(records)

    bad_default = by_revision["known-bad"].get("default")
    bad_max = by_revision["known-bad"].get("max")
    tcg_reproduces_reported_boundary = (
        valid_environment
        and bad_default is not None
        and bad_default["passed"] is True
        and bad_max is not None
        and bad_max["passed"] is False
    )

    return {
        "schema_version": 1,
        "question": "does the reported AAVMF GIC boundary reproduce under x86_64-hosted TCG",
        "firmware_revisions": revisions,
        "qemu_revision": qemu_revision,
        "host_system": "x86_64-linux",
        "guest_system": "aarch64-linux",
        "accelerator": "tcg",
        "gic_modes": list(MODES),
        "github_actions": {
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "head_sha": os.environ.get("GITHUB_SHA"),
        },
        "controls": {
            "all_builds_succeeded": build_success,
            "no_infrastructure_timeout": no_infrastructure_timeout,
            "known_good_default_passed": good_default_passed,
            "complete_case_set": complete_case_set,
            "complete_execution": complete_execution,
        },
        "valid_environment": valid_environment,
        "tcg_reproduces_reported_boundary": tcg_reproduces_reported_boundary,
        "classifications": classifications,
        "current_decision": classifications["current"] if valid_environment else "environment-invalid",
        "builds": builds,
        "cases": cases,
        "overlap": {
            "nixpkgs_489505": "active QEMU_PV_VARS draft; does not carry this GIC matrix",
            "nixpkgs_522698": "active OVMF package-set refactor; does not carry this GIC matrix",
        },
        "authority": "internal Linux Fieldwork investigation; no upstream contact",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=pathlib.Path, required=True)
    parser.add_argument("--known-good", default=DEFAULT_REVISIONS["known-good"])
    parser.add_argument("--known-bad", default=DEFAULT_REVISIONS["known-bad"])
    parser.add_argument("--current", default=DEFAULT_REVISIONS["current"])
    parser.add_argument("--qemu-revision", default=DEFAULT_QEMU_REVISION)
    parser.add_argument("--build-timeout", type=int, default=2400)
    parser.add_argument("--case-timeout", type=int, default=120)
    parser.add_argument("--qemu-timeout", type=int, default=60)
    args = parser.parse_args()

    try:
        require(CASE_NIX.is_file(), f"missing case expression: {CASE_NIX}")
        require(args.build_timeout > 0, "build timeout must be positive")
        require(
            args.case_timeout > args.qemu_timeout > 0,
            "case timeout must exceed positive QEMU timeout",
        )
    except MatrixError as exc:
        print(f"matrix configuration failed: {exc}", file=sys.stderr)
        return 2

    results = args.results.resolve()
    if results.exists():
        print(f"refusing to reuse results directory: {results}", file=sys.stderr)
        return 2
    results.mkdir(parents=True)

    revisions = {
        "known-good": args.known_good,
        "known-bad": args.known_bad,
        "current": args.current,
    }
    builds: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    try:
        for label, revision in revisions.items():
            print(f"building exact case app for {label} at {revision}", flush=True)
            build = build_case_app(
                label=label,
                firmware_revision=revision,
                qemu_revision=args.qemu_revision,
                results=results,
                timeout=args.build_timeout,
            )
            builds.append(build)
            (results / f"build-{label}.json").write_text(
                json.dumps(build, indent=2) + "\n", encoding="utf-8"
            )
            if build["exit_status"] != 0:
                continue
            for mode in MODES:
                print(f"running {label} with GIC mode {mode}", flush=True)
                record = run_case(
                    build=build,
                    mode=mode,
                    results=results,
                    timeout=args.case_timeout,
                    qemu_timeout=args.qemu_timeout,
                )
                cases.append(record)
                (results / f"{record['case']}.json").write_text(
                    json.dumps(record, indent=2) + "\n", encoding="utf-8"
                )
                print(
                    f"completed {record['case']}: outcome={record['outcome']} "
                    f"status={record['exit_status']}",
                    flush=True,
                )

        summary = build_summary(builds, cases, revisions, args.qemu_revision)
    except (MatrixError, OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError) as exc:
        print(f"matrix validation failed: {exc}", file=sys.stderr)
        return 2

    (results / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["valid_environment"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
