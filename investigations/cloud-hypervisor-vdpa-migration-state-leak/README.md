# Cloud Hypervisor — vDPA failed-start migration state leak

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #585
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

`Vdpa::start_migration()` commits `self.migrating = true` before it proves that the backend can enter migration. If suspend support is absent or `suspend()` fails, the method returns `Err` with the flag still true.

That leaked flag is observable through later lifecycle decisions. `Vdpa::pause()` treats `migrating=true` as permission to return success, while pause outside live migration normally fails. `Vdpa::snapshot()` similarly requires `migrating=true` and then consumes the vDPA handle with `self.vhost.take()`.

A failed migration attempt can therefore alter later ordinary pause/snapshot behavior until some successful migration reaches `complete_migration()` and clears the flag.

## Explain like I'm five

The vDPA device flips an “I am migrating” switch before asking the backend whether migration is actually possible.

If the backend says no, the operation reports failure but the switch stays on. Later code trusts that switch and allows actions that are supposed to happen only during migration.

## Why care

The flag is not cosmetic. It controls whether vDPA pause and snapshot are legal, and snapshot has a destructive side effect: it drops the vDPA file handle so the device can be opened on the destination.

Failed setup should not grant later migration-only behavior.

## Current state

- State: `SCOPING`
- Exact working head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Latest authoritative gate: exact source review
- First incomplete step: execute a failed-start vDPA unit/test-double fixture
- Cleanup state: no runtime resources created
- Next safe action: force unsupported/failed suspend and observe the subsequent pause decision
- External-contact state: false; no upstream interaction authorized or made

## Question

Does failed `Vdpa::start_migration()` leave migration-only state enabled, and what is the smallest transactional change that restores the pre-call state on every error?

## Source

Path: `virtio-devices/src/vdpa.rs`

Relevant fields:

```text
vhost: Option<VhostKernVdpa<...>>
migrating: bool
```

### Start

```text
self.migrating = true
if backend_features has VHOST_BACKEND_F_SUSPEND {
    self.vhost.suspend()?
} else {
    Err("vDPA device can't be suspended")
}
```

Both the unsupported-feature branch and the failing-suspend branch return after the flag was set.

### Pause

```text
if self.migrating {
    Ok(())
} else {
    Err("Can't pause a vDPA device outside live migration")
}
```

### Snapshot

```text
if !self.migrating {
    return Err("Can't snapshot a vDPA device outside live migration")
}
...
self.vhost.take()
```

### Completion

```text
self.migrating = false
```

There is no shared migration-cancellation callback that runs after a failed start.

## Baseline sequence

```text
migrating=false
send-migration
start_migration sets true
backend lacks suspend / suspend fails
start_migration returns Err
migration worker returns source VM
migrating remains true
ordinary pause now takes migration-only success branch
```

If the VM is then paused and snapshotted, the stale flag also satisfies the vDPA snapshot guard and can consume the backend handle.

## First probe

Prefer a unit/test-double seam to avoid requiring vDPA hardware for the first discriminator.

1. Build a Vdpa instance or injectable backend whose suspend capability is absent.
2. Assert ordinary `pause()` initially rejects outside migration.
3. Call `start_migration()` and assert `Err`.
4. Call `pause()` again.
5. Current source is expected to return `Ok(())`; candidate must preserve the original rejection.

Second control: advertise suspend support but return an error from suspend. Post-error lifecycle result must be identical.

If a safe snapshot fixture is practical, confirm the stale flag also changes snapshot from rejection to acceptance and reaches `self.vhost.take()`.

## Candidate boundary

The narrow invariant is transactional state entry:

> `migrating=true` is committed only after the backend has successfully entered the migration state.

The smallest likely candidate is to validate suspend support, successfully call suspend, and only then assign the flag. An explicit rollback-on-error variant is equivalent if ordering constraints require the early flag.

Do not bundle the later-failure rollback problem into this patch. A successful vDPA migration start followed by snapshot has a different irreversible handoff issue, tracked in the broader rollback inventory associated with #584.

## Adjacent contexts

### DeviceManager partial start

`DeviceManager::start_migration()` iterates migratable devices with `?`. If a later device fails, earlier devices remain in whatever state their successful hooks established. That broader transactional question needs a cross-device rollback decision and should not enlarge this tiny flag fix.

### VM aggregate order

`Vm::start_migration()` runs memory-manager start first and then DeviceManager. MemoryManager currently uses the default no-op migration-start hook, so the strongest mutation risk in this path is the device iteration.

### VFIO

Current `VfioPciDevice::start_migration()` validates migration support and virtual-IOMMU compatibility without mutating migration state. Its pause/resume paths own VFIO state transitions with recovery. This is a useful negative control: not every migration hook needs rollback merely because it can return an error.

### vhost-user

Vhost-user start sets a migration flag and later snapshot deliberately shuts down the backend. Late migration failure after that snapshot is a separate rollback problem (#584).

## Results

Established by source review:

- vDPA sets `migrating=true` before two fallible entry checks;
- errors do not restore the flag;
- pause/snapshot use the flag as a permission predicate;
- snapshot can drop the vDPA handle;
- successful completion is the visible flag-clear path;
- shared failed-migration recovery has no cancellation hook.

Not yet executed:

- failed-start fixture;
- post-error pause/snapshot observations;
- candidate compile/tests/backend gates.

## Evidence boundary

This finding does not require guessing a thread schedule: it is a direct mutation-before-error path. The guest-visible consequence still needs executable confirmation, and the first candidate should be tested against both unsupported suspend and suspend-call failure if the latter can be injected cheaply.

## Stop condition

Close only if execution demonstrates another owner clears `migrating` before the failed migration returns the VM to ordinary ownership. Otherwise keep the change local to vDPA migration-state entry.

## Next step

Add the smallest failure-injection/unit seam, prove post-error pause behavior, then test the assignment-after-success candidate.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this investigation.
