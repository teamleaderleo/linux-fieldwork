#!/usr/bin/env python3
"""Prepare exact composed and mutation copies for chrootless authority probes."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import stat
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCHES = (
    ROOT
    / "investigations/mmdebstrap-chrootless-env/"
    / "0001-use-configured-dpkg-path.patch",
    ROOT
    / "investigations/mmdebstrap-chrootless-env/"
    / "0002-use-absolute-env-wrapper.patch",
    ROOT
    / "investigations/mmdebstrap-chrootless-env/"
    / "0003-use-absolute-env-for-chrootless-hooks.patch",
)


class PreparationError(RuntimeError):
    pass


def replace_exact(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise PreparationError(
            f"{label} marker count mismatch: expected 1, observed {count}"
        )
    return source.replace(old, new)


def apply_patch(tree: pathlib.Path, patch: pathlib.Path) -> None:
    completed = subprocess.run(
        [
            "patch",
            "--batch",
            "--forward",
            "--fuzz=0",
            "-p1",
            "-i",
            str(patch),
        ],
        cwd=tree,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise PreparationError(f"cannot apply {patch.name}:\n{output}")
    if "fuzz" in output.lower():
        raise PreparationError(f"fuzzy application reported for {patch.name}:\n{output}")


def check_perl(path: pathlib.Path) -> None:
    completed = subprocess.run(
        ["perl", "-c", str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if completed.returncode != 0:
        raise PreparationError(
            f"Perl syntax failed for {path}:\n{completed.stdout}{completed.stderr}"
        )


def prepare(destination: pathlib.Path) -> dict[str, str]:
    if destination.exists():
        shutil.rmtree(destination)
    tree = destination / "candidate-tree"
    candidate = tree / "upstream/mmdebstrap/mmdebstrap"
    candidate.parent.mkdir(parents=True)
    shutil.copy2(SOURCE, candidate)

    for patch in PATCHES:
        apply_patch(tree, patch)

    mode = stat.S_IMODE(candidate.stat().st_mode)
    candidate.chmod(mode | stat.S_IXUSR)
    check_perl(candidate)
    candidate_source = candidate.read_text(encoding="utf-8")

    inner_mutation = destination / "mmdebstrap-inner-path-mutation"
    inner_source = replace_exact(
        candidate_source,
        '    my @result = (\'-i\', "PATH=$dpkgpath", "TMPDIR=$tmpdir");\n',
        '    my @result = (\'-i\', "PATH=$ENV{PATH}", "TMPDIR=$tmpdir");\n',
        "inner PATH mutation",
    )
    inner_mutation.write_text(inner_source, encoding="utf-8")
    inner_mutation.chmod(mode | stat.S_IXUSR)
    check_perl(inner_mutation)

    outer_mutation = destination / "mmdebstrap-outer-env-mutation"
    outer_source = replace_exact(
        candidate_source,
        "                    chrootless_env_path(),\n"
        "                    chrootless_dpkg_environment(\n",
        "                    'env',\n"
        "                    chrootless_dpkg_environment(\n",
        "direct outer wrapper mutation",
    )
    outer_source = replace_exact(
        outer_source,
        "                '-oDir::Bin::dpkg=' . chrootless_env_path(),\n",
        "                '-oDir::Bin::dpkg=env',\n",
        "apt-managed outer wrapper mutation",
    )
    outer_mutation.write_text(outer_source, encoding="utf-8")
    outer_mutation.chmod(mode | stat.S_IXUSR)
    check_perl(outer_mutation)

    hook_mutation = destination / "mmdebstrap-hook-env-mutation"
    hook_source = replace_exact(
        candidate_source,
        "    my $env_path = $options->{mode} eq 'chrootless'\n"
        "      ? chrootless_env_path()\n"
        "      : 'env';\n",
        "    my $env_path = 'env';\n",
        "chrootless hook wrapper mutation",
    )
    hook_mutation.write_text(hook_source, encoding="utf-8")
    hook_mutation.chmod(mode | stat.S_IXUSR)
    check_perl(hook_mutation)

    return {
        "schema_version": 2,
        "source": str(SOURCE),
        "candidate": str(candidate),
        "inner_mutation": str(inner_mutation),
        "outer_mutation": str(outer_mutation),
        "hook_mutation": str(hook_mutation),
        "source_mode": format(stat.S_IMODE(SOURCE.stat().st_mode), "04o"),
        "candidate_mode": format(stat.S_IMODE(candidate.stat().st_mode), "04o"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = prepare(args.destination.resolve())
    except (OSError, PreparationError, subprocess.SubprocessError) as error:
        print(f"candidate preparation failed: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for key in (
            "candidate",
            "inner_mutation",
            "outer_mutation",
            "hook_mutation",
        ):
            print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
