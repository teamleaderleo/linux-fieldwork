# Cloud Hypervisor — failed migration disk-lock recovery

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #583
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

A default live migration (`preserve_source=false`) can cross the source disk-lock handoff point, fail later, and then resume the source VM without reacquiring its advisory disk locks.

`Vmm::send_migration()` pauses the source during migration and calls `vm.release_disk_locks()` before several fallible snapshot/protocol/completion operations. `Vmm::check_migration()` recovers any failed migration by resuming a paused source, stopping dirty logging, and returning the VM to `VmOwnership::Owned`. It does not call `try_lock_disks()`.

`Vm::restore()` does explicitly acquire disk locks before restored vCPUs start, and the lock API documentation says locks should be held before a VM starts running. This makes failed migration recovery an asymmetric path worth immediate runtime discrimination.

## Explain like I'm five

Cloud Hypervisor puts a “someone is using this disk” lock on writable VM disks.

During live migration it eventually removes that lock so the destination can take over. That handoff happens before every last migration step is guaranteed to succeed.

If a later step fails, Cloud Hypervisor wakes the original VM back up. The recovery code does not put the disk lock back first.

## Why care

The advisory lock exists to prevent two Cloud Hypervisor processes from accidentally writing the same disk image at once. A recovered source VM that runs without its lock no longer has that protection.

An independent process could acquire the disk's write lock during or after the failed handoff. Recovery must not resume guest I/O until the source has regained the lock.

## Current state

- State: `SCOPING`
- Exact working head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Latest authoritative gate: current source + original disk-lock history
- First incomplete step: execute a late-failure migration and inspect OFD lock state
- Cleanup state: no runtime resources created
- Next safe action: inject failure after lock release and compare pre/post lock ownership
- External-contact state: false; no upstream interaction authorized or made

## Intent and precedent

Disk locks were introduced by upstream commit `05968f5c2c1b65fb0c75fda31e27cfa10c95ada2`.

That commit describes OFD advisory locks as protection against multiple Cloud Hypervisor processes writing the same disk image. Its migration rationale says the sender must release locks when the VM stops so the receiving side can acquire them.

Current `Vm::release_disk_locks()` documents:

```text
This should only be called when the VM is stopped and the VMM supposed
to shut down. A new VMM ... should then acquire all locks before the VM
starts to run.
```

A failed migration is different: the source VMM remains authoritative and its VM may be resumed.

## Question

When a live migration fails after the source disk locks have been released, does failed-migration recovery restore those locks before guest execution resumes?

## Source

### Release point

`Vmm::send_migration()` completes the precopy pause/memory phase and then, when `preserve_source` is false, does:

```text
vm.release_disk_locks()?
```

This is not the end of the migration. Fallible work still follows:

- postcopy fault-connection setup and thread spawn where applicable;
- `vm.snapshot()`;
- final dirty-memory handling caused by snapshot side effects;
- `send_state()`;
- Complete/CompletePaused request + acknowledgement;
- migration-context finalization;
- `vm.stop_dirty_log()`;
- postcopy serve-thread join;
- `vm.complete_migration()`.

Any failure propagates to `MigrationWorkerResult`.

### Failure recovery

`Vmm::check_migration()` joins the migration worker. On `Err`, it runs a recovery closure:

```text
if initial state was Running and current state is Paused:
    vm.resume()

vm.stop_dirty_log()
self.vm = VmOwnership::Owned(vm)
```

No disk-lock acquisition occurs there.

### Known acquire path

`Vm::restore()` performs:

```text
self.device_manager.lock().unwrap().try_lock_disks()?
start_restored_vcpus()
```

The acquire-before-running ordering is therefore already implemented for restore.

Repository search on current source finds `try_lock_disks()` at the restore path, not failed live-migration recovery.

## Baseline consequence

A late failure can produce this sequence:

```text
source VM owns exclusive disk lock
source VM pauses
source explicitly clears disk lock
migration's later protocol/snapshot step fails
migration worker returns Err
VMM resumes source VM
source returns to normal Owned state
no lock reacquire is visible
```

The guest can then continue disk I/O through already-open file descriptors while the advisory lock is no longer protecting the image.

## First executable discriminator

Use a writable regular image covered by the built-in advisory locking mechanism.

1. Boot source VM and prove a second write lock is denied.
2. Start live migration.
3. Let migration reach the post-pause lock-release point.
4. Deliberately fail a later operation, preferably the State or Complete exchange so the release point is unambiguous.
5. Wait for source failed-migration recovery to finish.
6. Prove the source VM is running again.
7. From an independent helper, query/acquire the image OFD write lock.

Expected baseline if the source analysis is correct:

```text
pre-migration second writer: denied
post-failure recovered source: running
post-failure second writer lock: succeeds
```

## Negative controls

- Fail migration before the lock-release point: original lock should remain held.
- `preserve_source=true`: release is skipped, lock should remain held.
- readonly image: shared read-lock semantics should remain internally consistent.
- successful migration: destination should acquire the image lock through restore as designed.

## Candidate boundary

Required invariant:

> A source VM returned to runnable ownership after migration failure must hold every advisory disk lock it held before migration before any guest execution resumes.

The ordering must be reacquire -> resume, not resume -> reacquire.

If reacquisition fails because the destination or another process acquired the disk during the handoff window, automatic source resume is unsafe. Recovery should leave the source paused/stopped and report the lock conflict.

The candidate should account for whether the lock-release point was crossed. Before selecting an unconditional reacquire, test whether acquiring the same OFD lock again when it was never released is harmless and whether partial multi-disk reacquisition needs rollback/error handling.

## Adjacent contexts

### Multiple disks

`try_lock_disks()` loops over block devices. If reacquisition succeeds for some disks then fails on another, recovery policy must avoid resuming with a partial lock set. This may require either rollback or a safe stopped state.

### Destination already acquired locks

A late failure may happen after destination restore has acquired disk locks. That makes source reacquisition fail for a legitimate reason. The correct recovery outcome is a human/orchestrator-visible failure with the source not running, not forcing the lock or racing the destination.

### Preserve-source mode

`preserve_source=true` intentionally keeps source locks and should remain a passing control.

### Vhost-user block

The advisory lock mechanism explicitly excludes vhost-user block devices. Keep them outside this candidate.

## Results

Established by source/history review:

- live migration explicitly releases source disk locks before several remaining fallible operations;
- migration failure recovery can resume the paused source VM;
- recovery does not reacquire disk locks;
- restore does acquire locks before starting restored vCPUs;
- lock API/history identifies acquire-before-run as the intended safety contract.

Not yet executed:

- a late-failure source recovery on current main;
- independent OFD lock-state proof after recovery;
- multi-disk partial reacquisition behavior;
- a candidate patch or CI gates.

## Evidence boundary

This is a source-ordering finding with strong intent evidence. Fieldwork has not yet shown a second process acquiring the image while the recovered source runs. That runtime discriminator is required before promotion.

No claim is made about vhost-user block locking.

## Stop condition

Close as a negative result if a controlled late-failure run proves another current owner reacquires every lock before source resume. Otherwise keep the fix centered on failed-migration recovery; do not bundle unrelated migration liveness work.

## Next step

Create a controlled late-failure migration fixture and record exact source head, migration phase, lock state before release, lock state after failure, source VM state, and second-lock result.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this investigation.
