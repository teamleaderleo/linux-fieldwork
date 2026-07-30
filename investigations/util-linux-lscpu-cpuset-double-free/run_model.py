from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / "ownership_model.c"


def compile_and_run(label: str, *, fixed: bool) -> subprocess.CompletedProcess[str]:
    compiler = shutil.which("cc")
    if compiler is None:
        raise RuntimeError("C compiler unavailable")

    with tempfile.TemporaryDirectory(prefix=f"lscpu-{label}-") as tmp:
        binary = pathlib.Path(tmp) / label
        command = [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(SOURCE),
            "-o",
            str(binary),
        ]
        if fixed:
            command.insert(1, "-DCLEAR_OUTPUT_AFTER_ERROR")
        compiled = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if compiled.returncode != 0:
            raise RuntimeError(compiled.stdout + compiled.stderr)
        return subprocess.run(
            [str(binary)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )


def main() -> int:
    baseline = compile_and_run("baseline", fixed=False)
    candidate = compile_and_run("candidate", fixed=True)

    if baseline.returncode != 42:
        raise RuntimeError(
            f"baseline returned {baseline.returncode}: "
            f"{baseline.stdout}{baseline.stderr}"
        )
    if "duplicate cleanup detected" not in baseline.stderr:
        raise RuntimeError("baseline did not expose retained dangling ownership")
    if candidate.returncode != 0:
        raise RuntimeError(
            f"candidate returned {candidate.returncode}: "
            f"{candidate.stdout}{candidate.stderr}"
        )
    if "cleanup is idempotent" not in candidate.stdout:
        raise RuntimeError("candidate did not preserve NULL-safe outer cleanup")

    print("baseline: duplicate cleanup detected (status 42)")
    print("candidate: output cleared, later cleanup is harmless (status 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
