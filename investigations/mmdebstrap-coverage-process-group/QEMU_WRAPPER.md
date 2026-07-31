# QEMU wrapper process-group model

Tracking: issue #306 and PR #313.

## In simple words

The coverage caller chooses both `run_null.sh` and `run_qemu.sh`. A caller-owned process group is useful only if the actual QEMU wrapper and its helper processes remain inside that operation boundary.

This focused model uses the exact imported `run_qemu.sh`, including its background output follower and cleanup function, while replacing only the expensive `timeout --foreground debvm-run ...` payload with a held disposable worker.

## Why care

The null backend proves nested shell-pipeline ownership. The QEMU wrapper has a different topology:

- `run_qemu.sh` wrapper;
- background `setpriv --pdeathsig TERM tail -f shared/output.txt`;
- foreground `timeout --foreground debvm-run ...` operation;
- wrapper EXIT/INT/TERM cleanup;
- guest-result file interpreted during cleanup.

A repair that stops the null pipeline but lets the QEMU-like foreground operation escape would not satisfy the caller-level contract.

## Exact model

Regression:

`tests/test_mmdebstrap_coverage_qemu_process_group.py`

The fixture retains the exact imported:

- `coverage.py` source;
- `run_qemu.sh` source;
- status-only patch from merged PR #204;
- group-owned candidate patch.

It provides controlled replacements for:

- `shellcheck` and `shfmt` — successful no-op checks;
- `lscpu` — deterministic generic topology;
- `timeout` — consumes the wrapper arguments and execs one held Python worker.

The fake foreground worker records its PID and process group, waits on the same FIFO-style barrier used by the null topology, writes guest status 0 only on release, and records later work.

No QEMU binary, debvm, socket, image mutation, root operation, or network access is used.

## Three-way parent-only SIGINT comparison

### Imported baseline

Expected and retained:

```text
coverage status: 0
QEMU-like foreground worker: alive after coverage and wrapper exit
later-work marker: written after release
```

The background tail may terminate through its parent-death signal, but the held foreground operation remains outside immediate-wrapper ownership.

### Merged status-only repair

Expected and retained:

```text
coverage status: 130
QEMU-like foreground worker: alive after coverage and wrapper exit
later-work marker: written after release
```

This distinguishes parent status correction from backend lifecycle ownership.

### Group-owned candidate

Expected and retained:

```text
coverage status: 130
live in-group QEMU-wrapper work: none
later-work marker: absent
```

The dedicated group includes the wrapper and foreground operation. Group TERM stops the complete retained operation boundary before the caller returns.

## Unsignaled control

The group-owned candidate is also released normally:

- the fake foreground operation writes guest status 0;
- `run_qemu.sh` completes its ordinary result handling;
- coverage records `result: SUCCESS`;
- the QEMU-like later-work marker exists;
- no live group member remains.

This protects ordinary wrapper semantics from a cancellation-only change.

## Why `timeout --foreground` matters

The imported wrapper explicitly uses `timeout --foreground`. The focused fake command follows the same foreground-command position and does not create another session or process group.

The selected caller boundary therefore contains the modeled operation. A future backend that calls `setsid()`, creates another group, delegates to a remote supervisor, or ignores TERM falls outside this evidence and must be reviewed separately.

## Cleanup discipline

The test:

- writes coverage stdout/stderr to files so escaped descendants cannot hold assertion pipes open;
- registers teardown for the coverage session and discovered backend group;
- distinguishes live processes from transient zombies through `/proc`;
- releases negative-control survivors only after recording their state;
- permits TERM-to-KILL escalation only inside fixture teardown, never as product policy.

## Evidence boundary

Established:

- exact wrapper construction and cleanup source are present;
- baseline and status-only parent-PID cancellation leave the held foreground operation alive;
- group ownership stops it;
- ordinary candidate completion remains successful.

Not established:

- real QEMU/debvm descendants;
- privileged helpers;
- monitor or serial socket behavior;
- `/dev/tty`-specific debug behavior;
- escaped sessions/groups;
- uncooperative descendants;
- TERM-to-KILL product policy.

Internal Linux Fieldwork evidence only. External contact authorized: `false`.