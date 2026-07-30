#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any


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


def prepare_output(requested: Path, artifacts: Path) -> Path:
    output = requested.resolve()
    allowed_roots = (artifacts.resolve(), Path(tempfile.gettempdir()).resolve())
    if not any(root in output.parents for root in allowed_roots):
        roots = ", ".join(str(root) for root in allowed_roots)
        raise ValueError(f"output must be a child of one of: {roots}; got {output}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def signal_name(signum: int) -> str:
    return signal.Signals(signum).name.removeprefix("SIG")


def run_owner_signals(
    harness: Any,
    driver: Path,
    output_root: Path,
    label: str,
    signums: tuple[int, ...],
) -> dict[str, Any]:
    run_dir = output_root / label
    proc = harness.run_driver(driver, run_dir, "run-progress-parent")
    pgid = proc.pid
    checkpoint = run_dir / "checkpoint.tsv"
    child_pid_file = run_dir / "run-progress-child.pid"
    harness.wait_for(checkpoint, proc, 30)
    harness.wait_for(child_pid_file, proc, 30)
    before = harness.snapshot(run_dir, "before-signal", pgid)

    for signum in signums:
        os.kill(proc.pid, signum)
        time.sleep(0.05)

    after_signal = harness.snapshot(run_dir, "after-signal", pgid)
    (run_dir / "release").touch()
    rc = harness.finish(proc, 30)
    time.sleep(0.15)
    after_exit = harness.snapshot(run_dir, "after-exit", pgid)
    returned = (run_dir / "run-progress-returned").exists()
    stderr_text = (run_dir / "stderr.log").read_text(errors="replace")

    rerun_dir = run_dir / "rerun"
    rerun = harness.run_driver(driver, rerun_dir, None)
    rerun_rc = harness.finish(rerun, 30)
    time.sleep(0.15)
    rerun_after_exit = harness.snapshot(rerun_dir, "after-exit", rerun.pid)

    names = [signal_name(signum) for signum in signums]
    return {
        "label": label,
        "signals": names,
        "signal_scope": "run_progress-owner-pid-only",
        "checkpoint": checkpoint.read_text(errors="replace").strip(),
        "child_pid": int(child_pid_file.read_text().strip()),
        "interrupted_exit": rc,
        "logged_signals": {
            name: f"run_progress() received signal {name}" in stderr_text
            for name in names
        },
        "first_signal_reported": (
            f"run_progress() received signal: {names[0]}" in stderr_text
        ),
        "returned_success": returned,
        "before_signal": before,
        "after_signal": after_signal,
        "after_exit": after_exit,
        "rerun_exit": rerun_rc,
        "rerun_after_exit": rerun_after_exit,
        "stderr": stderr_text,
    }


def repaired_checks(result: dict[str, Any]) -> dict[str, bool]:
    return {
        "all_signals_logged": all(result["logged_signals"].values()),
        "first_signal_retained": result["first_signal_reported"],
        "interrupted_failed": result["interrupted_exit"] != 0,
        "did_not_return_success": not result["returned_success"],
        "process_group_empty": result["after_exit"]["process_count"] == 0,
        "rerun_succeeded": result["rerun_exit"] == 0,
        "rerun_process_group_empty": (
            result["rerun_after_exit"]["process_count"] == 0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    script = Path(__file__).resolve()
    repo = args.repo_root.resolve() if args.repo_root else find_repo_root(script)
    artifacts = script.parent
    requested_output = args.output if args.output else artifacts / "ci-run-repair"
    output = prepare_output(requested_output, artifacts)

    patch = artifacts / "mmdebstrap-run-progress-record-signal.patch"
    harness_path = artifacts / "cancellation_harness.py"
    source = repo / "upstream/mmdebstrap/mmdebstrap"
    harness = load_harness(harness_path)
    source_text = source.read_text()

    original_driver = output / "mmdebstrap.run-progress-original-driver"
    original_driver.write_text(
        harness.make_run_progress_driver(harness.instrument_source(source_text))
    )
    original_driver.chmod(0o755)
    negative_control = run_owner_signals(
        harness,
        original_driver,
        output,
        "negative-control-term",
        (signal.SIGTERM,),
    )
    negative_checks = {
        "signal_logged": all(negative_control["logged_signals"].values()),
        "misreported_success_reproduced": (
            negative_control["interrupted_exit"] == 0
            and negative_control["returned_success"]
            and not negative_control["first_signal_reported"]
        ),
        "process_group_empty": (
            negative_control["after_exit"]["process_count"] == 0
        ),
        "rerun_succeeded": negative_control["rerun_exit"] == 0,
        "rerun_process_group_empty": (
            negative_control["rerun_after_exit"]["process_count"] == 0
        ),
    }

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

        candidate_text = candidate_source.read_text()
        driver = output / "mmdebstrap.run-progress-repaired-driver"
        driver.write_text(
            harness.make_run_progress_driver(
                harness.instrument_source(candidate_text)
            )
        )
        driver.chmod(0o755)

        cases = (
            ("owner-int", (signal.SIGINT,)),
            ("owner-hup", (signal.SIGHUP,)),
            ("owner-pipe", (signal.SIGPIPE,)),
            ("owner-term", (signal.SIGTERM,)),
            ("owner-term-then-hup", (signal.SIGTERM, signal.SIGHUP)),
        )
        matrix = []
        all_repair_checks = True
        for label, signums in cases:
            result = run_owner_signals(harness, driver, output, label, signums)
            checks = repaired_checks(result)
            matrix.append({"checks": checks, "result": result})
            all_repair_checks = all_repair_checks and all(checks.values())

    summary = {
        "negative_control": {
            "checks": negative_checks,
            "result": negative_control,
        },
        "repair_matrix": matrix,
    }
    (output / "repair-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(negative_checks.values()) and all_repair_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
