#!/usr/bin/env python3
"""Build the versioned lf-lifecycle packages used by the LF-02 probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import subprocess
from pathlib import Path


PACKAGES = (
    {
        "key": "v1",
        "version": "1.0",
        "config": "default=one\n",
        "postinst_failure": False,
    },
    {
        "key": "v2",
        "version": "2.0",
        "config": "default=two\n",
        "postinst_failure": False,
    },
    {
        "key": "v3-fail",
        "version": "3.0",
        "config": "default=three\n",
        "postinst_failure": True,
    },
    {
        "key": "v3-recover",
        "version": "3.1",
        "config": "default=three-recovered\n",
        "postinst_failure": False,
    },
)


def script_text(phase: str, version: str, fail: bool = False) -> str:
    failure = "\nexit 42" if fail else ""
    return f"""#!/bin/sh
set -eu
root=${{DPKG_ROOT:-}}
if [ -z "$root" ]; then
    echo 'DPKG_ROOT was empty' >&2
    exit 97
fi
mkdir -p "$root/var/lib/lf-lifecycle"
args_hex=-
if [ "$#" -gt 0 ]; then
    args_hex=$(printf '%s\\000' "$@" | od -An -tx1 | tr -d ' \\n')
fi
printf 'phase=%s script_version=%s args_hex=%s dpkg_root=%s cwd=%s uid=%s gid=%s\\n' \\
    '{phase}' '{version}' "$args_hex" "$root" "$(pwd)" "$(id -u)" "$(id -g)" \\
    >> "$root/var/lib/lf-lifecycle/script.log"{failure}
"""


def write_text(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def build_one(output: Path, spec: dict[str, object]) -> dict[str, object]:
    key = str(spec["key"])
    version = str(spec["version"])
    work = output / "work" / key
    if work.exists():
        shutil.rmtree(work)

    control = f"""Package: lf-lifecycle
Version: {version}
Section: misc
Priority: optional
Architecture: all
Maintainer: Linux Fieldwork <noreply@example.invalid>
Description: LF-02 chrootless lifecycle fixture {key}
"""
    write_text(work / "DEBIAN/control", control)
    write_text(work / "DEBIAN/conffiles", "/etc/lf-lifecycle.conf\n")
    write_text(work / "DEBIAN/preinst", script_text("preinst", version), 0o755)
    write_text(
        work / "DEBIAN/postinst",
        script_text("postinst", version, bool(spec["postinst_failure"])),
        0o755,
    )
    write_text(work / "DEBIAN/prerm", script_text("prerm", version), 0o755)
    write_text(work / "DEBIAN/postrm", script_text("postrm", version), 0o755)
    write_text(work / "etc/lf-lifecycle.conf", str(spec["config"]))
    write_text(work / "usr/lib/lf-lifecycle/version", version + "\n")

    archive = output / f"lf-lifecycle_{version}_all.deb"
    subprocess.run(
        ["dpkg-deb", "--build", "--root-owner-group", str(work), str(archive)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    return {
        "key": key,
        "package": "lf-lifecycle",
        "version": version,
        "architecture": "all",
        "archive": archive.name,
        "size_bytes": archive.stat().st_size,
        "sha256": digest,
        "conffile_default": str(spec["config"]).rstrip("\n"),
        "postinst_failure": bool(spec["postinst_failure"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    manifest = {
        "schema_version": 1,
        "packages": [build_one(output, spec) for spec in PACKAGES],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # The work trees are useful source receipts, but executable modes must stay explicit.
    for script in (output / "work").glob("*/DEBIAN/*inst"):
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for script in (output / "work").glob("*/DEBIAN/*rm"):
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())