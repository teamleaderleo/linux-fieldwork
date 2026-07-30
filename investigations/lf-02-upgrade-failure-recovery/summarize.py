#!/usr/bin/env python3
"""Validate and summarize the LF-02 upgrade/failure/recovery matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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
    "install-v1": ("installed", "1.0", "default=one\n"),
    "local-edit": ("installed", "1.0", "user=preserved\n"),
    "unpack-v2": ("unpacked", "2.0", "user=preserved\n"),
    "configure-v2": ("installed", "2.0", "user=preserved\n"),
    "unpack-v3-fail": ("unpacked", "3.0", "user=preserved\n"),
    "configure-v3-fail": ("half-configured", "3.0", "user=preserved\n"),
    "unpack-v3-recover": ("unpacked", "3.1", "user=preserved\n"),
    "configure-v3-recover": ("installed", "3.1", "user=preserved\n"),
    "purge": (("absent", "not-installed"), None, None),
}

CATEGORY_IDS = {
    "required_host_read",
    "harmless_runtime_interaction",
    "unexpected_mutation",
    "service_action",
    "unresolved",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_snapshot(label: str, record: dict[str, object]) -> None:
    expected_status, expected_payload, expected_conf = SNAPSHOT_EXPECTATIONS[label]
    package = record["package"]
    actual_status = package["status_word"]
    if isinstance(expected_status, tuple):
        assert actual_status in expected_status, (label, actual_status, expected_status)
    else:
        assert actual_status == expected_status, (label, actual_status, expected_status)
    assert record["payload_version"] == expected_payload, (
        label,
        record["payload_version"],
        expected_payload,
    )
    conffiles = record["conffiles"]
    principal = conffiles.get("etc/lf-lifecycle.conf")
    if expected_conf is None:
        assert principal is None, (label, principal)
    else:
        assert principal is not None, (label, conffiles)
        assert principal["content"] == expected_conf, (label, principal)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    results = args.results.resolve()
    target = str(Path(args.target).resolve())
    provenance = load_json(results / "provenance.json")
    fixtures = load_json(results / "fixtures/manifest.json")

    phases: dict[str, dict[str, object]] = {}
    for path in sorted(results.glob("*.phase.json")):
        record = load_json(path)
        assert record["schema_version"] == 1
        assert record["duration_ms"] >= 0
        phases[record["name"]] = record
    assert tuple(name for name in PHASE_ORDER if name in phases) == PHASE_ORDER
    assert set(phases) == set(PHASE_ORDER)
    for name in PHASE_ORDER:
        phase = phases[name]
        if name == "configure-v3-fail":
            assert phase["expected_exit"] == "nonzero"
            assert phase["exit_status"] != 0
        else:
            assert phase["expected_exit"] == "0"
            assert phase["exit_status"] == 0

    snapshots: dict[str, dict[str, object]] = {}
    for label in SNAPSHOT_EXPECTATIONS:
        record = load_json(results / f"{label}.snapshot.json")
        assert record["schema_version"] == 1
        validate_snapshot(label, record)
        snapshots[label] = record

    final_script_log = snapshots["purge"]["script_log"]
    assert final_script_log
    for line in final_script_log:
        assert f"dpkg_root={target}" in line, line
        assert f"cwd={target}" in line, line
    assert any("phase=postinst script_version=3.0" in line for line in final_script_log)
    assert any("phase=postinst script_version=3.1" in line for line in final_script_log)

    classifications: dict[str, dict[str, object]] = {}
    totals = {identifier: 0 for identifier in CATEGORY_IDS}
    for name in PHASE_ORDER:
        record = load_json(results / f"{name}-access.summary.json")
        assert record["schema_version"] == 1
        assert set(record["categories"]) == CATEGORY_IDS
        assert record["category_total_matches_events"] is True
        assert record["category_total"] == record["outside_access_events"]
        classifications[name] = record
        for identifier, count in record["categories"].items():
            totals[identifier] += count

    host_diff = (results / "host-fingerprint.diff").read_text(encoding="utf-8")
    host_fingerprint_unchanged = not host_diff
    lifecycle_contract = True
    product_candidate = (
        totals["unexpected_mutation"] > 0
        or not host_fingerprint_unchanged
        or not lifecycle_contract
    )

    conffile_siblings = {
        label: sorted(record["conffiles"])
        for label, record in snapshots.items()
    }
    summary = {
        "schema_version": 1,
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
            "unresolved": totals["unresolved"],
            "host_fingerprint_unchanged": host_fingerprint_unchanged,
            "product_candidate": product_candidate,
        },
        "disposition": "promote-product-candidate" if product_candidate else "retain-mapped-behavior",
        "authority": "internal Linux Fieldwork investigation; no upstream contact",
    }
    (results / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
