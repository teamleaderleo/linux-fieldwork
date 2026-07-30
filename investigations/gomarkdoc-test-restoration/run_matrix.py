#!/usr/bin/env python3
"""Run the gomarkdoc check-restoration matrix against exact Nixpkgs revisions."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

MODES = (
    "baseline",
    "unset-goflags",
    "filter-goflags",
    "add-fixture",
    "add-fixture-unset-goflags",
)
DEFAULT_REVISIONS = {
    "known-good": "4590696c8693fea477850fe379a01544293ca4e2",
    "known-bad": "acd02b8",
    "current": "396e6226eab2fd092b1690abcd33ea522fde16dc",
}
ROOT = pathlib.Path(__file__).resolve().parents[2]
MATRIX = pathlib.Path(__file__).with_name("matrix.nix")


def symptom_counts(log: str) -> dict[str, int]:
    return {
        "unsupported_mod_flag": log.count("flag provided but not defined: -mod"),
        "unsupported_other_flag": log.count("flag provided but not defined: -other"),
        "missing_empty_config": log.count(
            "open ../.gomarkdoc-empty.yml: no such file or directory"
        ),
        "gomarkdoc_package_fail": log.count(
            "FAIL\tgithub.com/princjef/gomarkdoc/cmd/gomarkdoc"
        )
        + log.count("FAIL  github.com/princjef/gomarkdoc/cmd/gomarkdoc"),
        "go_test_pass": log.count("PASS"),
    }


def classify_revision(cases: dict[str, dict[str, Any]]) -> str:
    """Classify only from exit status; log symptoms remain separate evidence."""

    passed = {mode for mode, record in cases.items() if record["exit_status"] == 0}
    if "baseline" in passed:
        return "suite-passes-unchanged"

    flag_only = bool(passed & {"unset-goflags", "filter-goflags"})
    fixture_only = "add-fixture" in passed
    combined = "add-fixture-unset-goflags" in passed

    if flag_only and not fixture_only:
        return "test-time-goflags-is-sufficient"
    if fixture_only and not flag_only:
        return "missing-fixture-is-sufficient"
    if flag_only and fixture_only:
        return "either-narrow-repair-is-sufficient"
    if combined:
        return "fixture-and-test-flags-interact"
    return "no-tested-repair-restores-suite"


def run_case(
    *,
    label: str,
    revision: str,
    mode: str,
    results: pathlib.Path,
    timeout: int,
) -> dict[str, Any]:
    case_name = f"{label}--{mode}"
    log_path = results / f"{case_name}.log"
    environment = os.environ.copy()
    environment.update(
        {
            "FIELDWORK_MATRIX_NIX": str(MATRIX),
            "FIELDWORK_NIXPKGS_REV": revision,
            "FIELDWORK_MATRIX_MODE": mode,
        }
    )
    expression = """
      (import (builtins.toPath (builtins.getEnv "FIELDWORK_MATRIX_NIX"))) {
        nixpkgsRev = builtins.getEnv "FIELDWORK_NIXPKGS_REV";
        mode = builtins.getEnv "FIELDWORK_MATRIX_MODE";
      }
    """
    command = [
        "nix",
        "build",
        "--impure",
        "--no-link",
        "--print-build-logs",
        "--expr",
        expression,
    ]
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        status = completed.returncode
        log = completed.stdout
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        status = 124
        stdout = exc.stdout or ""
        log = stdout if isinstance(stdout, str) else stdout.decode(errors="replace")
        log += f"\nFIELDWORK case timed out after {timeout} seconds\n"

    duration_ms = round((time.monotonic() - started) * 1000)
    log_path.write_text(log, encoding="utf-8")
    return {
        "schema_version": 1,
        "case": case_name,
        "revision_label": label,
        "nixpkgs_revision": revision,
        "mode": mode,
        "exit_status": status,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "log": log_path.name,
        "symptoms": symptom_counts(log),
    }


def build_summary(
    records: list[dict[str, Any]], revisions: dict[str, str]
) -> dict[str, Any]:
    by_revision: dict[str, dict[str, dict[str, Any]]] = {
        label: {} for label in revisions
    }
    for record in records:
        label = record["revision_label"]
        mode = record["mode"]
        if mode in by_revision[label]:
            raise ValueError(f"duplicate matrix case: {label}/{mode}")
        by_revision[label][mode] = record

    for label, cases in by_revision.items():
        missing = sorted(set(MODES) - set(cases))
        extra = sorted(set(cases) - set(MODES))
        if missing or extra:
            raise ValueError(f"{label}: missing={missing}, extra={extra}")

    controls = {
        "known_good_baseline_passed": by_revision["known-good"]["baseline"][
            "exit_status"
        ]
        == 0,
        "known_bad_baseline_failed": by_revision["known-bad"]["baseline"][
            "exit_status"
        ]
        != 0,
        "no_case_timed_out": not any(record["timed_out"] for record in records),
    }
    valid_reproduction = all(controls.values())
    classifications = {
        label: classify_revision(cases) for label, cases in by_revision.items()
    }

    return {
        "schema_version": 1,
        "question": (
            "which narrow boundary restores gomarkdoc v1.1.0 checks without "
            "weakening buildGoModule vendoring"
        ),
        "revisions": revisions,
        "modes": list(MODES),
        "github_actions": {
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "head_sha": os.environ.get("GITHUB_SHA"),
        },
        "controls": controls,
        "valid_reproduction": valid_reproduction,
        "classifications": classifications,
        "current_decision": classifications["current"],
        "cases": records,
        "authority": "internal Linux Fieldwork investigation; no upstream contact",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=pathlib.Path, required=True)
    parser.add_argument("--known-good", default=DEFAULT_REVISIONS["known-good"])
    parser.add_argument("--known-bad", default=DEFAULT_REVISIONS["known-bad"])
    parser.add_argument("--current", default=DEFAULT_REVISIONS["current"])
    parser.add_argument("--case-timeout", type=int, default=1800)
    args = parser.parse_args()

    if not MATRIX.is_file():
        print(f"missing matrix expression: {MATRIX}", file=sys.stderr)
        return 2
    if args.case_timeout < 1:
        print("case timeout must be positive", file=sys.stderr)
        return 2

    results = args.results.resolve()
    try:
        results.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"refusing to reuse results directory: {results}", file=sys.stderr)
        return 2

    revisions = {
        "known-good": args.known_good,
        "known-bad": args.known_bad,
        "current": args.current,
    }
    records: list[dict[str, Any]] = []
    for label, revision in revisions.items():
        for mode in MODES:
            print(f"running {label}/{mode} at {revision}", flush=True)
            record = run_case(
                label=label,
                revision=revision,
                mode=mode,
                results=results,
                timeout=args.case_timeout,
            )
            records.append(record)
            (results / f"{record['case']}.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )
            print(
                f"completed {record['case']}: status={record['exit_status']} "
                f"duration_ms={record['duration_ms']}",
                flush=True,
            )

    try:
        summary = build_summary(records, revisions)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"matrix validation failed: {exc}", file=sys.stderr)
        return 2

    summary_path = results / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["valid_reproduction"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
