#!/usr/bin/env python3
"""Verify the source chain behind the systemd-oomd reporter collision hypothesis."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any

PINNED_SYSTEMD = "6a863b4dc31adc49fdfdd5deba32ed1b115adda3"
PINNED_TEST_BLOB = "43937c6ec7877df23f66ccd3827a1b6f154943ff"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(root: pathlib.Path, relative: str) -> str:
    path = root / relative
    require(path.is_file(), f"missing source file: {relative}")
    return path.read_text(encoding="utf-8")


def git_output(root: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def contains_all(source: str, fragments: list[str], label: str) -> None:
    missing = [fragment for fragment in fragments if fragment not in source]
    require(not missing, f"{label}: missing source fragments: {missing!r}")


def verify(root: pathlib.Path) -> dict[str, Any]:
    revision = git_output(root, "rev-parse", "HEAD")
    require(revision == PINNED_SYSTEMD, f"unexpected systemd revision: {revision}")

    paths = {
        "cgroup": "src/core/cgroup.c",
        "unit": "src/core/unit.c",
        "varlink": "src/core/varlink.c",
        "oomd": "src/oom/oomd-manager.c",
        "test": "test/units/TEST-55-OOMD.sh",
    }
    blobs = {name: git_output(root, "hash-object", path) for name, path in paths.items()}
    require(blobs["test"] == PINNED_TEST_BLOB, f"unexpected TEST-55-OOMD blob: {blobs['test']}")

    cgroup = load(root, paths["cgroup"])
    unit = load(root, paths["unit"])
    varlink = load(root, paths["varlink"])
    oomd = load(root, paths["oomd"])
    test = load(root, paths["test"])

    contains_all(
        cgroup,
        [
            "r = cg_pid_get_path(0, &m->cgroup_root);",
            "if (unit_has_name(u, SPECIAL_ROOT_SLICE))\n                p = strdup(u->manager->cgroup_root);",
            ".moom_mem_pressure = MANAGED_OOM_AUTO,",
        ],
        "user-manager root identity",
    )
    contains_all(
        unit,
        [
            "(void) manager_varlink_send_managed_oom_update(u);",
            "We finished loading, let's ensure our parents recalculate the members mask",
        ],
        "reload publication",
    )
    contains_all(
        varlink,
        [
            "mode = managed_oom_mode_to_string(c->moom_mem_pressure);",
            "r = sd_json_variant_append_array(&arr, e);",
            "sd_varlink_send(u->manager->managed_oom_varlink, \"io.systemd.oom.ReportManagedOOMCGroups\", v);",
        ],
        "user-manager ManagedOOM report",
    )
    contains_all(
        oomd,
        [
            "if (message.mode == MANAGED_OOM_AUTO)",
            "hashmap_remove(monitor_hm, empty_to_root(message.path))",
            "r = sd_varlink_get_peer_uid(link, &uid);",
        ],
        "path-only unsubscribe",
    )
    contains_all(
        test,
        [
            "testcase_basic_user()",
            "mkdir -p /run/systemd/system/user@.service.d/",
            "run_testcases",
        ],
        "existing OOMD integration-test boundary",
    )

    return {
        "schema_version": 2,
        "systemd_revision": revision,
        "source_blobs": blobs,
        "demonstrated_source_chain": {
            "user_manager_root_from_own_pid_cgroup": True,
            "root_slice_uses_manager_cgroup_root": True,
            "managed_oom_defaults_to_auto": True,
            "unit_load_publishes_managed_oom_update": True,
            "user_manager_sends_all_managed_oom_properties": True,
            "oomd_auto_removes_by_path_without_reporter_identity": True,
        },
        "inference": (
            "a user-manager root-slice AUTO update can remove a PID-1 KILL "
            "registration for the same cgroup path"
        ),
        "runtime_status": (
            "source mechanism verified on current main; runtime execution is "
            "performed separately in the controlled systemd fork"
        ),
        "authority": "internal Linux Fieldwork investigation; no upstream contact",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    root = args.source.resolve()
    try:
        result = verify(root)
    except (
        VerificationError,
        FileNotFoundError,
        OSError,
        subprocess.CalledProcessError,
        UnicodeDecodeError,
    ) as exc:
        print(f"source verification failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
