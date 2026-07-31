# Sudo backend process-group model

Tracking: issue #306 and PR #313.

## In simple words

Coverage selects `run_null.sh SUDO` for tests that require root. The wrapper contains nested pipelines and invokes:

```sh
env --chdir=./shared sudo --preserve-env sh -x ./test.sh
```

Correct parent status is not enough if sudo and the root test remain alive after the outer wrapper is terminated.

## Why care

The privileged path can continue to mutate shared files or system state after the coverage driver has reported cancellation. It also adds a sudo monitor/PTY boundary that could, in principle, create a different process group and escape caller ownership.

The focused matrix therefore checks both lifecycle and group identity.

## Exact local negative control

A disposable exact `run_null.sh SUDO` pipeline was started in a dedicated session. The generated root test recorded its PID, process group, UID, and waited on a FIFO.

Before cancellation, seven live members shared one session/group:

- outer `run_null.sh SUDO`;
- nested pipeline shells;
- `tee`;
- `sudo --preserve-env sh -x ./test.sh`;
- root `sh -x ./test.sh`.

The worker recorded UID 0.

TERM was sent only to the outer wrapper PID. It returned `-15`, while six group members remained alive and several were reparented to PID 1. After the FIFO was released, the root test wrote its later-work marker.

This confirms that sudo's monitor/PTY path does not make immediate-wrapper cancellation sufficient in the tested Sudo 1.9.16p2 configuration.

## Executable repository matrix

Regression:

`tests/test_mmdebstrap_coverage_sudo_process_group.py`

The module runs only when:

```text
sudo -n true
```

succeeds. Otherwise it is skipped as an unavailable environment capability rather than treated as product failure.

The fixture uses:

- exact imported `coverage.py`;
- exact imported `run_null.sh`;
- `Needs-Root: true` so coverage selects `run_null.sh SUDO` itself;
- actual passwordless sudo;
- a generated root test that records PID, PGID, UID, readiness, and later work;
- file-backed logs, `/proc` accounting, and registered group cleanup.

## Three-way result contract

### Imported baseline

Expected:

```text
coverage status: 0
root worker and sudo pipeline: alive after driver/wrapper return
later work: written after release
```

### Merged status-only repair

Expected:

```text
coverage status: 130
root worker and sudo pipeline: alive after driver/wrapper return
later work: written after release
```

### Group-owned candidate

Expected:

```text
coverage status: 130
live in-group sudo backend work: none
later work: absent
```

The test also requires the observed group to contain both the `run_null.sh SUDO` wrapper and `sudo --preserve-env` command. If sudo creates a different group in the hosted environment, the candidate fails rather than silently claiming ownership.

## Unsignaled control

The group-owned candidate is released normally:

- the root worker writes later work;
- the pipeline returns status 0;
- coverage records `result: SUCCESS`;
- no live group member remains.

## Compatibility boundary

The local negative control used Sudo 1.9.16p2 with `use_pty` enabled. The repository regression records the hosted sudo behavior rather than assuming every sudoers configuration is identical.

Not established:

- sudo configurations that deliberately create another session/group;
- password-prompt interaction;
- commands that daemonize or call `setsid()`;
- privileged descendants outside the local process namespace;
- TERM-ignoring privileged work;
- product escalation.

Fixture teardown may escalate after a failed assertion; the product patch does not.

## Working result

Passwordless sudo does not remove the need for caller-owned backend groups. In the tested topology, it remains inside the dedicated operation boundary and is stopped by group TERM.

Internal Linux Fieldwork evidence only. External contact authorized: `false`.