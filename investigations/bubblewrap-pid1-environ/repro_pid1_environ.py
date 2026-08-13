#!/usr/bin/env python3
import argparse
import ctypes
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"This process .*fork.*")

MARKER_NAME = "FIELDWORK_MARKER"
OLD_VALUE = "fieldwork-old-marker"
NEW_VALUE = "fieldwork-new-marker"
CONTROL_NAME = "FIELDWORK_CONTROL"
CONTROL_VALUE = "fieldwork-control-kept"
libc = ctypes.CDLL(None, use_errno=True)
libc.getenv.restype = ctypes.c_char_p


def proc_environ(pid="self"):
    with open(f"/proc/{pid}/environ", "rb") as f:
        return f.read()


def c_getenv(name):
    value = libc.getenv(name.encode())
    return None if value is None else value.decode(errors="replace")


def run_model_case(kind):
    rfd, wfd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(rfd)
        if kind == "clearenv":
            if libc.clearenv() != 0:
                os._exit(90)
        elif kind == "unsetenv":
            if libc.unsetenv(MARKER_NAME.encode()) != 0:
                os._exit(91)
        elif kind == "setenv":
            if libc.setenv(MARKER_NAME.encode(), NEW_VALUE.encode(), 1) != 0:
                os._exit(92)
        else:
            os._exit(93)

        data = proc_environ()
        line = (
            f"{kind}: getenv={c_getenv(MARKER_NAME)!r} "
            f"control={c_getenv(CONTROL_NAME)!r} "
            f"proc_old={f'{MARKER_NAME}={OLD_VALUE}'.encode() in data} "
            f"proc_new={f'{MARKER_NAME}={NEW_VALUE}'.encode() in data} "
            f"proc_control={f'{CONTROL_NAME}={CONTROL_VALUE}'.encode() in data}\n"
        )
        os.write(wfd, line.encode())
        os.close(wfd)
        os._exit(0)

    os.close(wfd)
    output = os.read(rfd, 4096).decode().strip()
    os.close(rfd)
    _, status = os.waitpid(pid, 0)
    if status != 0:
        raise RuntimeError(f"model child {kind} failed: status={status}")
    print(output)
    return output


def run_model():
    if os.getenv(MARKER_NAME) != OLD_VALUE or os.getenv(CONTROL_NAME) != CONTROL_VALUE:
        print("model requires both synthetic environment values", file=sys.stderr)
        return 2

    outputs = {kind: run_model_case(kind) for kind in ("clearenv", "unsetenv", "setenv")}
    ok = (
        "getenv=None control=None proc_old=True proc_new=False proc_control=True" in outputs["clearenv"]
        and f"getenv=None control='{CONTROL_VALUE}' proc_old=True proc_new=False proc_control=True" in outputs["unsetenv"]
        and f"getenv='{NEW_VALUE}' control='{CONTROL_VALUE}' proc_old=True proc_new=False proc_control=True" in outputs["setenv"]
    )
    return 0 if ok else 1


def bwrap_case(path, name, env_args, as_pid_1=False):
    py = (
        "import os; "
        "d=open('/proc/1/environ','rb').read(); "
        f"print('command_value='+repr(os.getenv('{MARKER_NAME}'))); "
        f"print('command_control='+repr(os.getenv('{CONTROL_NAME}'))); "
        f"print('pid1_old='+str(b'{MARKER_NAME}={OLD_VALUE}' in d)); "
        f"print('pid1_new='+str(b'{MARKER_NAME}={NEW_VALUE}' in d)); "
        f"print('pid1_control='+str(b'{CONTROL_NAME}={CONTROL_VALUE}' in d))"
    )
    cmd = [path, "--unshare-pid"]
    if as_pid_1:
        cmd.append("--as-pid-1")
    cmd += [
        "--dev-bind", "/", "/",
        "--proc", "/proc",
        *env_args,
        "--", "/usr/bin/python3", "-c", py,
    ]
    env = os.environ.copy()
    env[MARKER_NAME] = OLD_VALUE
    env[CONTROL_NAME] = CONTROL_VALUE
    completed = subprocess.run(cmd, env=env, text=True, capture_output=True, check=False)
    output = completed.stdout.strip().replace("\n", "; ")
    error = completed.stderr.strip().replace("\n", "; ")
    print(f"{name}: rc={completed.returncode} stdout=[{output}] stderr=[{error}]")
    return completed.returncode, completed.stdout


def empty_environment_case(path):
    cmd = [
        path,
        "--unshare-pid",
        "--dev-bind", "/", "/",
        "--proc", "/proc",
        "--clearenv",
        "--", "/usr/bin/python3", "-c",
        f"import os; print('marker='+repr(os.getenv('{MARKER_NAME}'))+' control='+repr(os.getenv('{CONTROL_NAME}')))",
    ]
    completed = subprocess.run(cmd, env={}, text=True, capture_output=True, check=False)
    output = completed.stdout.strip().replace("\n", "; ")
    error = completed.stderr.strip().replace("\n", "; ")
    print(f"empty-env-clearenv: rc={completed.returncode} stdout=[{output}] stderr=[{error}]")
    return completed.returncode == 0 and "marker=None control=None" in completed.stdout


def run_bwrap(path, expect_scrubbed=False):
    helper_old = False if expect_scrubbed else True
    clear_control = False if expect_scrubbed else True
    cases = [
        ("clearenv-helper", ["--clearenv"], False, None, None, helper_old, False, clear_control),
        ("unsetenv-helper", ["--unsetenv", MARKER_NAME], False, None, CONTROL_VALUE, helper_old, False, True),
        ("setenv-helper", ["--setenv", MARKER_NAME, NEW_VALUE], False, NEW_VALUE, CONTROL_VALUE, helper_old, False, True),
        ("clearenv-as-pid-1-control", ["--clearenv"], True, None, None, False, False, False),
    ]
    rc = 0
    for name, args, as_pid_1, command_value, command_control, expect_old, expect_new, expect_control in cases:
        status, stdout = bwrap_case(path, name, args, as_pid_1)
        if status != 0:
            rc = 2
            continue
        expected_command = f"command_value={command_value!r}"
        expected_command_control = f"command_control={command_control!r}"
        got_old = "pid1_old=True" in stdout
        got_new = "pid1_new=True" in stdout
        got_control = "pid1_control=True" in stdout
        if (
            expected_command not in stdout
            or expected_command_control not in stdout
            or got_old != expect_old
            or got_new != expect_new
            or got_control != expect_control
        ):
            rc = max(rc, 1)

    if not empty_environment_case(path):
        rc = max(rc, 1)

    return rc


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model", action="store_true")
    group.add_argument("--bwrap", metavar="PATH")
    parser.add_argument("--expect-scrubbed", action="store_true")
    args = parser.parse_args()
    if args.model:
        return run_model()
    return run_bwrap(args.bwrap, expect_scrubbed=args.expect_scrubbed)


if __name__ == "__main__":
    sys.exit(main())
