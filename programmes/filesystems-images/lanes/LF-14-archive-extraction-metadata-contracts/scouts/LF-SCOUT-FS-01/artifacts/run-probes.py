#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

EPOCH = 946684800
SPARSE_END = 8 * 1024 * 1024
SPARSE_SIZE = SPARSE_END + len(b"END")
CASES = [
    "traversal",
    "absolute",
    "symlink",
    "hardlink",
    "sparse",
    "numeric-owner",
    "mode-bits",
    "timestamps",
    "xattr",
]


def find_repo_root(start: pathlib.Path) -> pathlib.Path:
    for candidate in [start, *start.parents]:
        if (candidate / "upstream/mmdebstrap/tarfilter").is_file():
            return candidate
    raise RuntimeError("cannot find repository root")


def prepare_output(requested: pathlib.Path, artifacts: pathlib.Path) -> pathlib.Path:
    output = requested.resolve()
    roots = {
        artifacts.resolve(),
        pathlib.Path(tempfile.gettempdir()).resolve(),
        pathlib.Path("/tmp").resolve(),
        pathlib.Path("/var/tmp").resolve(),
    }
    if not any(root in output.parents for root in roots):
        allowed = ", ".join(str(root) for root in sorted(roots, key=str))
        raise ValueError(
            f"output must be a strict child of an artifacts or temporary root "
            f"({allowed}); got {output}"
        )
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def member_manifest(path: pathlib.Path) -> list[dict[str, Any]]:
    rows = []
    try:
        with tarfile.open(path, "r:*") as archive:
            for member in archive:
                rows.append(
                    {
                        "name": member.name,
                        "type": (
                            member.type.decode("ascii", "replace")
                            if isinstance(member.type, bytes)
                            else str(member.type)
                        ),
                        "size": member.size,
                        "uid": member.uid,
                        "gid": member.gid,
                        "mode": oct(member.mode),
                        "mtime": member.mtime,
                        "linkname": member.linkname,
                        "pax_headers": dict(sorted(member.pax_headers.items())),
                        "sparse": member.sparse,
                    }
                )
    except Exception as exc:
        listed = subprocess.run(
            ["tar", "-tvf", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        rows.append(
            {
                "manifest_error": f"{type(exc).__name__}: {exc}",
                "gnu_tar_list_status": listed.returncode,
                "gnu_tar_list_stdout": listed.stdout.decode("utf-8", "replace"),
                "gnu_tar_list_stderr": listed.stderr.decode("utf-8", "replace"),
                "sparse": None,
            }
        )
    return rows


def file_info(path: pathlib.Path) -> dict[str, Any]:
    status = path.lstat()
    info = {
        "exists": True,
        "mode": oct(stat.S_IMODE(status.st_mode)),
        "uid": status.st_uid,
        "gid": status.st_gid,
        "mtime": int(status.st_mtime),
        "size": status.st_size,
        "blocks_512": status.st_blocks,
        "allocated_bytes": status.st_blocks * 512,
        "inode": status.st_ino,
        "nlink": status.st_nlink,
        "kind": (
            "symlink"
            if path.is_symlink()
            else "directory"
            if path.is_dir()
            else "file"
        ),
    }
    if path.is_symlink():
        info["link_target"] = os.readlink(path)
    try:
        info["user.lf14"] = os.getxattr(path, b"user.lf14").decode(
            "utf-8", "replace"
        )
    except OSError:
        info["user.lf14"] = None
    return info


def safe_info(path: pathlib.Path) -> dict[str, Any]:
    try:
        return file_info(path)
    except FileNotFoundError:
        return {"exists": False}


def expected_sparse_sha256() -> str:
    digest = hashlib.sha256()
    digest.update(b"BEGIN")
    digest.update(b"\0" * (1024 * 1024 - len(b"BEGIN")))
    digest.update(b"MIDDLE")
    digest.update(b"\0" * (SPARSE_END - 1024 * 1024 - len(b"MIDDLE")))
    digest.update(b"END")
    return digest.hexdigest()


def sparse_content(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "content_ok": False}

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        samples: dict[str, str] = {}
        sample_ok = True
        for offset, expected in (
            (0, b"BEGIN"),
            (1024 * 1024, b"MIDDLE"),
            (SPARSE_END, b"END"),
        ):
            stream.seek(offset)
            actual = stream.read(len(expected))
            samples[str(offset)] = actual.hex()
            sample_ok = sample_ok and actual == expected
        holes: dict[str, str] = {}
        holes_ok = True
        for offset in (4096, 2 * 1024 * 1024):
            stream.seek(offset)
            actual = stream.read(32)
            holes[str(offset)] = actual.hex()
            holes_ok = holes_ok and actual == b"\0" * 32

    actual_hash = digest.hexdigest()
    expected_hash = expected_sparse_sha256()
    return {
        "exists": True,
        "sha256": actual_hash,
        "expected_sha256": expected_hash,
        "samples": samples,
        "holes": holes,
        "content_ok": (
            path.stat().st_size == SPARSE_SIZE
            and actual_hash == expected_hash
            and sample_ok
            and holes_ok
        ),
    }


def evaluate(
    case: str,
    target: pathlib.Path,
    base: pathlib.Path,
    status: int,
    archive_manifest: list[dict[str, Any]],
    direct_sparse_alloc: int | None,
) -> tuple[bool, dict[str, Any], str]:
    details: dict[str, Any] = {"status": status}
    if case == "traversal":
        outside = base / "lf14-traversal-escape"
        inside = target / "lf14-traversal-escape"
        details.update(outside=safe_info(outside), inside=safe_info(inside))
        return (
            not outside.exists() and not inside.exists() and status != 0,
            details,
            "reject ../ member and create no file outside target",
        )
    if case == "absolute":
        rooted = pathlib.Path("/lf14-absolute-escape")
        inside = target / "lf14-absolute-escape"
        details.update(rooted=safe_info(rooted), inside=safe_info(inside))
        return (
            not rooted.exists() and inside.is_file() and status == 0,
            details,
            "strip leading slash and extract beneath target",
        )
    if case == "symlink":
        outside_payload = base / "lf14-symlink-outside/payload"
        pivot = target / "pivot"
        details.update(outside_payload=safe_info(outside_payload), pivot=safe_info(pivot))
        return (
            not outside_payload.exists() and status != 0,
            details,
            "do not follow archive-created symlink outside target",
        )
    if case == "hardlink":
        base_file, peer = target / "hard/base", target / "hard/peer"
        details.update(base=safe_info(base_file), peer=safe_info(peer))
        ok = (
            base_file.is_file()
            and peer.is_file()
            and base_file.stat().st_ino == peer.stat().st_ino
            and base_file.stat().st_nlink >= 2
            and status == 0
        )
        return ok, details, "preserve hard-link inode relationship"
    if case == "sparse":
        path = target / ".sparse-source"
        content = sparse_content(path)
        details.update(
            file=safe_info(path),
            content=content,
            archive_sparse=archive_manifest[0].get("sparse"),
        )
        logical = path.stat().st_size if path.exists() else 0
        allocated = path.stat().st_blocks * 512 if path.exists() else logical
        allocation_ok = (
            allocated < logical // 4
            if direct_sparse_alloc is None
            else allocated <= max(direct_sparse_alloc * 4, logical // 4)
        )
        ok = (
            path.is_file()
            and logical == SPARSE_SIZE
            and content["content_ok"]
            and allocation_ok
            and status == 0
        )
        return ok, details, "preserve exact logical bytes and sparse allocation"
    if case == "numeric-owner":
        path = target / "owner/file"
        header = archive_manifest[0]
        expected_uid = header["uid"] if os.geteuid() == 0 else os.geteuid()
        expected_gid = header["gid"] if os.geteuid() == 0 else os.getegid()
        details.update(
            file=safe_info(path),
            header_uid=header["uid"],
            header_gid=header["gid"],
            expected_extracted_uid=expected_uid,
            expected_extracted_gid=expected_gid,
        )
        ok = (
            path.is_file()
            and header["uid"] == 12345
            and header["gid"] == 23456
            and path.stat().st_uid == expected_uid
            and path.stat().st_gid == expected_gid
            and status == 0
        )
        return (
            ok,
            details,
            "preserve numeric archive ownership and apply caller-privilege extraction rules",
        )
    if case == "mode-bits":
        path = target / "mode/file"
        details.update(file=safe_info(path))
        return (
            path.is_file()
            and stat.S_IMODE(path.stat().st_mode) == 0o751
            and status == 0,
            details,
            "preserve mode 0751",
        )
    if case == "timestamps":
        path = target / "time/file"
        details.update(file=safe_info(path))
        return (
            path.is_file() and int(path.stat().st_mtime) == EPOCH and status == 0,
            details,
            "preserve mtime 2000-01-01T00:00:00Z",
        )
    if case == "xattr":
        path = target / "xattr/file"
        details.update(file=safe_info(path))
        try:
            value = os.getxattr(path, b"user.lf14")
        except OSError:
            value = None
        return (
            path.is_file() and value == b"corpus" and status == 0,
            details,
            "preserve ordinary user.lf14 xattr",
        )
    raise AssertionError(case)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and exercise the LF-14 archive corpus"
    )
    parser.add_argument("--repo-root", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    script = pathlib.Path(__file__).resolve()
    repo = args.repo_root.resolve() if args.repo_root else find_repo_root(script)
    output = prepare_output(args.output, script.parent)
    fixtures, filtered, extracts, logs = (
        output / name for name in ("fixtures", "filtered", "extracts", "logs")
    )
    for directory in (fixtures, filtered, extracts, logs):
        directory.mkdir(parents=True, exist_ok=True)

    generator = script.with_name("generate-fixtures.py")
    subprocess.run([sys.executable, str(generator), str(fixtures)], check=True)
    tarfilter = repo / "upstream/mmdebstrap/tarfilter"
    environment = {
        "platform": platform.platform(),
        "python": sys.version,
        "euid": os.geteuid(),
        "egid": os.getegid(),
        "tar": subprocess.check_output(["tar", "--version"], text=True).splitlines()[0],
        "tarfilter": str(tarfilter.relative_to(repo)),
    }
    (output / "environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n"
    )

    manifests: dict[str, Any] = {}
    commands = [f"{sys.executable} {generator.relative_to(repo)} {fixtures}"]
    for case in CASES:
        source = fixtures / f"{case}.tar"
        destination = filtered / f"{case}.tar"
        commands.append(
            "python3 upstream/mmdebstrap/tarfilter "
            f"--path-exclude=/__lf14_never_match__ < {source} > {destination}"
        )
        with source.open("rb") as input_stream, destination.open("wb") as output_stream:
            filtered_run = subprocess.run(
                [
                    sys.executable,
                    str(tarfilter),
                    "--path-exclude=/__lf14_never_match__",
                ],
                stdin=input_stream,
                stdout=output_stream,
                stderr=subprocess.PIPE,
            )
        if filtered_run.returncode:
            raise RuntimeError(
                f"tarfilter failed for {case}: {filtered_run.stderr.decode()}"
            )
        manifests[case] = {
            "original": member_manifest(source),
            "filtered": member_manifest(destination),
        }
    (output / "archive-manifests.json").write_text(
        json.dumps(manifests, indent=2, sort_keys=True) + "\n"
    )

    results: list[dict[str, Any]] = []
    sparse_direct_alloc: int | None = None
    for path_name, archive_dir in (
        ("gnu-tar-direct", fixtures),
        ("mmdebstrap-tarfilter", filtered),
    ):
        for case in CASES:
            base = extracts / path_name / case
            target = base / "target"
            (base / "lf14-symlink-outside").mkdir(parents=True, exist_ok=True)
            target.mkdir(parents=True, exist_ok=True)
            archive = archive_dir / f"{case}.tar"
            command = [
                "tar",
                "--xattrs",
                "--xattrs-include=user.*",
                "-xf",
                str(archive),
                "-C",
                str(target),
            ]
            commands.append(" ".join(command))
            extracted = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (logs / f"{path_name}-{case}.stdout").write_bytes(extracted.stdout)
            (logs / f"{path_name}-{case}.stderr").write_bytes(extracted.stderr)
            direct_reference = (
                sparse_direct_alloc
                if path_name == "mmdebstrap-tarfilter" and case == "sparse"
                else None
            )
            ok, details, expected = evaluate(
                case,
                target,
                base,
                extracted.returncode,
                manifests[case][
                    "filtered" if path_name == "mmdebstrap-tarfilter" else "original"
                ],
                direct_reference,
            )
            if (
                path_name == "gnu-tar-direct"
                and case == "sparse"
                and (target / ".sparse-source").exists()
            ):
                sparse_direct_alloc = (
                    target / ".sparse-source"
                ).stat().st_blocks * 512
            results.append(
                {
                    "path": path_name,
                    "case": case,
                    "pass": ok,
                    "expected": expected,
                    "details": details,
                    "stderr": extracted.stderr.decode("utf-8", "replace"),
                }
            )

    (output / "extraction-results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n"
    )
    (output / "commands.txt").write_text("\n".join(commands) + "\n")

    lines = [
        "# Extraction matrix",
        "",
        "| Path | Fixture | Expected behavior | Result | Key observation |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        details = result["details"]
        observation = "exit=" + str(details["status"])
        if result["case"] == "sparse" and details.get("file", {}).get("exists"):
            observation += (
                f", logical={details['file']['size']}, "
                f"allocated={details['file']['allocated_bytes']}, "
                f"content_ok={details['content']['content_ok']}"
            )
        elif result["case"] == "hardlink" and details.get("base", {}).get("exists"):
            observation += (
                f", inode_equal={details['base']['inode'] == details['peer']['inode']}"
            )
        elif result["case"] == "numeric-owner":
            observation += (
                f", header={details['header_uid']}:{details['header_gid']}, "
                f"extracted={details['file'].get('uid')}:{details['file'].get('gid')}, "
                f"expected={details['expected_extracted_uid']}:"
                f"{details['expected_extracted_gid']}"
            )
        elif result["case"] in ("mode-bits", "timestamps", "xattr"):
            file_details = details.get("file", {})
            observation += (
                f", mode={file_details.get('mode')}, "
                f"mtime={file_details.get('mtime')}, "
                f"xattr={file_details.get('user.lf14')}"
            )
        elif result["case"] == "absolute":
            observation += (
                f", inside={details['inside']['exists']}, "
                f"rooted={details['rooted']['exists']}"
            )
        elif result["case"] == "traversal":
            observation += f", outside={details['outside']['exists']}"
        elif result["case"] == "symlink":
            observation += (
                f", outside_payload={details['outside_payload']['exists']}"
            )
        lines.append(
            f"| {result['path']} | {result['case']} | {result['expected']} | "
            f"{'PASS' if result['pass'] else 'FAIL'} | {observation} |"
        )
    (output / "extraction-matrix.md").write_text("\n".join(lines) + "\n")

    comparisons = ["# Metadata comparison", ""]
    for case in CASES:
        original = manifests[case]["original"]
        rewritten = manifests[case]["filtered"]
        comparisons.extend(
            [
                f"## {case}",
                "",
                f"Archive member count: original `{len(original)}`, "
                f"filtered `{len(rewritten)}`.",
            ]
        )
        if case == "sparse":
            comparisons.append(f"Original sparse map: `{original[0].get('sparse')}`")
            comparisons.append(f"Filtered sparse map: `{rewritten[0].get('sparse')}`")
            if rewritten[0].get("manifest_error"):
                comparisons.append(
                    f"Filtered manifest error: `{rewritten[0]['manifest_error']}`"
                )
                comparisons.append(
                    f"GNU tar list status: `{rewritten[0]['gnu_tar_list_status']}`"
                )
        elif case == "xattr":
            comparisons.append(
                f"Original pax headers: `{original[0].get('pax_headers')}`"
            )
            comparisons.append(
                f"Filtered pax headers: `{rewritten[0].get('pax_headers')}`"
            )
        else:
            fields = (
                "name",
                "type",
                "size",
                "uid",
                "gid",
                "mode",
                "mtime",
                "linkname",
            )
            same = all(
                all(field in row for field in fields)
                for row in original + rewritten
            ) and [
                {field: row[field] for field in fields} for row in original
            ] == [
                {field: row[field] for field in fields} for row in rewritten
            ]
            comparisons.append(f"Core member fields equal: `{same}`")
        comparisons.append("")
    (output / "metadata-comparison.md").write_text("\n".join(comparisons))

    failures = [result for result in results if not result["pass"]]
    print(
        json.dumps(
            {
                "failures": [
                    {"path": result["path"], "case": result["case"]}
                    for result in failures
                ]
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
