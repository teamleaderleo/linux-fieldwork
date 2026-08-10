# Cloud Hypervisor virtio-pci restore — freshness reconciliation

Updated: 2026-08-11
Owning issue: #563
Parent pass: #559
External-contact state: false; none occurred

## TL;DR

The source boundary used by the investigation remains valid after upstream `main` advanced from `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3` to `915d359f97475b1a39d8561f8db514da9e692d19`.

The five intervening commits touch QCOW2 block code plus `cloud-hypervisor/tests/common/tests_wrappers.rs`; they do **not** touch `virtio-devices/src/transport/pci_device.rs`. A direct read at the refreshed head confirms the restore loop still restores each queue's saved fields and then unconditionally calls `used_idx(...).unwrap()` twice.

Therefore the bounded question, per-queue lifecycle invariant, and proposed three/four-state discriminator in the main investigation remain current. Execution is still the first incomplete gate.

## Exact reconciliation

Compared:

```text
base: a18a2b3f66f7a3cec7f62d07605945beda8eb5d3
head: 915d359f97475b1a39d8561f8db514da9e692d19
relation: head is 5 commits ahead, 0 behind
```

Changed paths in that range:

```text
block/src/formats/qcow/backing.rs
block/src/formats/qcow/engine_sync.rs
block/src/formats/qcow/engine_uring.rs
block/src/formats/qcow/parser.rs
block/src/lib.rs
block/src/test_util.rs
cloud-hypervisor/tests/common/tests_wrappers.rs
```

No changed path intersects the restore owner.

## Refreshed current-source observation

At `915d359f...`, `VirtioPciDevice::new()` still does, for every serialized queue:

```rust
queue.set_size(state.queues[i].size);
queue.set_ready(state.queues[i].ready);
queue.try_set_desc_table_address(...).unwrap();
queue.try_set_avail_ring_address(...).unwrap();
queue.try_set_used_ring_address(...).unwrap();
queue.set_next_avail(queue.used_idx(...).unwrap().0);
queue.set_next_used(queue.used_idx(...).unwrap().0);
```

This means the known zero-ring `used_idx()` read and panic mechanism remains live on the refreshed head.

Canonical issue:

https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8693

Closed, unmerged prior attempt:

https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8702

## Decision impact

No source-level conclusion from the investigation loses:

- the owner remains `virtio-devices/src/transport/pci_device.rs`;
- restore still knows each queue's saved `ready` bit before dereferencing the used ring;
- the reported inactive-queue failure remains reachable in source;
- a device-wide-only guard remains insufficient for the already-mapped mixed-queue state;
- the smallest useful next action remains an executable constructor-level discriminator, not more source widening.

## Evidence boundary

This is a source-identity and current-code reconciliation only. It does not replace the pending runtime/unit baseline. No Cloud Hypervisor build, KVM run, or candidate test was executed in this freshness pass.

## Next safe action

Use `915d359f97475b1a39d8561f8db514da9e692d19` (or a later freshly reconciled descendant) as the carrier base for the compact inactive / active / mixed-queue fixture. Preserve exact base identity before applying a candidate.
