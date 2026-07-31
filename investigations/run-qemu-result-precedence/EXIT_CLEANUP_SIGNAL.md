# Retain signals that arrive during ordinary EXIT cleanup

State: `candidate-created — exact-head CI pending`

## TL;DR

The stacked `run_qemu.sh` repair at `39a7fafcde48ee8efb99ce6829486327e51abbdb` correctly keeps a second handled signal from replacing the first signal-derived result. It applies the same ignore policy to ordinary EXIT cleanup, where no signal has yet been retained.

A TERM delivered after successful work enters EXIT cleanup is therefore ignored and the wrapper can return 0. The third patch records the first INT/TERM during ordinary cleanup, completes cleanup, and applies:

```text
captured host failure > first cleanup-time signal > guest failure > first cleanup failure > success
```

Explicit signal cleanup keeps the existing policy: once INT or TERM already selected 130/143, later handled signals remain ignored until bounded cleanup finishes.

## Explain like I'm five

The second repair says, “Once I heard a stop alarm, ignore more stop alarms while I put the tools away.” That is useful.

But it also says, “If I started putting tools away after normal success, ignore the first stop alarm too.” The wrapper can then finish and say success even though someone pressed stop.

The third repair remembers the first stop alarm during normal cleanup, finishes putting the tools away, and reports the stop.

## Why care

Cancellation during cleanup is still cancellation. Returning 0 can make a scheduler, package test, or developer believe the workload completed normally. At the same time, immediately terminating cleanup can leave temporary state behind.

The lifecycle contract needs both properties:

- a first signal during ordinary cleanup is retained and reported;
- a second handled signal cannot replace an already-retained result or interrupt bounded cleanup.

## Exact source boundary

The composed predecessor is:

1. `0001-preserve-primary-result.patch`;
2. `0002-retain-first-signal-through-cleanup.patch`.

Both patches apply with zero fuzz to imported `upstream/mmdebstrap/run_qemu.sh` blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`.

The predecessor ordinary EXIT handler is:

```sh
cleanup_exit() {
  rv=$?
  trap '' INT TERM
  trap - EXIT
  finish "$rv"
}
```

Ignoring INT and TERM here occurs before any signal status has been retained.

## Deterministic predecessor control

The focused test:

1. starts a shell model built from the exact composed functions and traps;
2. exits ordinary work with status 0;
3. blocks inside the first cleanup action and publishes `cleanup-ready`;
4. sends TERM to the wrapper PID;
5. releases cleanup;
6. records final status, cleanup log, and temporary-directory state.

Expected predecessor result:

```text
status: 0
cleanup log: rm, rmdir
temporary directory: removed
```

Cleanup completes, but cancellation disappears.

## Third patch

`0003-retain-signal-during-exit-cleanup.patch` adds one initialized status slot and one first-writer recorder.

During ordinary EXIT cleanup:

```sh
trap 'record_cleanup_signal 130' INT
trap 'record_cleanup_signal 143' TERM
trap - EXIT
```

The first handled signal stores its status. Later handled signals leave that value unchanged. After cleanup, `finish()` first switches INT and TERM to ignored, then promotes the recorded signal only when the already-captured host status is zero.

This order closes the final decision window: a signal accepted before cleanup finishes is retained; signals after the cleanup boundary cannot change the selected result while the wrapper exits.

During explicit `cleanup_signal()`, INT and TERM remain ignored because the first signal status was already supplied directly to `finish()`.

## Executable contract

`tests/test_run_qemu_exit_cleanup_signal.py` covers:

- zero-fuzz application of all three patches;
- complete `/bin/sh -n` on the composed source;
- exact predecessor ordinary EXIT→TERM false success;
- repaired ordinary EXIT→INT 130 and EXIT→TERM 143;
- INT→TERM and TERM→INT during the same cleanup, requiring the first to win;
- captured host failure 42 over a later cleanup-time TERM;
- cleanup-time TERM over guest failure 1;
- cleanup-time TERM over cleanup failure 74/75;
- complete `rm, rmdir` cleanup on the successful cleanup path;
- temporary-directory removal;
- immediate clean rerun;
- source-shape checks distinguishing ordinary EXIT signal recording from explicit signal cleanup ignoring.

## Result precedence

| Captured host status | Cleanup-time signal | Guest | Cleanup | Final status |
| --- | --- | --- | --- | --- |
| nonzero | any | any | any | captured host status |
| 0 | first INT/TERM | any | any | 130/143 |
| 0 | none | failure | any | 1 |
| 0 | none | success | first failure | first cleanup failure |
| 0 | none | success | success | 0 |

This chooses the first primary event: a host failure captured before EXIT cleanup is not replaced by a later signal. When the captured host result is success, a cleanup-time signal becomes the primary failure.

## Cleanup and safety

The regression uses disposable directories, short-lived `/bin/sh` processes, PID-targeted INT/TERM, and deterministic file barriers. It runs no QEMU, debvm, guest image, network request, package installation, mount, root operation, public target, or credential-bearing command.

Every process is awaited. The release marker is created only while the process remains alive. Temporary directories are owned by Python context managers and the candidate also proves immediate rerun after signaled cleanup.

## Evidence boundary

The reduction proves shell trap and result behavior for the exact composed source shape. It does not prove full QEMU integration, process-group delivery, foreground-child cancellation, HUP/QUIT behavior, escalation policy, or cleanup that blocks indefinitely.

Ignoring later INT/TERM is justified only for this bounded cleanup path. A long or unbounded cleanup path would need an explicit escalation contract.

## Disposition

Open a stacked repair against branch `fix/run-qemu-result-precedence`, execute exact-head Linux Fieldwork CI, and review the complete four-file delta plus the composed thirteen-file result before merging into PR #270.

Internal Linux Fieldwork work only. External contact authorized: `false`.
