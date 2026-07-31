#!/usr/bin/env python3
"""Apply the retained product patch and emit an executable helper harness."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCH = (
    ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime"
    / "0001-normalize-root-chrootless-directory-mtimes.patch"
)


class PreparationError(RuntimeError):
    pass


def extract_function(source: str, name: str, next_name: str) -> str:
    marker = f"sub {name}"
    next_marker = f"sub {next_name}"
    if source.count(marker) != 1 or source.count(next_marker) != 1:
        raise PreparationError(
            f"cannot identify exact function boundary: {name} -> {next_name}"
        )
    start = source.index(marker)
    end = source.index(next_marker, start)
    return source[start:end]


def prepare(output: pathlib.Path) -> None:
    with tempfile.TemporaryDirectory(prefix="mtime-product-helper-") as temporary:
        work = pathlib.Path(temporary)
        candidate = work / "upstream/mmdebstrap/mmdebstrap"
        candidate.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, candidate)
        completed = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(PATCH),
            ],
            cwd=work,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        patch_output = completed.stdout + completed.stderr
        if completed.returncode != 0:
            raise PreparationError(f"candidate patch failed:\n{patch_output}")
        lowered = patch_output.lower()
        if "fuzz" in lowered or "offset" in lowered:
            raise PreparationError(f"candidate patch was not exact:\n{patch_output}")

        syntax = subprocess.run(
            ["perl", "-c", str(candidate)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if syntax.returncode != 0:
            raise PreparationError(
                "candidate Perl syntax failed:\n"
                + syntax.stdout
                + syntax.stderr
            )

        helper = extract_function(
            candidate.read_text(encoding="utf-8"),
            "normalize_archive_directory_mtimes",
            "main",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "#!/usr/bin/perl\n"
        "use strict;\n"
        "use warnings;\n"
        "use File::Find;\n"
        "sub error { die $_[0] . \"\\n\"; }\n"
        + helper
        + "normalize_archive_directory_mtimes($ARGV[0], $ARGV[1]);\n",
        encoding="utf-8",
    )
    output.chmod(0o755)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=pathlib.Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        prepare(args.output.resolve())
    except (OSError, PreparationError, subprocess.SubprocessError) as error:
        print(f"product normalizer preparation failed: {error}", file=sys.stderr)
        return 2
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
