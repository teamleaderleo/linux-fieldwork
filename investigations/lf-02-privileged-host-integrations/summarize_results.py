#!/usr/bin/env python3
"""Build the LF-02 privileged-host integration summary.

The classifier deliberately distinguishes an explicit D-Bus AccessDenied reply
from unrelated filesystem EACCES lines elsewhere in the strace output.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any

LABELS = ("default-root", "no-inhibit-root", "isolated-root")
ACCESS_DENIED = re.compile(
    r"(?:org\.freedesktop\.DBus\.Error\.)?AccessDenied"
)


def read_text(root: pathlib.Path, name: str) -> str:
    path = root / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def marker_state(root: pathlib.Path, label: str, when: str) -> dict[str, Any]:
    value = read_text(root, f"{label}-marker-{when}.txt")
    present = "present=1" in value
    digest = None
    for line in value.splitlines():
        if re.fullmatch(r"[0-9a-f]{64}  .*", line):
            digest = line.split()[0]
            break
    return {"present": present, "sha256": digest, "raw": value.splitlines()[:4]}


def classify_case(root: pathlib.Path, label: str) -> dict[str, Any]:
    before = marker_state(root, label, "before")
    after = marker_state(root, label, "after")
    dbus_connect = read_text(root, f"{label}-dbus-connect.txt")
    logind = read_text(root, f"{label}-logind-messages.txt")
    dbus_result = read_text(root, f"{label}-dbus-result.txt")
    needrestart = read_text(root, f"{label}-needrestart.txt")

    logind_inhibit_message = (
        "Inhibit" in logind and "org.freedesktop.login1" in logind
    )
    inhibitor_fd_received = "SCM_RIGHTS" in dbus_result
    explicit_access_denied = ACCESS_DENIED.search(dbus_result) is not None
    logind_access_denied = logind_inhibit_message and explicit_access_denied

    if not logind_inhibit_message:
        logind_result = "not-observed"
    elif logind_access_denied:
        logind_result = "access-denied"
    elif inhibitor_fd_received:
        logind_result = "inhibitor-fd-received"
    else:
        logind_result = "response-unclassified"

    return {
        "exit": int(read_text(root, f"{label}.status").strip()),
        "marker_before": before,
        "marker_after": after,
        "marker_changed": before != after,
        "system_bus_connect": "/dbus/system_bus_socket" in dbus_connect,
        "logind_inhibit_message": logind_inhibit_message,
        "inhibitor_fd_received": inhibitor_fd_received,
        "logind_access_denied": logind_access_denied,
        "logind_result": logind_result,
        "needrestart_exec": "/usr/lib/needrestart/dpkg-status" in needrestart,
        "needrestart_marker_syscall": "/run/needrestart/unpacked" in needrestart,
    }


def build_summary(root: pathlib.Path) -> dict[str, Any]:
    cases = {label: classify_case(root, label) for label in LABELS}
    script_equal = (
        read_text(root, "default-root-script.normalized")
        == read_text(root, "no-inhibit-root-script.normalized")
        == read_text(root, "isolated-root-script.normalized")
    )
    alternative_equal = (
        read_text(root, "default-root-alternative.normalized")
        == read_text(root, "no-inhibit-root-alternative.normalized")
        == read_text(root, "isolated-root-alternative.normalized")
    )

    return {
        "schema_version": 2,
        "cases": cases,
        "target_script_state_equal": script_equal,
        "target_alternatives_state_equal": alternative_equal,
        "findings": {
            "privileged_needrestart_host_mutation": (
                cases["default-root"]["marker_changed"]
                and cases["default-root"]["needrestart_exec"]
            ),
            "inhibit_option_removes_system_bus_call": (
                cases["default-root"]["system_bus_connect"]
                and not cases["no-inhibit-root"]["system_bus_connect"]
            ),
            "default_inhibitor_fd_received": (
                cases["default-root"]["logind_result"]
                == "inhibitor-fd-received"
            ),
            "inhibit_controls_have_no_logind_call": (
                cases["no-inhibit-root"]["logind_result"] == "not-observed"
                and cases["isolated-root"]["logind_result"] == "not-observed"
            ),
            "disabling_host_dpkg_logger_removes_needrestart": (
                cases["no-inhibit-root"]["needrestart_exec"]
                and not cases["isolated-root"]["needrestart_exec"]
            ),
            "isolated_control_has_no_observed_host_service_action": (
                not cases["isolated-root"]["system_bus_connect"]
                and not cases["isolated-root"]["needrestart_exec"]
            ),
        },
    }


def summary_passes(summary: dict[str, Any]) -> bool:
    cases = summary["cases"]
    findings = summary["findings"]
    return bool(
        all(case["exit"] == 0 for case in cases.values())
        and summary["target_script_state_equal"]
        and summary["target_alternatives_state_equal"]
        and findings["privileged_needrestart_host_mutation"]
        and findings["inhibit_option_removes_system_bus_call"]
        and findings["default_inhibitor_fd_received"]
        and findings["inhibit_controls_have_no_logind_call"]
        and findings["disabling_host_dpkg_logger_removes_needrestart"]
        and findings["isolated_control_has_no_observed_host_service_action"]
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} RESULT_DIR", file=sys.stderr)
        return 2
    root = pathlib.Path(argv[1])
    summary = build_summary(root)
    rendered = json.dumps(summary, indent=2) + "\n"
    (root / "summary.json").write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if summary_passes(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
