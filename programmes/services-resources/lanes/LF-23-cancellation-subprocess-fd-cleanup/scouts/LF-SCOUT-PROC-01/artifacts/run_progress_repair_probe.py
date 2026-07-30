#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "upstream/mmdebstrap/mmdebstrap").is_file():
            return candidate
    raise RuntimeError("cannot find repository root")


def load_harness(path: Path):
    spec = importlib.util.spec_from_file_location("lf23_cancellation_harness", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load harness from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    script = Path(__file__).resolve()
    repo = args.repo_root.resolve() if args.repo_root else find_repo_root(script)
    artifacts = script.parent
    output = (
        args.output.resolve()
        if args.output
        else artifacts / "ci-run-repair"
    )
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    patch = artifacts / "mmdebstrap-run-progress-record-signal.patch"
    harness_path = artifacts / "cancellation_harness.py"
    source = repo / "upstream/mmdebstrap/mmdebstrap"
    harness = load_harness(harness_path)

    with tempfile.TemporaryDirectory(prefix="lf23-run-progress-repair-") as td:
        candidate_repo = Path(td) / "candidate"
        candidate_source = candidate_repo / "upstream/mmdebstrap/mmdebstrap"
        candidate_source.parent.mkdir(parents=True)
        shutil.copy2(source, candidate_source)
        applied = subprocess.run(
            ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        (output / "patch-stdout.log").write_text(applied.stdout)
        (output / "patch-stderr.log").write_text(applied.stderr)
        if applied.returncode != 0:
            raise RuntimeError(
                f"candidate patch failed to apply: {applied.stdout}{applied.stderr}"
            )

        source_text = candidate_source.read_text()
        instrumented_text = harness.instrument_source(source_text)
        driver = output / "mmdebstrap.run-progress-driver"
        driver.write_text(harness.make_run_progress_driver(instrumented_text))
        driver.chmod(0o755)

        result = harness.run_progress_parent_only(driver, output)
        checks = {
            "signal_logged": result["interruption_logged"],
            "interrupted_failed": result["interrupted_exit"] != 0,
            "did_not_return_success": not result["returned_success"],
            "no_misreported_success": not result["misreported_success"],
            "process_group_empty": result["after_exit"]["process_count"] == 0,
            "rerun_succeeded": result["rerun_exit"] == 0,
            "rerun_process_group_empty": (
                result["rerun_after_exit"]["process_count"] == 0
            ),
        }
        summary = {"checks": checks, "result": result}
        (output / "repair-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
