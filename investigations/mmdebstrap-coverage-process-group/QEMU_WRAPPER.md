# QEMU wrapper process-group model

State: `target-tested`

Tracking: issue #306 and PR #313.  
Exact candidate receipt: CI `30632491641`, job `91161937871`, success.

## In simple words

The coverage caller chooses both `run_null.sh` and `run_qemu.sh`. A caller-owned process group is useful only when the wrapper, its output follower, and its foreground operation stay inside that boundary.

This model keeps exact imported `run_qemu.sh` and replaces only the expensive `timeout --foreground debvm-run ...` payload with one held disposable worker.

## Retained topology

The exact wrapper contains:

- `run_qemu.sh`;
- a background `setpriv --pdeathsig TERM tail -f shared/output.txt` follower;
- a foreground `timeout --foreground debvm-run ...` operation;
- EXIT/INT/TERM cleanup;
- guest-result interpretation during cleanup.

The fixture supplies deterministic `shellcheck`, `shfmt`, `lscpu`, and `timeout` controls. The fake foreground worker records PID and process group, waits on a FIFO, writes guest status 0 on release, and records later work.

No QEMU binary, debvm, image mutation, socket, root operation, or network access is used.

## Three-way parent-only SIGINT result

### Imported baseline

After parent-only SIGINT:

- the QEMU-like foreground operation remains live;
- the coverage driver remains blocked waiting for the wrapper;
- no later-work marker exists yet;
- after fixture release, later work appears and the final driver status is 0.

### Merged status-only predecessor

After parent-only SIGINT:

- the QEMU-like foreground operation remains live;
- the coverage driver remains blocked waiting for the wrapper;
- no later-work marker exists yet;
- after fixture release, later work appears and the final driver status is 130.

This distinguishes corrected status from complete backend ownership.

### Group-owned candidate

After parent-only SIGINT:

- the complete modeled wrapper operation receives group TERM;
- the driver exits 130 without fixture release;
- no live in-group backend remains;
- no later-work marker appears.

## Unsignaled control

The candidate also preserves ordinary behavior:

- the fake foreground operation writes guest status 0;
- `run_qemu.sh` completes normal result handling;
- coverage records `result: SUCCESS`;
- the later-work marker exists;
- no live group member remains.

## Why `timeout --foreground` matters

The imported wrapper explicitly uses `timeout --foreground`. The fake command occupies the same foreground-command position and does not create another session or process group. The selected caller boundary therefore contains the modeled operation.

A future backend that calls `setsid()`, creates a new group, delegates to a remote supervisor, or ignores TERM falls outside this evidence.

## Exact repository receipt

CI `30632491641` passed all four QEMU controls on exact PR #313 head `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`:

- baseline survivor and final status 0 after release;
- status-only survivor and final status 130 after release;
- group candidate status 130 with no live operation and no later work;
- unsignaled candidate success and clean teardown.

The same job passed all 359 repository tests.

## Cleanup discipline

The test:

- writes stdout/stderr to files;
- records live group state before releasing negative controls;
- verifies the driver is still blocked while the operation survives;
- registers driver-session and backend-group teardown;
- distinguishes live members from zombies through `/proc`;
- permits TERM-to-KILL escalation only in fixture teardown.

## Evidence boundary

Established:

- exact wrapper construction and cleanup source are retained;
- immediate-wrapper cancellation leaves the modeled foreground operation alive;
- group ownership stops it;
- ordinary candidate completion remains successful.

Not established:

- real QEMU/debvm descendants;
- monitor or serial socket behavior;
- privileged helpers;
- `/dev/tty`-specific behavior;
- escaped sessions/groups;
- uncooperative descendants;
- product TERM-to-KILL policy.

Internal Linux Fieldwork evidence only. External contact authorized: `false`.
