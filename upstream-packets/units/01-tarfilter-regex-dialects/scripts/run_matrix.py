from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--prerequisite", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    return parser.parse_args()


ARGS = parse_args()
BASELINE = ARGS.baseline.resolve()
PREREQ = ARGS.prerequisite.resolve()
CANDIDATE = ARGS.candidate.resolve()


def archive(member_name: str, *, with_links: bool = False) -> bytes:
    output = io.BytesIO()
    payload = b"payload\n"
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as ar:
        member = tarfile.TarInfo(member_name)
        member.size = len(payload)
        ar.addfile(member, io.BytesIO(payload))
        if with_links:
            hard = tarfile.TarInfo("hard")
            hard.type = tarfile.LNKTYPE
            hard.linkname = member_name
            ar.addfile(hard)
            sym = tarfile.TarInfo("sym")
            sym.type = tarfile.SYMTYPE
            sym.linkname = member_name
            ar.addfile(sym)
    return output.getvalue()


def snapshot(data: bytes) -> dict[str, tuple[str, str]]:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as ar:
        out: dict[str, tuple[str, str]] = {}
        for member in ar:
            kind = "hard" if member.islnk() else "sym" if member.issym() else "file"
            out[member.name] = (kind, member.linkname)
        return out


def run_filter(path: pathlib.Path, member: str, expression: str, *, with_links=False):
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    return subprocess.run(
        [sys.executable, str(path), "--transform", expression],
        input=archive(member, with_links=with_links),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
    )


def run_gnu(work: pathlib.Path, member: str, expression: str, *, with_links=False):
    root = work / "root"
    root.mkdir(parents=True, exist_ok=True)
    target = root / member
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("payload\n")
    names = [member]
    if with_links:
        os.link(target, root / "hard")
        os.symlink(member, root / "sym")
        names.extend(["hard", "sym"])
    archive_path = work / "gnu.tar"
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    completed = subprocess.run(
        [
            "tar",
            "--format=pax",
            "--transform",
            expression,
            "-cf",
            str(archive_path),
            "-C",
            str(root),
            *names,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
    )
    if completed.returncode == 0:
        completed.stdout = archive_path.read_bytes()
    return completed


def require_success(
    path: pathlib.Path,
    member: str,
    expression: str,
    expected: dict[str, tuple[str, str]],
    work: pathlib.Path,
    *,
    with_links=False,
):
    candidate = run_filter(path, member, expression, with_links=with_links)
    if candidate.returncode != 0:
        raise AssertionError(
            f"candidate failed {member=} {expression=}: "
            f"{candidate.stderr.decode(errors='replace')}"
        )
    candidate_snapshot = snapshot(candidate.stdout)
    if candidate_snapshot != expected:
        raise AssertionError(
            f"candidate snapshot {member=} {expression=}: "
            f"{candidate_snapshot!r} != {expected!r}"
        )
    reference = run_gnu(work, member, expression, with_links=with_links)
    if reference.returncode != 0:
        raise AssertionError(
            f"gnu failed {member=} {expression=}: "
            f"{reference.stderr.decode(errors='replace')}"
        )
    reference_snapshot = snapshot(reference.stdout)
    if reference_snapshot != expected:
        raise AssertionError(
            f"gnu snapshot {member=} {expression=}: "
            f"{reference_snapshot!r} != {expected!r}"
        )


def main() -> int:
    results: list[dict[str, object]] = []
    baseline = run_filter(BASELINE, "aaa", "s/a+/b/")
    if baseline.returncode != 0 or snapshot(baseline.stdout) != {"b": ("file", "")}:
        raise AssertionError("baseline mismatch did not reproduce")
    prerequisite = run_filter(PREREQ, "aaa", "s/a+/b/")
    if prerequisite.returncode != 0 or snapshot(prerequisite.stdout) != {
        "b": ("file", "")
    }:
        raise AssertionError("prerequisite mismatch did not reproduce")
    prerequisite_x = run_filter(PREREQ, "aaa", "s/a+/b/x")
    if prerequisite_x.returncode == 0:
        raise AssertionError("prerequisite unexpectedly accepted x")
    results.append({"name": "baseline-negative-controls", "status": "pass"})

    success_cases = [
        ("aaa", "s/a+/b/", "aaa"),
        ("aaa", r"s/a\+/b/", "b"),
        ("aaa", "s/a+/b/x", "b"),
        ("aaa", r"s/a\+/b/x", "aaa"),
        ("aa", "s/a?/b/", "aa"),
        ("aa", r"s/a\?/b/", "ba"),
        ("aa", "s/a?/b/x", "ba"),
        ("aa", r"s/a\?/b/x", "aa"),
        ("ab", "s/a|b/c/", "ab"),
        ("ab", r"s/a\|b/c/", "cb"),
        ("ab", "s/a|b/c/x", "cb"),
        ("ab", r"s/a\|b/c/x", "ab"),
        ("aaa", "s/(aa)/[&]/", "aaa"),
        ("aaa", r"s/\(aa\)/[&]/", "[aa]a"),
        ("aaa", "s/(aa)/[&]/x", "[aa]a"),
        ("aaa", r"s/\(aa\)/[&]/x", "aaa"),
        ("aaa", "s/a{2}/b/", "aaa"),
        ("aaa", r"s/a\{2\}/b/", "ba"),
        ("aaa", "s/a{2}/b/x", "ba"),
        ("aaa", r"s/a\{2\}/b/x", "aaa"),
        ("aa", r"s/\(a\)\1/b/", "b"),
        ("aa", r"s/(a)\1/b/x", "b"),
        ("ab", r"s/\(^a\)/x/", "xb"),
        ("ab", "s/(^a)/x/x", "xb"),
        ("b", r"s/a\|^b/x/", "x"),
        ("b", "s/a|^b/x/x", "x"),
        ("a", r"s/a$\|b/x/", "x"),
        ("a", "s/a$|b/x/x", "x"),
        ("*a", "s/*a/X/", "X"),
        ("*b", r"s/a\|*b/X/", "X"),
        ("0", r"s/\0/X/", "X"),
        ("x0", r"s/\0/X/x", "xX"),
        ("a", "s/a**/X/x", "X"),
        ("0", "s/a+*/X/x", "X0"),
        ("aa", "s/a++/X/x", "X"),
        ("aaaaa", "s/a{2}{2,3}/X/x", "Xa"),
        (")", "s/)/X/x", "X"),
        ("a)b", "s/a)b/X/x", "X"),
        ("(", r"s/\(?/X/x", "X"),
        ("(", r"s/[(?]/X/x", "X"),
        ("(", r"s/\(/X/x", "X"),
    ]
    with tempfile.TemporaryDirectory(prefix="unit01-success-") as td:
        base = pathlib.Path(td)
        for index, (member, expression, expected_name) in enumerate(success_cases):
            print(
                f"success {index + 1}/{len(success_cases)} {expression}",
                flush=True,
            )
            require_success(
                CANDIDATE,
                member,
                expression,
                {expected_name: ("file", "")},
                base / str(index),
            )
    results.append(
        {"name": "success-matrix", "cases": len(success_cases), "status": "pass"}
    )

    with tempfile.TemporaryDirectory(prefix="unit01-links-") as td:
        base = pathlib.Path(td)
        cases = [(r"s/a\+/b/2", "aaa/b"), ("s/a+/b/x2", "aaa/b")]
        for index, (expression, transformed) in enumerate(cases):
            print(f"links {index + 1}/{len(cases)} {expression}", flush=True)
            expected = {
                transformed: ("file", ""),
                "hard": ("hard", transformed),
                "sym": ("sym", transformed),
            }
            require_success(
                CANDIDATE,
                "aaa/aaa",
                expression,
                expected,
                base / str(index),
                with_links=True,
            )
    results.append({"name": "occurrence-link-scope", "cases": 2, "status": "pass"})

    invalid_both = [
        ("ab", "s/a(?=b)/X/x", "unsupported extended-regex group extension"),
        ("a", "s/(?:a)/X/x", "unsupported extended-regex group extension"),
        ("A", "s/(?i)a/X/x", "unsupported extended-regex group extension"),
        ("a", "s/(?P<n>a)/X/x", "unsupported extended-regex group extension"),
        ("aaaa", "s/a{}/X/x", "invalid active regex interval"),
        ("aaaa", "s/a{2/X/x", "invalid active regex interval"),
        ("aaaa", "s/a{x}/X/x", "invalid active regex interval"),
        ("aaaa", r"s/a\{\}/X/", "invalid active regex interval"),
        ("aaaa", r"s/a\{2/X/", "invalid active regex interval"),
        ("aaaa", r"s/a\{x\}/X/", "invalid active regex interval"),
        (
            "aaaaa",
            r"s/a\{2\}\{2,3\}/X/",
            "consecutive basic-regex intervals are invalid",
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="unit01-invalid-") as td:
        base = pathlib.Path(td)
        for index, (member, expression, message) in enumerate(invalid_both):
            print(
                f"invalid {index + 1}/{len(invalid_both)} {expression}",
                flush=True,
            )
            candidate = run_filter(CANDIDATE, member, expression)
            if candidate.returncode == 0 or candidate.stdout:
                raise AssertionError(f"candidate accepted invalid {expression}")
            if message not in candidate.stderr.decode(errors="replace"):
                raise AssertionError(
                    f"missing diagnostic {message!r}: {candidate.stderr!r}"
                )
            reference = run_gnu(base / str(index), member, expression)
            if reference.returncode == 0:
                raise AssertionError(f"gnu accepted expected-invalid {expression}")
    results.append(
        {"name": "shared-rejection", "cases": len(invalid_both), "status": "pass"}
    )

    posix_boundary = [
        ("5", "s/[[:digit:]]/x/"),
        ("a", "s/[[.a.]]/x/"),
        ("a", "s/[[=a=]]/x/"),
    ]
    with tempfile.TemporaryDirectory(prefix="unit01-posix-") as td:
        base = pathlib.Path(td)
        for index, (member, expression) in enumerate(posix_boundary):
            print(
                f"posix {index + 1}/{len(posix_boundary)} {expression}",
                flush=True,
            )
            candidate = run_filter(CANDIDATE, member, expression)
            if candidate.returncode == 0 or candidate.stdout:
                raise AssertionError(
                    f"candidate accepted unsupported POSIX form {expression}"
                )
            reference = run_gnu(base / str(index), member, expression)
            if reference.returncode != 0:
                raise AssertionError(
                    f"gnu rejected boundary form {expression}: {reference.stderr!r}"
                )
    results.append(
        {
            "name": "explicit-posix-boundary",
            "cases": len(posix_boundary),
            "status": "pass",
        }
    )

    print(
        json.dumps(
            {
                "python": sys.version,
                "tar": subprocess.check_output(
                    ["tar", "--version"], text=True
                ).splitlines()[0],
                "results": results,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
