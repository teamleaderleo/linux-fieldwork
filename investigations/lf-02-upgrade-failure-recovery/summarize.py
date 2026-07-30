#!/usr/bin/env python3
"""Validate and summarize the LF-02 upgrade/failure/recovery matrix."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


PHASE_ORDER = (
    "install-v1",
    "unpack-v2",
    "configure-v2",
    "unpack-v3-fail",
    "configure-v3-fail",
    "unpack-v3-recover",
    "configure-v3-recover",
    "purge",
)

SNAPSHOT_EXPECTATIONS = {
    "install-v1": ("installed", "1.0"),
    "local-edit": ("installed", "1.0"),
    "unpack-v2": ("unpacked", "2.0"),
    "configure-v2": ("installed", "2.0"),
    "unpack-v3-fail": ("unpacked", "3.0"),
    "configure-v3-fail": ("half-configured", "3.0"),
    "unpack-v3-recover": ("unpacked", "3.1"),
    "configure-v3-recover": ("installed", "3.1"),
    "purge": (("absent", "not-installed"), None),
}

CONFFILE_EXPECTATIONS = {
    "install-v1": {"etc/lf-lifecycle.conf": "default=one\n"},
    "local-edit": {"etc/lf-lifecycle.conf": "user=preserved\n"},
    "unpack-v2": {
        "etc/lf-lifecycle.conf": "user=preserved\n",
        "etc/lf-lifecycle.conf.dpkg-new": "default=two\n",
    },
    "configure-v2": {
        "etc/lf-lifecycle.conf": "user=preserved\n",
        "etc/lf-lifecycle.conf.dpkg-dist": "default=two\n",
    },
    "unpack-v3-fail": {
        "etc/lf-lifecycle.conf": "user=preserved\n",
        "etc/lf-lifecycle.conf.dpkg-dist": "default=two\n",
        "etc/lf-lifecycle.conf.dpkg-new": "default=three\n",
    },
    "configure-v3-fail": {
        "etc/lf-lifecycle.conf": "user=preserved\n",
        "etc/lf-lifecycle.conf.dpkg-dist": "default=three\n",
    },
    "unpack-v3-recover": {
        "etc/lf-lifecycle.conf": "user=preserved\n",
        "etc/lf-lifecycle.conf.dpkg-dist": "default=three\n",
        "etc/lf-lifecycle.conf.dpkg-new": "default=three-recovered\n",
    },
    "configure-v3-recover": {
        "etc/lf-lifecycle.conf": "user=preserved\n",
        "etc/lf-lifecycle.conf.dpkg-dist": "default=three-recovered\n",
    },
    "purge": {},
}

CATEGORY_IDS = {
    "required_host_read",
    "harmless_runtime_interaction",
    "unexpected_mutation",
    "service_action",
    "unresolved",
}

MAPPED_SERVICE_EXECUTABLE = "/usr/lib/needrestart/dpkg-status"
MAPPED_SERVICE_PATHS = {
    "/run/needrestart",
    "/run/needrestart/unpacked",
    "/run/needrestart/errored",
}
SCRIPT_LOG_REQUIRED_FIELDS = {"phase", "script_version", "dpkg_root", "cwd"}


class ValidationError(RuntimeError):
    """Raised when retained evidence violates the declared contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(record, dict), f"{path}: expected a JSON object")
    return record


def validate_snapshot(label: str, record: dict[str, Any]) -> None:
    expected_status, expected_payload = SNAPSHOT_EXPECTATIONS[label]
    package = record["package"]
    actual_status = package["status_word"]
    if isinstance(expected_status, tuple):
        require(
            actual_status in expected_status,
            f"{label}: status {actual_status!r} outside {expected_status!r}",
        )
    else:
        require(
            actual_status == expected_status,
            f"{label}: status {actual_status!r}, expected {expected_status!r}",
        )
    require(
        record["payload_version"] == expected_payload,
        f"{label}: payload {record['payload_version']!r}, expected {expected_payload!r}",
    )

    conffiles = record["conffiles"]
    require(isinstance(conffiles, dict), f"{label}: conffiles must be an object")
    expected_conffiles = CONFFILE_EXPECTATIONS[label]
    require(
        set(conffiles) == set(expected_conffiles),
        f"{label}: conffile paths {sorted(conffiles)!r}, expected {sorted(expected_conffiles)!r}",
    )
    for path, expected_content in expected_conffiles.items():
        actual = conffiles[path]
        require(isinstance(actual, dict), f"{label}: {path} metadata must be an object")
        require(
            actual.get("content") == expected_content,
            f"{label}: {path} content {actual.get('content')!r}, expected {expected_content!r}",
        )


def parse_script_log_line(line: str) -> dict[str, str]:
    """Parse the probe's space-delimited key=value script log format exactly."""

    require(isinstance(line, str) and bool(line), "script log line must be non-empty text")
    fields: dict[str, str] = {}
    for token in line.split():
        require("=" in token, f"script log token is not key=value: {token!r}")
        key, value = token.split("=", 1)
        require(bool(key) and bool(value), f"script log token is incomplete: {token!r}")
        require(key not in fields, f"script log repeats field {key!r}: {line}")
        fields[key] = value
    require(
        SCRIPT_LOG_REQUIRED_FIELDS.issubset(fields),
        f"script log fields {sorted(fields)!r} omit required fields",
    )
    return fields


def mapped_service_action(row: dict[str, str]) -> bool:
    operation = row["operation"]
    path = row["path"]
    result = row["result"]
    if (
        operation == "execution"
        and path == MAPPED_SERVICE_EXECUTABLE
        and result == "0"
    ):
        return True
    return (
        operation == "mutation"
        and path in MAPPED_SERVICE_PATHS
        and result.startswith("-1 ")
    )


def contained_artifact(results: Path, name: str, artifact_name: str) -> Path:
    relative = Path(artifact_name)
    require(not relative.is_absolute(), f"{name}: artifact path must be relative")
    require(".." not in relative.parts, f"{name}: artifact path contains parent traversal")
    results_root = results.resolve(strict=True)
    path = (results_root / relative).resolve(strict=True)
    require(
        path.is_relative_to(results_root),
        f"{name}: artifact path escaped results: {artifact_name}",
    )
    require(path.is_file(), f"{name}: missing classifier event file {artifact_name}")
    return path


def classify_service_actions(
    results: Path, name: str, record: dict[str, Any], expected_count: int
) -> tuple[int, int]:
    artifacts = record.get("artifacts", {})
    require(isinstance(artifacts, dict), f"{name}: artifacts must be an object")
    event_name = artifacts.get("events", f"{name}-access.tsv")
    require(isinstance(event_name, str) and event_name, f"{name}: missing event file")
    event_path = contained_artifact(results, name, event_name)

    with event_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required_columns = {"operation", "path", "result", "category"}
        require(
            reader.fieldnames is not None
            and required_columns.issubset(reader.fieldnames),
            f"{name}: classifier event columns are incomplete",
        )
        service_rows = [
            row for row in reader if row.get("category") == "service action"
        ]

    require(
        len(service_rows) == expected_count,
        f"{name}: service-action rows {len(service_rows)}, expected {expected_count}",
    )
    mapped = sum(mapped_service_action(row) for row in service_rows)
    return mapped, len(service_rows) - mapped


def build_summary(results: Path, target: str) -> dict[str, Any]:
    provenance = load_json(results / "provenance.json")
    fixtures = load_json(results / "fixtures/manifest.json")

    phases: dict[str, dict[str, Any]] = {}
    for path in sorted(results.glob("*.phase.json")):
        record = load_json(path)
        require(record.get("schema_version") == 1, f"{path.name}: unsupported schema")
        require(record.get("duration_ms", -1) >= 0, f"{path.name}: negative duration")
        name = record.get("name")
        require(isinstance(name, str), f"{path.name}: missing phase name")
        require(name not in phases, f"duplicate phase record: {name}")
        phases[name] = record
    require(set(phases) == set(PHASE_ORDER), f"phase set mismatch: {sorted(phases)!r}")
    for name in PHASE_ORDER:
        phase = phases[name]
        if name == "configure-v3-fail":
            require(phase.get("expected_exit") == "nonzero", f"{name}: expected_exit")
            require(phase.get("exit_status") != 0, f"{name}: deliberate failure succeeded")
        else:
            require(phase.get("expected_exit") == "0", f"{name}: expected_exit")
            require(phase.get("exit_status") == 0, f"{name}: nonzero exit")

    snapshots: dict[str, dict[str, Any]] = {}
    for label in SNAPSHOT_EXPECTATIONS:
        record = load_json(results / f"{label}.snapshot.json")
        require(record.get("schema_version") == 1, f"{label}: unsupported schema")
        validate_snapshot(label, record)
        snapshots[label] = record

    final_script_log = snapshots["purge"]["script_log"]
    require(isinstance(final_script_log, list) and bool(final_script_log), "empty script log")
    script_records = [parse_script_log_line(line) for line in final_script_log]
    for fields in script_records:
        require(
            fields["dpkg_root"] == target,
            f"script log has wrong dpkg_root: {fields['dpkg_root']!r}",
        )
        require(
            fields["cwd"] == target,
            f"script log has wrong cwd: {fields['cwd']!r}",
        )
    require(
        any(
            fields["phase"] == "postinst" and fields["script_version"] == "3.0"
            for fields in script_records
        ),
        "missing failing 3.0 postinst log",
    )
    require(
        any(
            fields["phase"] == "postinst" and fields["script_version"] == "3.1"
            for fields in script_records
        ),
        "missing recovery 3.1 postinst log",
    )

    classifications: dict[str, dict[str, Any]] = {}
    totals = {identifier: 0 for identifier in CATEGORY_IDS}
    mapped_service_actions = 0
    unmapped_service_actions = 0
    for name in PHASE_ORDER:
        record = load_json(results / f"{name}-access.summary.json")
        require(record.get("schema_version") == 1, f"{name}: unsupported classifier schema")
        categories = record.get("categories")
        require(isinstance(categories, dict), f"{name}: categories must be an object")
        require(set(categories) == CATEGORY_IDS, f"{name}: category set mismatch")
        for identifier, count in categories.items():
            require(isinstance(count, int) and count >= 0, f"{name}: invalid {identifier} count")
        computed_total = sum(categories.values())
        require(
            record.get("category_total_matches_events") is True,
            f"{name}: classifier category total flag is false",
        )
        require(
            record.get("category_total") == computed_total,
            f"{name}: category total differs from category counts",
        )
        require(
            record.get("outside_access_events") == computed_total,
            f"{name}: outside access events differ from category counts",
        )
        mapped, unmapped = classify_service_actions(
            results, name, record, categories["service_action"]
        )
        mapped_service_actions += mapped
        unmapped_service_actions += unmapped
        classifications[name] = record
        for identifier, count in categories.items():
            totals[identifier] += count

    host_diff = (results / "host-fingerprint.diff").read_text(encoding="utf-8")
    host_fingerprint_unchanged = not host_diff
    lifecycle_contract = True
    product_candidate = (
        totals["unexpected_mutation"] > 0
        or unmapped_service_actions > 0
        or not host_fingerprint_unchanged
        or not lifecycle_contract
    )
    blocked_unresolved = totals["unresolved"] > 0 and not product_candidate
    if product_candidate:
        disposition = "promote-product-candidate"
    elif blocked_unresolved:
        disposition = "blocked-unresolved"
    else:
        disposition = "retain-mapped-behavior"

    conffile_siblings = {
        label: sorted(record["conffiles"])
        for label, record in snapshots.items()
    }
    return {
        "schema_version": 1,
        "decision_policy_version": 2,
        "question": "chrootless dpkg upgrade, expected configure failure, recovery, and purge",
        "provenance": provenance,
        "fixtures": fixtures,
        "target": target,
        "phases": {name: phases[name] for name in PHASE_ORDER},
        "snapshots": {
            label: {
                "package": record["package"],
                "payload_version": record["payload_version"],
                "conffile_paths": conffile_siblings[label],
                "script_log_lines": len(record["script_log"]),
                "artifacts": record["artifacts"],
            }
            for label, record in snapshots.items()
        },
        "classifications": classifications,
        "classification_totals": totals,
        "observations": {
            "separate_unpack_configure_v2": True,
            "modified_conffile_preserved_through_recovery": True,
            "failed_configure_exit_status": phases["configure-v3-fail"]["exit_status"],
            "failed_configure_target_status": snapshots["configure-v3-fail"]["package"]["status_word"],
            "recovery_target_status": snapshots["configure-v3-recover"]["package"]["status_word"],
            "recovery_payload_version": snapshots["configure-v3-recover"]["payload_version"],
            "purge_target_status": snapshots["purge"]["package"]["status_word"],
            "purge_principal_conffile_absent": "etc/lf-lifecycle.conf" not in snapshots["purge"]["conffiles"],
            "maintainer_script_log_remains_below_target_after_purge": bool(snapshots["purge"]["script_log"]),
            "host_fingerprint_unchanged": host_fingerprint_unchanged,
        },
        "decision_inputs": {
            "lifecycle_contract_satisfied": lifecycle_contract,
            "unexpected_mutations": totals["unexpected_mutation"],
            "service_actions": totals["service_action"],
            "mapped_needrestart_actions": mapped_service_actions,
            "unmapped_service_actions": unmapped_service_actions,
            "environment_sensitive_host_hooks": mapped_service_actions > 0,
            "unresolved": totals["unresolved"],
            "host_fingerprint_unchanged": host_fingerprint_unchanged,
            "product_candidate": product_candidate,
            "blocked_unresolved": blocked_unresolved,
        },
        "disposition": disposition,
        "authority": "internal Linux Fieldwork investigation; no upstream contact",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    results = args.results.resolve()
    target = str(Path(args.target).resolve())
    try:
        summary = build_summary(results, target)
    except (ValidationError, FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"evidence validation failed: {exc}", file=sys.stderr)
        return 2

    (results / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
