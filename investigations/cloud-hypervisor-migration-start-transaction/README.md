# Cloud Hypervisor — transactional device migration start

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #586
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

`DeviceManager::start_migration()` applies device start hooks sequentially and stops at the first error. It has no rollback for earlier devices that already changed state.

That is immediately dangerous with vDPA: a successful vDPA start sets migration state and suspends the backend before the VM pause stage. A later device can reject migration, causing the worker to fail while the VM still reports `Running`. Generic migration recovery only calls `vm.resume()` when the VM state is `Paused`, so no device resume is run for this early failure.

A running source VM can therefore be returned to normal ownership with an earlier device still in migration-specific runtime state.

## Explain like I'm five

Cloud Hypervisor asks each device, one after another, to enter migration mode.

If device A succeeds and device B says “I can't migrate,” the function returns an error. It does not tell A to undo what it just did.

For vDPA, “enter migration mode” can actually suspend the hardware backend while the guest CPUs are still running.

## Why care

Migration-start failure must not strand parts of a running VM in migration mode. The current behavior depends on every device succeeding after earlier devices have already committed their own transitions.

## Current state

- State: `SCOPING`
- Exact working head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Latest authoritative gate: source/call-graph inventory
- First incomplete step: deterministic fake-device aggregate test
- Cleanup state: no runtime resources created
- Next safe action: prove one successful start remains committed after a later controlled failure
- External-contact state: false; no upstream interaction authorized or made

## Source boundary

### DeviceManager

```text
for each DeviceTree entry:
    if migratable:
        migratable.start_migration()?
```

There is no successful-start list and no unwind step.

`DeviceTree` wraps a `HashMap<String, DeviceNode>`, so iteration ordering is not a stable correctness boundary.

### VM

`Vm::start_migration()` currently calls MemoryManager first, then DeviceManager. MemoryManager does not override the migration-start hook, so the material current mutations are in devices.

### vDPA success

A migratable vDPA can successfully:

```text
migrating = true
backend suspend()
```

before `send_migration()` reaches the memory-migration pause path.

### Later rejection

VFIO provides useful pure-validation failures in `start_migration()`:

```text
migration v2 unsupported -> Err
virtual IOMMU attached    -> Err
```

Those failures do not need to mutate VFIO state, so they cleanly distinguish aggregate rollback from a failing component's own cleanup.

## Generic failed-worker recovery

`Vmm::check_migration()` resumes only when:

```text
initial VM state == Running
current VM state == Paused
```

A failure in `Vm::start_migration()` occurs before the normal migration pause, so the VM can still be `Running`; the recovery path then skips `vm.resume()` entirely.

That makes DeviceManager-level rollback the only visible place to undo an earlier start-time device transition.

## First executable discriminator

Use fake `Migratable` components, not hardware.

Two fakes share an `AtomicUsize` call counter:

- each start increments the counter;
- call number 1 records a committed state and returns `Ok`;
- call number 2 records entry and returns a controlled `Err`.

This is independent of HashMap ordering: whichever node is first succeeds, whichever is second fails.

Baseline assertion:

```text
aggregate result = Err
successful first component remains committed = true
```

A candidate with rollback should restore the first component before returning.

## Candidate design questions

### Rollback hook

Add a migration-cancel hook and unwind successfully started devices in reverse order.

Pros:
- also useful for failures after all starts succeed;
- represents real compensating transitions for stateful devices.

Questions:
- rollback itself can fail;
- how to preserve the original error while surfacing rollback failures;
- whether rollback order must be reverse of start order.

### Two-phase preflight

Add non-mutating migration capability/precondition validation before mutating start hooks.

Pros:
- VFIO unsupported migration and vDPA missing-suspend capability can fail before any device is changed;
- reduces rollback frequency.

Limits:
- actual suspend/start operations remain fallible even after capability validation;
- later migration failures still need rollback for vhost-user/vDPA destructive state.

A combined preflight + rollback contract may be appropriate, but the first patch should follow executable evidence rather than redesign the full migration trait immediately.

## Component inventory so far

### vDPA

Stateful and fallible. Successful start suspends backend. Its own failed-start flag leak is tracked separately in #585.

### VFIO

Current start hook is validation-only. It rejects unsupported migration or virtual-IOMMU migration before pause. Pause/resume own VFIO migration-state transitions with their own recovery helper.

### regular virtio-net

`start_migration()` invalidates announcement generation only. Normal `resume()` notifies announcements again. This is lighter state but still shows that start hooks need not be pure validation.

### vhost-user family

Start sets migration state; snapshot later becomes destructive and shuts down backend connections. Late-failure rollback is tracked in #584.

### MemoryManager

Uses the default no-op `start_migration()` on current source. Dirty logging has separate start/stop hooks and recovery already tries to stop dirty logging after migration failure.

## Evidence boundary

Established:

- aggregate start is sequential and not transactional;
- ordering is HashMap-backed;
- at least one supported component (vDPA) has a real runtime mutation on successful start;
- later device failures exist before VM pause;
- generic recovery skips resume while VM state remains Running.

Pending:

- fake-device unit proof;
- real vDPA + later rejecting device consequence;
- rollback/preflight candidate;
- CI.

## Stop condition

Close only if a faithful aggregate test reveals a hidden unwind path. Otherwise retain this as the aggregate transaction owner even if individual component bugs are fixed separately.

## Next step

Implement the deterministic fake-device test, then compare a minimal rollback prototype with a preflight-validation prototype.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this investigation.
