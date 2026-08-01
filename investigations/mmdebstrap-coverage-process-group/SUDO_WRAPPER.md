# Sudo backend process-group model

State: `target-tested`

Tracking: issue #306 and PR #313.  
Exact candidate receipt: CI `30632491641`, job `91161937871`, success.

## In simple words

Coverage selects `run_null.sh SUDO` for tests that require root. The wrapper contains nested pipelines and invokes:

```sh
env --chdir=./shared sudo --preserve-env sh -x ./test.sh
```

Correct cancellation status is incomplete when sudo and the UID-0 worker continue after the outer wrapper is terminated.

## Why this path needs a separate control

The privileged path adds a sudo monitor/PTY boundary that could create another process group and escape caller ownership. The focused matrix therefore checks both lifecycle and observed group identity.

## Exact local negative control

A disposable exact `run_null.sh SUDO` pipeline ran in a dedicated session. The generated root test recorded PID, process group, UID, readiness, and later work.

In the retained Sudo 1.9.16p2/use_pty topology, seven live members shared the operation group before cancellation. Wrapper-only TERM left six members alive. After FIFO release, the UID-0 worker performed later work.

This proves that immediate-wrapper cancellation is insufficient in the tested configuration.

## Repository matrix

Regression:

`tests/test_mmdebstrap_coverage_sudo_process_group.py`

The module executes when `sudo -n true` succeeds. Otherwise it skips as an unavailable environment capability.

The fixture uses:

- exact imported `coverage.py`;
- exact imported `run_null.sh`;
- `Needs-Root: true`, so coverage selects `run_null.sh SUDO` itself;
- actual passwordless sudo;
- a generated root test that records PID, PGID, UID, readiness, and later work;
- file-backed logs and Linux `/proc` accounting.

## Three-way result

### Imported baseline

- final coverage status: 0;
- root worker and sudo pipeline survive wrapper-only termination;
- later work appears after release.

### Merged status-only predecessor

- final coverage status: 130;
- root worker and sudo pipeline survive wrapper-only termination;
- later work appears after release.

### Group-owned candidate

- coverage status: 130;
- no live in-group sudo backend work remains;
- later work is absent.

The test requires the observed group to contain both the `run_null.sh SUDO` wrapper and the `sudo --preserve-env` command. A hosted group escape fails the control instead of silently upgrading the claim.

## Unsignaled control

The group-owned candidate also completes normally:

- the root worker writes later work;
- the pipeline returns status 0;
- coverage records `result: SUCCESS`;
- no live group member remains.

## Exact repository receipt

CI `30632491641` passed all four sudo controls on exact PR #313 head `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`:

- baseline survivor and final status 0;
- status-only survivor and final status 130;
- candidate status 130 with no live privileged work and no later work;
- unsignaled candidate success and clean teardown.

The same job passed all 359 repository tests.

## Compatibility boundary

The hosted and local controls record the available sudo behavior rather than assuming every sudoers policy is identical.

Not established:

- sudo configurations that create another session or process group;
- password-prompt interaction;
- commands that daemonize or call `setsid()`;
- privileged descendants outside the local process namespace;
- TERM-ignoring work;
- product escalation.

Fixture teardown may escalate after a failed assertion; the product patch does not.

## Working result

Passwordless sudo does not remove the need for caller-owned backend groups. In the tested topology, sudo remains inside the dedicated operation boundary and is stopped by group TERM.

Internal Linux Fieldwork evidence only. External contact authorized: `false`.
