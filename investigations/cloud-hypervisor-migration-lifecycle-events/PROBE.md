# Probe plan — SIGTERM during send-migration

Updated: 2026-08-11

Source boundary: `cloud-hypervisor/cloud-hypervisor` main @ `915d359f97475b1a39d8561f8db514da9e692d19`

This probe is designed from the current integration harness. It is execution planning, not a recorded runtime result.

## Goal

Prove the smallest host-originated lifecycle case:

> After the source event monitor reports `vm.migration-started`, send SIGTERM to the source Cloud Hypervisor process while `VmOwnership::Migration` is active. Measure whether the source exits promptly or waits for the migration worker, and record source/destination state afterward.

The expected current behavior from source and merged PR review is that the VMM control loop errors with `VmMigrating`, then `MigrationWorkerHandle::drop()` joins the worker before process exit.

## Reuse current test machinery

Base the fixture on `_test_live_migration_tcp_timeout()` in `cloud-hypervisor/tests/integration.rs`.

That helper already provides:

- source and destination VMM processes;
- source and destination API sockets;
- source and destination event-monitor files;
- a 1.5 GiB shared-memory guest;
- `stress --vm 2 --vm-bytes 220M --vm-keep` to keep pages dirty;
- a TCP receive-migration endpoint;
- a `migration-receive-ready` gate before the source starts sending;
- a tight `downtime_ms=1` migration configuration;
- event helpers for `migration-started` / `migration-failed` / `migration-finished`;
- cleanup and child-output reporting.

The existing timeout-cancel test is ignored due to upstream issue 8651. Do not depend on its flaky assertion. Reuse only the deterministic setup pieces.

## Injection sequence

1. Boot the source guest and verify SSH/cpu-count control.
2. Start the memory stressor.
3. Start destination `receive-migration`.
4. Wait for destination `migration-receive-ready`.
5. Dispatch source `send-migration` with a long enough timeout to keep the worker alive during observation, for example:

```text
destination_url=tcp:127.0.0.1:<port>,downtime_ms=1,timeout_s=30,timeout_strategy=ignore
```

6. Confirm the `ch-remote send-migration` command itself returned success. Async dispatch semantics mean this does not mean migration completed.
7. Wait for source event monitor `migration-started`.
8. Record `t0 = Instant::now()`.
9. Send `SIGTERM` directly to `src_child.id()` with `libc::kill`.
10. Poll `src_child.try_wait()` for a short observation window such as 2 seconds.
11. Record whether source exited, its exit status if available, and elapsed time.
12. Continue observing source events until either migration finishes/fails or the worker would exceed the test's bounded timeout.
13. Record destination process state and API responsiveness.
14. Use the repository's existing `kill_child()` / process-group cleanup only after evidence capture.

## Why direct `libc::kill` for the observation

`test_infra::kill_child()` sends SIGTERM and then waits up to 10 seconds before falling back to SIGKILL. That helper is excellent cleanup but would combine the primary observation with its timeout policy.

For the discriminator, send SIGTERM directly, observe for a short fixed interval, then call `kill_child()` only if cleanup is still needed.

## Baseline outcomes

### Outcome A — current predicted defect

Within the short observation window:

```text
source process still alive
source API/control loop no longer responds normally
migration worker continues
```

Then, after migration worker completion/failure:

```text
source exits with failure
log chain includes lifecycle operation -> VmMigrating
```

This confirms the exact current source/review prediction.

### Outcome B — source has changed behavior elsewhere

Source exits promptly and cleanly after SIGTERM while migration is cancelled/closed coherently.

If this occurs, stop product work and identify the unseen cancellation owner before claiming the defect persists.

### Outcome C — prompt failure exit

Source exits promptly but with failure, and destination/migration state is left inconsistent or still active.

This is a distinct lifecycle defect; preserve source/destination state before cleanup.

## Required receipts

Capture:

- source exact commit and binary `--version`;
- command lines for source, destination, receive-migration, send-migration;
- source event-monitor sequence;
- destination event-monitor sequence;
- SIGTERM send timestamp;
- source exit timestamp/status;
- source stderr chain;
- source API response after SIGTERM if process remains alive;
- destination API response/state;
- migration command outcome;
- whether disk/backend locks remain owned;
- cleanup actions and surviving processes after cleanup.

## Negative controls

### Control 1 — SIGTERM without migration

Send SIGTERM to an otherwise equivalent running source VMM. It should establish ordinary termination latency and status.

### Control 2 — migration without SIGTERM

Run the same stressed migration configuration and allow it to reach its ordinary success/failure outcome. This bounds how long the migration worker would naturally live.

### Control 3 — rejected API request during migration

After `migration-started`, send a mutating API request that current ownership policy rejects with `VmMigrating`.

The VMM should stay alive because API errors are returned through the request channel instead of being propagated from the epoll lifecycle event handler. This proves that the defect owner is the asynchronous lifecycle-event path, not `VmMigrating` itself.

## Follow-up only after baseline

If Outcome A reproduces, run these in order:

1. `Reset` / guest reboot during the same controlled migration window.
2. `GuestExit` / clean guest shutdown.
3. a final-phase race close to migration completion.

Do not begin with all three. SIGTERM has the clearest authority contract and produces the smallest reviewable proof.

## Candidate acceptance criteria

A future candidate for administrative Exit should satisfy:

```text
migration-started
SIGTERM arrives
migration is explicitly cancelled or reaches an atomic commit winner
source process terminates promptly
at most one VM survives
all migration sockets/workers are cleaned up
process exit reflects deliberate termination, not VmMigrating failure
```

Guest reset/shutdown can select a different replay policy after their own probes.
