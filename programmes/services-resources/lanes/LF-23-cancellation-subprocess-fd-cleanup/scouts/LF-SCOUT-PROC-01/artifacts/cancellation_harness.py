#!/usr/bin/env python3
"""Deterministic cancellation probe for the imported mmdebstrap source.

The harness makes a temporary instrumented copy of the exact imported source.
Instrumentation adds passive checkpoints only; the source under upstream/ is
left untouched. Each required run gets a fresh process group and TMPDIR. A
fourth targeted run exercises the run_progress() parent-only signal path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from typing import Any

STAGES = ("before-child-launch", "active-worker", "cleanup")
SIGNAL = signal.SIGTERM

CHECKPOINT_HELPER = r'''
sub lf_checkpoint {
    my ($name, $root) = @_;
    return if !defined $ENV{LF_CHECKPOINT};
    return if $ENV{LF_CHECKPOINT} ne $name;
    my $dir = $ENV{LF_RUN_DIR};
    if (!defined $dir || $dir eq '') {
        die "LF_RUN_DIR is required for checkpoint instrumentation\n";
    }
    opendir(my $fdh, "/proc/$$/fd") or die "opendir /proc/$$/fd: $!\n";
    my @fds = sort { $a <=> $b } grep { /^\d+$/ } readdir($fdh);
    closedir($fdh);
    my @fdrows = ();
    foreach my $fd (@fds) {
        my $target = readlink("/proc/$$/fd/$fd");
        $target = '<unreadable>' if !defined $target;
        push @fdrows, "$fd=$target";
    }
    open(my $fh, '>', "$dir/checkpoint.tsv")
      or die "open checkpoint.tsv: $!\n";
    print $fh join("\t", $name, $$, getppid(), getpgrp(), ($root // ''),
        join('|', @fdrows)), "\n";
    close($fh) or die "close checkpoint.tsv: $!\n";
    my $release = "$dir/release";
    while (!-e $release) {
        select undef, undef, undef, 0.02;
    }
    return;
}

'''

RUN_PROGRESS_DRIVER = r'''if (defined $ENV{LF_RUN_PROGRESS_DRIVER}) {
    my $get_exec = sub {
        return (
            'sh', '-c',
            'printf "%s\n" "$$" > "$LF_RUN_DIR/run-progress-child.pid"; sleep 2; printf "child-complete\n"'
        );
    };
    my $line_handler = sub { return 0, undef; };
    my $line_has_error = sub { return 0; };
    run_progress($get_exec, $line_handler, $line_has_error, undef);
    open(my $fh, '>', "$ENV{LF_RUN_DIR}/run-progress-returned")
      or die "open run-progress-returned: $!\n";
    print $fh "success\n";
    close($fh) or die "close run-progress-returned: $!\n";
    exit 0;
}
main();

__END__'''


def instrument_source(source: str) -> str:
    """Insert exact checkpoints and fail if the imported source drifts."""
    source = source.replace("sub main() {", CHECKPOINT_HELPER + "sub main() {", 1)

    before = """    my $pid;\n    if ($options->{mode} eq 'unshare') {\n"""
    after = """    lf_checkpoint('before-child-launch', $options->{root});\n\n    my $pid;\n    if ($options->{mode} eq 'unshare') {\n"""
    if source.count(before) != 1:
        raise RuntimeError("before-child-launch insertion marker drifted")
    source = source.replace(before, after, 1)

    active_before = """        @cleanup_tasks = setup_mounts($options);\n    }\n\n    eval {\n"""
    active_after = """        @cleanup_tasks = setup_mounts($options);\n        lf_checkpoint('active-worker', $options->{root});\n    }\n\n    eval {\n"""
    if source.count(active_before) != 1:
        raise RuntimeError("active-worker insertion marker drifted")
    source = source.replace(active_before, active_after, 1)

    cleanup_before = """    $waiting_for = \"cleanup\";\n\n    if (any { $_ eq $options->{format} } ('directory')) {\n"""
    cleanup_after = """    $waiting_for = \"cleanup\";\n\n    lf_checkpoint('cleanup', $options->{root});\n\n    if (any { $_ eq $options->{format} } ('directory')) {\n"""
    if source.count(cleanup_before) != 1:
        raise RuntimeError("cleanup insertion marker drifted")
    source = source.replace(cleanup_before, cleanup_after, 1)

    progress_before = """    my $output    = '';\n    my $has_error = 0;\n"""
    progress_after = """    lf_checkpoint('run-progress-parent', undef);\n\n    my $output    = '';\n    my $has_error = 0;\n"""
    if source.count(progress_before) != 1:
        raise RuntimeError("run-progress-parent insertion marker drifted")
    source = source.replace(progress_before, progress_after, 1)
    return source


def make_run_progress_driver(source: str) -> str:
    marker = "main();\n\n__END__"
    if source.count(marker) != 1:
        raise RuntimeError("main driver marker drifted")
    return source.replace(marker, RUN_PROGRESS_DRIVER, 1)


def prepare_process(
    cmd: list[str], run_dir: Path, env_extra: dict[str, str]
) -> subprocess.Popen[bytes]:
    run_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"LC_ALL": "C.UTF-8", "LF_RUN_DIR": str(run_dir)})
    env.update(env_extra)
    (run_dir / "command.json").write_text(json.dumps(cmd, indent=2) + "\n")
    stdout = (run_dir / "stdout.log").open("wb")
    stderr = (run_dir / "stderr.log").open("wb")
    return subprocess.Popen(
        cmd,
        stdout=stdout,
        stderr=stderr,
        env=env,
        start_new_session=True,
    )


def run_command(source: Path, run_dir: Path, checkpoint: str | None) -> subprocess.Popen[bytes]:
    tmpdir = run_dir / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    env_extra = {"TMPDIR": str(tmpdir)}
    if checkpoint is not None:
        env_extra["LF_CHECKPOINT"] = checkpoint
    cmd = [
        "perl",
        str(source),
        "--mode=root",
        "--variant=custom",
        "--format=null",
        "--dry-run",
        "--customize-hook=true",
        "--skip=check/signed-by,update",
        "",
        "/dev/null",
    ]
    return prepare_process(cmd, run_dir, env_extra)


def run_driver(source: Path, run_dir: Path, checkpoint: str | None) -> subprocess.Popen[bytes]:
    env_extra = {"LF_RUN_PROGRESS_DRIVER": "1"}
    if checkpoint is not None:
        env_extra["LF_CHECKPOINT"] = checkpoint
    return prepare_process(["perl", str(source)], run_dir, env_extra)


def wait_for(path: Path, proc: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        rc = proc.poll()
        if rc is not None:
            raise RuntimeError(f"process exited {rc} before {path.name}")
        time.sleep(0.02)
    raise TimeoutError(f"timed out waiting for {path}")


def group_pids(pgid: int) -> list[int]:
    pids: list[int] = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            if os.getpgid(int(item.name)) == pgid:
                pids.append(int(item.name))
        except (ProcessLookupError, PermissionError):
            continue
    return sorted(pids)


def snapshot(run_dir: Path, label: str, pgid: int) -> dict[str, Any]:
    out_dir = run_dir / label
    out_dir.mkdir(parents=True, exist_ok=True)
    pids = group_pids(pgid)
    rows: list[dict[str, Any]] = []
    for pid in pids:
        proc = Path("/proc") / str(pid)
        row: dict[str, Any] = {"pid": pid}
        try:
            row["cmdline"] = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            row["status"] = (proc / "status").read_text(errors="replace")
            row["mountinfo"] = (proc / "mountinfo").read_text(errors="replace")
            fds: dict[str, str] = {}
            for fd in sorted((proc / "fd").iterdir(), key=lambda p: int(p.name)):
                try:
                    fds[fd.name] = os.readlink(fd)
                except OSError as exc:
                    fds[fd.name] = f"<{exc}>"
            row["fds"] = fds
        except OSError:
            row["vanished"] = True
        rows.append(row)
    locks = Path("/proc/locks").read_text(errors="replace") if Path("/proc/locks").exists() else ""
    (out_dir / "processes.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    (out_dir / "locks.txt").write_text(locks)
    try:
        ss = subprocess.run(["ss", "-ap"], capture_output=True, text=True, timeout=5, check=False)
        (out_dir / "sockets.txt").write_text(ss.stdout + ss.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        (out_dir / "sockets.txt").write_text(f"unavailable: {exc}\n")
    return {"pids": pids, "process_count": len(pids)}


def finish(proc: subprocess.Popen[bytes], timeout: float) -> int:
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return proc.wait(timeout=5)


def retained_paths(tmpdir: Path) -> list[str]:
    if not tmpdir.exists():
        return []
    return sorted(str(p.relative_to(tmpdir)) for p in tmpdir.rglob("*") if p.exists())


def run_stage(instrumented: Path, original: Path, output_root: Path, stage: str) -> dict[str, Any]:
    run_dir = output_root / stage
    run_dir.mkdir(parents=True, exist_ok=True)
    proc = run_command(instrumented, run_dir, stage)
    pgid = proc.pid
    checkpoint = run_dir / "checkpoint.tsv"
    wait_for(checkpoint, proc, 30)
    before = snapshot(run_dir, "before-signal", pgid)
    os.killpg(pgid, SIGNAL)
    time.sleep(0.15)
    after_signal = snapshot(run_dir, "after-signal", pgid)
    (run_dir / "release").touch()
    rc = finish(proc, 30)
    time.sleep(0.15)
    after_exit = snapshot(run_dir, "after-exit", pgid)
    leftovers = retained_paths(run_dir / "tmp")

    rerun_dir = run_dir / "rerun"
    rerun = run_command(original, rerun_dir, None)
    rerun_rc = finish(rerun, 30)
    rerun_leftovers = retained_paths(rerun_dir / "tmp")

    result = {
        "stage": stage,
        "signal": "SIGTERM",
        "signal_scope": "process-group",
        "checkpoint": checkpoint.read_text(errors="replace").strip(),
        "interrupted_exit": rc,
        "before_signal": before,
        "after_signal": after_signal,
        "after_exit": after_exit,
        "retained_paths": leftovers,
        "rerun_exit": rerun_rc,
        "rerun_retained_paths": rerun_leftovers,
        "output_target": "/dev/null",
    }
    (run_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def run_progress_parent_only(driver: Path, output_root: Path) -> dict[str, Any]:
    run_dir = output_root / "run-progress-parent-only"
    proc = run_driver(driver, run_dir, "run-progress-parent")
    pgid = proc.pid
    checkpoint = run_dir / "checkpoint.tsv"
    child_pid_file = run_dir / "run-progress-child.pid"
    wait_for(checkpoint, proc, 30)
    wait_for(child_pid_file, proc, 30)
    before = snapshot(run_dir, "before-signal", pgid)
    os.kill(proc.pid, SIGNAL)
    time.sleep(0.15)
    after_signal = snapshot(run_dir, "after-signal", pgid)
    (run_dir / "release").touch()
    rc = finish(proc, 30)
    time.sleep(0.15)
    after_exit = snapshot(run_dir, "after-exit", pgid)
    returned = (run_dir / "run-progress-returned").exists()
    stderr_text = (run_dir / "stderr.log").read_text(errors="replace")

    rerun_dir = run_dir / "rerun"
    rerun = run_driver(driver, rerun_dir, None)
    rerun_rc = finish(rerun, 30)
    time.sleep(0.15)
    rerun_after_exit = snapshot(rerun_dir, "after-exit", rerun.pid)

    result = {
        "stage": "run-progress-parent-only",
        "signal": "SIGTERM",
        "signal_scope": "run_progress-owner-pid-only",
        "checkpoint": checkpoint.read_text(errors="replace").strip(),
        "child_pid": int(child_pid_file.read_text().strip()),
        "interrupted_exit": rc,
        "interruption_logged": "run_progress() received signal TERM" in stderr_text,
        "returned_success": returned,
        "misreported_success": rc == 0 and returned and "run_progress() received signal TERM" in stderr_text,
        "before_signal": before,
        "after_signal": after_signal,
        "after_exit": after_exit,
        "rerun_exit": rerun_rc,
        "rerun_after_exit": rerun_after_exit,
    }
    (run_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def capture_environment(output_root: Path) -> None:
    commands = {
        "uname": ["uname", "-a"],
        "os-release": ["cat", "/etc/os-release"],
        "perl": ["perl", "-V:version"],
        "python": ["python3", "--version"],
        "apt": ["apt-get", "--version"],
        "dpkg": ["dpkg", "--version"],
        "tar": ["tar", "--version"],
    }
    rows: dict[str, dict[str, Any]] = {}
    for name, cmd in commands.items():
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        rows[name] = {"command": cmd, "exit": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
    rows["identity"] = {"uid": os.getuid(), "gid": os.getgid(), "euid": os.geteuid(), "egid": os.getegid()}
    (output_root / "environment.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")


def prepare_output(requested: Path, artifacts: Path) -> Path:
    output = requested.resolve()
    allowed_roots = (
        artifacts.resolve(),
        Path("/tmp").resolve(),
        Path("/var/tmp").resolve(),
    )
    if not any(root in output.parents for root in allowed_roots):
        roots = ", ".join(str(root) for root in allowed_roots)
        raise ValueError(
            f"output must be a child of one of: {roots}; got {output}"
        )
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def main() -> int:
    artifacts = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("upstream/mmdebstrap/mmdebstrap"))
    parser.add_argument("--output", type=Path, default=artifacts / "ci-run")
    args = parser.parse_args()

    output_root = prepare_output(args.output, artifacts)
    capture_environment(output_root)

    source_text = args.source.read_text()
    instrumented_text = instrument_source(source_text)
    instrumented = output_root / "mmdebstrap.instrumented"
    instrumented.write_text(instrumented_text)
    instrumented.chmod(0o755)
    driver = output_root / "mmdebstrap.run-progress-driver"
    driver.write_text(make_run_progress_driver(instrumented_text))
    driver.chmod(0o755)
    (output_root / "source.json").write_text(json.dumps({
        "path": str(args.source),
        "bytes": len(source_text.encode()),
        "sha256": hashlib.sha256(source_text.encode()).hexdigest(),
    }, indent=2, sort_keys=True) + "\n")

    results = [run_stage(instrumented, args.source.resolve(), output_root, stage) for stage in STAGES]
    run_progress_result = run_progress_parent_only(driver, output_root)
    summary = {
        "results": results,
        "run_progress_parent_only": run_progress_result,
        "all_interrupted_failed": all(item["interrupted_exit"] != 0 for item in results),
        "all_reruns_clean": all(item["rerun_exit"] == 0 and not item["rerun_retained_paths"] for item in results),
        "all_process_groups_empty": all(item["after_exit"]["process_count"] == 0 for item in results),
        "promotion_reproduced": run_progress_result["misreported_success"],
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    clean_required = summary["all_interrupted_failed"] and summary["all_reruns_clean"] and summary["all_process_groups_empty"]
    clean_targeted = (
        run_progress_result["misreported_success"]
        and run_progress_result["after_exit"]["process_count"] == 0
        and run_progress_result["rerun_exit"] == 0
        and run_progress_result["rerun_after_exit"]["process_count"] == 0
    )
    return 0 if clean_required and clean_targeted else 1


if __name__ == "__main__":
    raise SystemExit(main())
