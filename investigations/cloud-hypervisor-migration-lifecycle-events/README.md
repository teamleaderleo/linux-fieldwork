# Cloud Hypervisor lifecycle events during asynchronous migration

Updated: 2026-08-11

Upstream origin:

- async migration issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/7039
- merged async migration PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8021

Canonical source: `cloud-hypervisor/cloud-hypervisor` `main`
Exact source head: `915d359f97475b1a39d8561f8db514da9e692d19`
Primary owners:

- `vmm/src/lib.rs` — control loop, `VmOwnership`, migration dispatch/result handling
- `vmm/src/migration/worker.rs` — worker ownership and join behavior
- `cloud-hypervisor/src/main.rs` — VMM thread result and process exit

Current state: **source- and maintainer-confirmed lifecycle defect; runtime discriminator pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Asynchronous send-migration moves the `Vm` into a migration worker so ordinary lifecycle operations cannot race it. That ownership rule is intentional and good.

The unresolved edge is how asynchronous lifecycle **events** are handled while that worker owns the VM.

Current control-loop behavior is:

```text
Exit      -> vmm_shutdown() -> VmMigrating -> control loop returns Err
Reset     -> vm_reboot()    -> VmMigrating -> control loop returns Err
GuestExit -> shutdown path  -> VmMigrating -> control loop returns Err
```

When the `Vmm` is then dropped, `MigrationWorkerHandle::drop()` synchronously joins the migration worker. The process therefore waits for the in-flight migration to finish on its own before the VMM thread can return its error. `main` converts that VMM-thread error into process failure.

This exact behavior was called out during review of the merged async-migration PR: the reviewer said lifecycle events error the VMM thread and make it hang until the migration worker finishes. The PR author agreed and promised a follow-up. Current main still carries the three TODOs added by that PR, and no migration-cancellation API is present in current source.

The bounded question is:

> When a host- or guest-originated lifecycle event arrives during send-migration, which side should own the event, how should the migration be stopped or completed, and where should the lifecycle action execute exactly once?

The answer may differ by event authority. Treating Exit, Reset, and GuestExit as one generic cancellation policy would hide an important distinction.

## Explain like I'm five

During migration, Cloud Hypervisor hands the VM to a worker thread and says:

```text
you own the VM until migration finishes
```

Meanwhile the main VMM still listens for:

```text
stop the VMM
reboot the guest
guest powered itself off
```

Today one of those events can arrive and the main VMM asks for the VM back immediately. The ownership guard correctly answers “migration owns it.” The main loop then treats that answer as a fatal error and stops processing events. Cleanup waits for migration to finish anyway.

The missing piece is a deliberate handoff rule such as:

```text
cancel migration -> regain VM -> perform lifecycle action
```

or, for some guest-originated events:

```text
finish migration -> replay the guest lifecycle event at the destination
```

## Why care

The async migration work was introduced specifically so the source VMM remains manageable while migration runs. A SIGTERM, guest reboot, or guest shutdown that turns the control loop into a waiting fatal error defeats that operational goal at the highest-consequence lifecycle boundary.

There is also an exactly-once problem. If a guest shutdown/reset races migration completion, the action must neither disappear nor run on both source and destination.

## Exact current-source path

### 1. Migration takes exclusive VM ownership

`vm_send_migration()` validates the request, takes the owned `Vm`, spawns a worker, and replaces ordinary ownership with:

```text
VmOwnership::Migration {
    migration_worker_handle,
    vm_info_response,
    device_manager,
}
```

The source comments explicitly say the worker owns the VM and shared access is avoided to prevent races.

`take_owned_or()` preserves the migration ownership value and returns `VmError::VmMigrating` when a lifecycle operation asks for the VM during migration.

### 2. The control loop still receives asynchronous lifecycle events

Current main has three explicit TODOs:

```text
EpollDispatch::Exit
EpollDispatch::Reset
EpollDispatch::GuestExit
```

Each calls an ordinary lifecycle method after consuming the event.

During `VmOwnership::Migration`, those methods return `VmMigrating`. The `?` operator propagates that as `Error::VmmShutdown`, `Error::VmReboot`, or `Error::VmShutdown`, ending `control_loop()`.

### 3. Dropping the migration handle waits

`MigrationWorkerHandle` owns an optional `JoinHandle`.

Its `Drop` implementation says that if cleanup did not call `join()` explicitly, it logs a warning and then calls `handle.join()` synchronously.

So a lifecycle event does not cancel the migration. The VMM thread leaves its control loop and then blocks in drop until the worker naturally returns.

### 4. Main converts the result to process failure

`start_vmm()` joins the VMM thread and maps a returned VMM error through `Error::VmmThread`. `main()` converts an error result into exit code 1.

For an ordinary SIGTERM during migration, the current source path therefore points toward:

```text
SIGTERM -> Exit event -> VmMigrating -> VMM error
        -> drop joins migration worker
        -> migration finishes/fails on its own
        -> process exits failure
```

Runtime timing still needs confirmation on exact current main, especially around socket/receiver behavior while the source control loop has stopped.

## Upstream review evidence

PR 8021 introduced async send-migration and the `VmOwnership::Migration` state.

During review, Like Xu / `likebreath` called out this exact edge as a follow-up concern: lifecycle events such as Exit, Reset, and GuestExit hit `VmError::VmMigrating`, error the VMM thread, and make it wait for the migration worker to finish. The suggested direction was to cancel the in-flight send-migration and honor the lifecycle event.

The PR author agreed that this was a real problem. They also described an alternate/partial design used in their fork: postpone guest reboot/shutdown and replay the event on the destination after successful migration.

The PR merged with the lifecycle TODOs in place. Current main still contains them.

This is useful design evidence because it exposes two plausible policies rather than one obvious patch.

## Event authority split

### A. Host/VMM exit

Examples include SIGTERM/SIGINT and administrative VMM shutdown.

Likely invariant:

```text
operator requests process termination
-> migration cannot indefinitely delay termination
-> source VM ends in one known state
-> destination cannot become an unintended surviving owner
```

Leading policy: cancel/abort the migration, recover worker ownership, then honor the exit/shutdown locally.

A successful migration that races the cancellation boundary needs an explicit winner so two runnable VMs cannot survive.

### B. Guest reset

The guest itself requested reboot/reset.

Possible policies:

1. cancel migration, recover source VM, reboot there;
2. if migration has crossed a commit boundary, complete migration and replay reboot on destination.

The PR author's fork used the replay family for guest lifecycle events. This preserves guest intent while allowing migration to win once sufficiently advanced.

### C. Guest clean shutdown

Same exactly-once concern as reset, with an additional process-lifecycle choice when `--no-shutdown` is disabled.

A completed migration plus lost guest shutdown is wrong. A shutdown applied to both source and destination is also wrong.

## Important adjacent owner: generic Exit event

`exit_evt` is wider than a single operator action. It can also be used by internal error paths to request VMM termination.

Before implementing “defer every Exit during migration,” classify the event producer. A fatal internal exit and an ordinary administrative SIGTERM may share the EventFd while requiring the same prompt termination outcome for different reasons.

If source identity is needed to make the decision, a bare EventFd count may be too lossy and the repair boundary may need a small explicit pending-lifecycle state.

## Runtime matrix

Use a migration long enough to make the ownership interval observable. Prefer an existing timeout/load helper over arbitrary sleeps.

### Host-originated

| phase | event | expected discriminator |
|---|---|---|
| before worker ownership | SIGTERM / VMM shutdown | ordinary clean shutdown control |
| worker owns VM, early precopy | SIGTERM | current hang/error vs candidate cancellation |
| worker owns VM, paused/final phase | SIGTERM | race winner explicit |
| migration failure/cancel path | SIGTERM | no double cleanup |

### Guest-originated

| phase | event | observe |
|---|---|---|
| early precopy | reboot/reset | source vs destination owner, event count |
| final paused phase | reboot/reset | exactly-once action |
| early precopy | clean shutdown | source/destination state and process lifetime |
| final paused phase | clean shutdown | exactly-once action |

For every run capture:

- migration events (`migration-started`, `migration-finished` / `migration-failed`);
- source and destination process exit status;
- source/destination VM state;
- API responsiveness during the event;
- disk-lock owner after completion/failure;
- guest boot ID where reboot identity is relevant;
- shutdown/reboot event-monitor counts;
- surviving processes/sockets;
- whether the worker was explicitly joined or only joined from Drop.

## Negative controls

1. Same lifecycle event with no migration active.
2. Migration that completes with no lifecycle event.
3. Migration cancellation/failure with no lifecycle event.
4. `vm.info` during migration, which async migration intentionally supports through the saved info response.
5. One disallowed mutating API request during migration, which should return a controlled migration-state error without killing the VMM loop.

The fifth control is especially useful: it distinguishes normal API rejection from the asynchronous EventFd path that currently propagates out of the control loop.

## Candidate policy variants

### Variant A — cancellation first

On Exit/Reset/GuestExit while migration owns the VM:

1. request migration cancellation;
2. wait for the worker to return the VM through the normal result path;
3. restore `VmOwnership::Owned` when appropriate;
4. apply the pending lifecycle action exactly once;
5. continue or terminate the VMM according to that action.

This matches the reviewer suggestion and is the leading policy for administrative Exit.

### Variant B — destination replay for guest events

For guest reset/shutdown:

1. record the pending guest lifecycle action;
2. let migration reach a commit decision;
3. on successful transfer, replay it once on the destination;
4. on failed migration, replay it once on the recovered source VM.

This matches the PR author's described fork behavior.

It needs a reliable way to carry the pending action across the source/destination boundary and define the commit point.

### Variant C — hybrid by event owner

Most likely design family:

- administrative/fatal Exit -> cancel migration and honor locally;
- guest Reset/GuestExit -> cancellation or replay depending on migration commit state.

This avoids forcing an operator termination request and a guest reboot request through one policy simply because both arrive through the epoll loop.

## Cancellation mechanism gap

Issue 7039 listed “cancel migration” as being implemented, and PR 8021 review discussed a future `migration-cancellation` endpoint. Current repository search at `915d359f...` finds no cancel-migration API or equivalent public action.

That means a lifecycle repair may need to establish a worker cancellation primitive before it can be elegantly exposed to users. Keep that primitive narrow: the immediate requirement is controlled worker termination/return of VM ownership.

## Evidence boundary

Established:

- current main still contains all three migration lifecycle TODOs;
- migration uses exclusive worker ownership;
- lifecycle calls during worker ownership return `VmMigrating`;
- those event handlers propagate the error out of `control_loop()`;
- `MigrationWorkerHandle::drop()` joins the worker synchronously;
- `main()` turns the VMM-thread error into process failure;
- merged PR review explicitly identifies the same hang/error behavior as a real follow-up problem;
- the PR author agreed and described a destination-replay design used in a fork;
- no current cancel-migration action was found in source or current issue/PR search.

Pending:

- target-native reproduction on current head;
- measured termination delay during an intentionally long migration;
- source/destination state after each guest-originated race;
- selected cancellation/replay policy;
- candidate code and CI gates.

## Stop condition

Choose a design only after runtime distinguishes these ownership cases:

1. administrative Exit during worker ownership;
2. guest Reset during worker ownership;
3. guest shutdown during worker ownership;
4. a migration-failure neighbor;
5. a migration-success race near final handoff.

The selected candidate must prove:

- one VM owner after every outcome;
- lifecycle action applied exactly once;
- no indefinite wait for operator Exit;
- control loop remains alive for ordinary rejected API calls;
- cleanup owns every worker/socket/disk lock;
- migration success/failure events remain coherent.

## Next safe action

Reuse the existing live-migration integration harness to make a deterministic long-running send-migration, then inject SIGTERM first. That is the smallest high-signal case because PR review already predicts the current behavior and the operator-exit policy is the least ambiguous. Preserve process timing, event monitor output, source/destination exit status, and surviving state before attempting a cancellation design.
