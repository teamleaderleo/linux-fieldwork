# Virtio config-BAR ioevent rollback

Updated: 2026-08-15

Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact Cloud Hypervisor source: `69d4c0a82ef15b2660906013bd87ae32668e7998`
Owned-fork research branch: `research/ch-pci-bar-r599-ioevent-rollback`
External-contact state: false

## Question

Can the virtio config-BAR ioevent move restore the complete OLD registration state after any ordinary register/unregister failure, instead of leaving a partial mix of OLD and NEW ioevents?

Current source performs the move as two fallible loops:

```text
unregister OLD ioevents one by one
-> register NEW ioevents one by one
```

The 2019 history that introduced OLD unregistration (`3fa5df4161085bd7cfdc1ea1f028e66994a26727`) prepended the unregister loop so old BAR addresses would stop triggering ioevents. It did not define rollback semantics for failures inside either loop.

## Candidate transaction

The experiment factors the two loops through a small `move_ioeventfds()` helper with an injected operation callback.

Primary path:

```text
remove OLD entries, recording each successful removal
-> add NEW entries, recording each successful addition
```

On an OLD-unregister failure:

```text
re-register every OLD entry already removed
```

On a NEW-register failure:

```text
unregister every NEW entry already added
-> re-register every OLD entry removed earlier
```

Rollback attempts all remaining compensating operations and retains the first rollback error. If rollback itself fails, the returned error says so explicitly instead of claiming the old state was restored.

The production closure maps the helper directly onto the existing symmetric VM operations:

```text
Vm::register_ioevent()
Vm::unregister_ioevent()
```

## Deterministic failure matrix

Unit tests use real `EventFd` identities plus a synthetic set of `(fd,address)` registrations. No KVM device is required to classify the transaction logic.

For two OLD and two NEW registrations, the primary-operation test injects failure at every position:

```text
OLD unregister #0
OLD unregister #1
NEW register #0
NEW register #1
```

After every injected primary failure, the final synthetic registry must equal the exact initial OLD registry.

A successful run must contain exactly the NEW registry.

A separate test injects both a primary failure and a compensating rollback failure. The helper must return an error containing `rollback failed`, and the synthetic state must differ from the clean OLD baseline so the caller cannot silently treat the operation as restored.

## Authoritative execution

Workflow:

`PCI BAR ioevent rollback probe v3`

Run/job:

`31898648034` / `95045734088`

Exact workflow head:

`a4eb617eeb39bf3e63d33d8e79d5dd6e39290532`

Artifact:

`9250520905`

Artifact digest:

`sha256:63e803aef7799cff69248d0b75bb3cc54fdd64bd576ac6597091a6192ec3c133`

Candidate diff SHA-256:

`14c0d27c74efb8f881244102fa43ef95834d5eb51ad8282d12c70e90e658de3d`

Results:

```text
ioevent_move_restores_old_for_every_primary_failure  PASS
ioevent_move_success_publishes_only_new              PASS
ioevent_move_reports_rollback_failure                PASS
all device_manager unit tests                        PASS
complete KVM-flavoured vmm test compile --no-run    PASS
stable project-shaped KVM Clippy                     PASS
nightly rustfmt                                      PASS
git diff --check                                     PASS
```

Earlier executions are retained as harness evidence:

- the first semantic run was already green through tests and compilation, then stopped on one test-only absolute-path Clippy lint;
- the v2 workflow failed before product execution because its fixture-cleanup script assumed a specific unit-test import ordering;
- v3 makes the fixture edit against the unit-test module marker and is the authoritative receipt.

## Evidence boundary

This proves the config-BAR ioevent sub-transaction can restore OLD after every **primary** register/unregister failure when compensating operations succeed.

It also proves that rollback itself can fail and must be surfaced.

It does not yet make the complete `AddressManager::move_bar()` transaction failure-atomic. Before ioevents run, the MMIO bus and DeviceTree may already have moved to NEW. Therefore a successful ioevent rollback alone is not enough to release the NEW allocator reservation after a late move error.

That is why the MMIO NEW-first candidate keeps both OLD and NEW reserved on any late error until the wider relocation state is reconciled.

## Composition rule

The independent layers now read:

```text
Bus map:
  route update itself is failure/concurrency safe

MMIO allocator:
  reserve NEW while OLD remains owned
  free OLD only after complete move success

Config-BAR ioevents:
  primary operation failure -> restore OLD registrations
  rollback failure -> report incomplete restoration
```

Next, compose this helper with `MMIO_NEW_FIRST.md` and the clean #677/#678/#679 Bus stack. Keep the late-`move_bar()` caller/config rollback contract as a separate sibling investigation because it owns the cross-step failure state.
