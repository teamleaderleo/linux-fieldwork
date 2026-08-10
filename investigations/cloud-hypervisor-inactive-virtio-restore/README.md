# Cloud Hypervisor inactive virtio-pci restore panic

## TL;DR

Current Cloud Hypervisor `main` still unconditionally reads the used-ring index for every saved virtio-pci queue during restore. An unused queue is saved with `ready=false` and zero ring addresses, so `used_idx()` reads guest address `0x2` and the current `.unwrap()` can panic the VMM.

The smallest durable invariant is queue-level readiness. Cloud Hypervisor activates a virtio device when any queue is ready and passes only ready+valid queues into device activation, so `device_activated=true` cannot establish that every queue has usable ring addresses. Virtio 1.3 also defines `queue_enable` per queue and requires queue fields to be configured before enabling the queue.

A compact candidate should therefore restore ring indexes only for enabled/ready queues, read `used_idx` once, propagate an invalid saved ring as a restore error, and cover the partially configured multi-queue case that a device-level guard can miss.

Tracking issue: [linux-fieldwork #558](https://github.com/teamleaderleo/linux-fieldwork/issues/558)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8693  
Closed upstream attempt: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8702

## Explain like I'm five

A virtio device can have several little work queues. Some guests only turn on the queues they need.

Cloud Hypervisor saves whether each queue was turned on. During restore, current code still asks every queue — including an untouched one whose addresses are all zero — “what was your last used entry?” The untouched queue sends that read toward address `0x2`, and the VMM panics.

The saved queue already tells us whether it was enabled. Read the ring only for queues that were enabled.

## Why care

The default virtio-rng can stay inactive when a guest never opens `/dev/hwrng`, so an ordinary VM snapshot can contain an untouched virtio-pci queue. A restore-time panic turns a valid saved VM state into process failure.

The multi-queue edge is equally useful. Device activation in current code is device-wide once any queue is ready, while queue setup remains per queue. A repair based only on `device_activated` can still reach a zero ring on a sibling queue.

## Current state

- State: `SCOPING / SOURCE MECHANISM PROVEN`
- Current upstream head inspected: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
- Current primary blob: `virtio-devices/src/transport/pci_device.rs` at `0c1593f53f624c0e23845c3b08339f6ab57e6355`
- Historical origin inspected: `646d33fea3b6c320bc12c404efa83907976518cb`
- Candidate source commit: none
- Latest distinguishing result: current activation is `any(queue.ready())`, and activation passes only ready+valid queues; per-device activation therefore does not imply per-queue ring validity
- Cleanup state: no runtime state
- Next safe action: build a minimal queue-ready restore guard with compact tests
- External-contact state: `false; none occurred`

## Question

What is the smallest restore change that avoids reading used-ring state from queues the guest never enabled, preserves enabled queue indexes, handles partially configured multi-queue devices, and converts malformed saved ring addresses into a normal restore error?

## Source

Project: `cloud-hypervisor/cloud-hypervisor`

Exact current head inspected:
`a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`

Primary path:
`virtio-devices/src/transport/pci_device.rs`

Current blob:
`0c1593f53f624c0e23845c3b08339f6ab57e6355`

## Canonical failure

Upstream issue 8693 reports a snapshot whose inactive virtio-rng transport contains:

```text
device_activated = false
queue.ready       = false
desc_table        = 0
avail_ring        = 0
used_ring         = 0
```

Restore reaches:

```rust
queue
    .used_idx(memory.memory().deref(), Ordering::Acquire)
    .unwrap()
```

The split used-ring index sits two bytes after the used-ring base, so a zero `used_ring` turns into a guest-memory read at `0x2`. The report records `InvalidGuestAddress(GuestAddress(2))` and a VMM-thread panic.

## Current restore path

For every queue in the snapshot, `VirtioPciDevice::new()` currently:

1. restores size;
2. restores `ready`;
3. restores descriptor, available-ring, and used-ring addresses;
4. calls `used_idx()`;
5. unwraps the result;
6. copies that same used index into both `next_avail` and `next_used`;
7. calls `used_idx()` a second time for the second assignment.

The read happens for every queue regardless of `ready`.

## The useful invariant is per queue

Current activation code says:

```text
needs activation when:
    device is not already activated
    AND driver is ready
    AND any queue is ready
```

`prepare_activator()` then iterates all queues and skips each queue that is not ready. It also skips ready queues that fail `queue.is_valid(...)`.

Therefore this state is coherent with current source:

```text
device_activated = true
queue 0.ready     = true   -> valid rings
queue 1.ready     = false  -> zero rings
```

A repair keyed only to `device_activated` can still read queue 1 at address `0x2`.

## Virtio contract

Virtio 1.3 defines PCI `queue_enable` as the per-queue switch allowing the device to execute requests from that virtqueue. The driver requirements say the other virtqueue fields must be configured before the driver enables the queue.

Reference:
https://docs.oasis-open.org/virtio/virtio/v1.3/virtio-v1.3.html

That lines up directly with Cloud Hypervisor's saved `QueueState.ready` field.

## History

Commit:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/646d33fea3b6c320bc12c404efa83907976518cb

In 2020, Cloud Hypervisor stopped replacing the full queue object from the snapshot and began copying selected queue fields explicitly. That change retained an unconditional read of the used index from guest memory after restoring queue addresses.

The current bug is therefore old restore behavior exposed by a valid inactive-queue snapshot.

## Closed upstream attempt

Upstream PR 8702 proposed:

- skipping ring-index restore for inactive/zero-ring queues;
- reading `used_idx()` once;
- returning `CreateVirtioPciDevice` on read failure;
- adding regression tests.

The PR was closed unmerged after review. The maintainer explicitly agreed the bug is genuine and described the desired repair as a simple conditional plus hoisting the duplicated `used_idx` read.

That review is useful design evidence while leaving the exact queue-level condition worth proving locally.

## Candidate

Leading minimal candidate:

```rust
if queue.ready() {
    let used_idx = queue
        .used_idx(memory.memory().deref(), Ordering::Acquire)
        .map_err(|e| {
            VirtioPciDeviceError::CreateVirtioPciDevice(anyhow!(
                "Failed to read used index for queue {i}: {e}"
            ))
        })?
        .0;

    queue.set_next_avail(used_idx);
    queue.set_next_used(used_idx);
}
```

Keep the source candidate boring. A separate validation check may be preferable if `queue.ready()` can be true with malformed ring addresses; in that case the read must return a normal restore error rather than silently skipping the queue.

## Distinguishing tests

### 1. Fully inactive queue

```text
device_activated = false
queue.ready       = false
ring addresses    = 0
```

Expected: restore succeeds and both next indexes remain their reset value.

### 2. Partially configured multi-queue device

```text
device_activated = true
queue 0.ready     = true  + valid rings
queue 1.ready     = false + zero rings
```

Expected: queue 0 index is restored; queue 1 is skipped. This kills a device-level-only guard.

### 3. Enabled valid queue

Write a known used index into guest memory and restore a ready queue.

Expected: both `next_avail` and `next_used` equal that known index.

### 4. Enabled malformed queue

```text
queue.ready    = true
used_ring      = unmapped address
```

Expected: `VirtioPciDevice::new()` returns `CreateVirtioPciDevice`; the process does not panic.

### 5. Reset state

Current device-reset code resets queue readiness. Snapshot/restore after a reset should follow the inactive-queue path.

## Negative controls

- Leave ring-index restoration enabled for a ready valid queue; skipping all reads would lose migration progress.
- Place guest RAM away from address zero in unit tests so an accidental low-address read fails loudly instead of finding unrelated mapped bytes.
- Use a multi-queue fixture so `device_activated` cannot accidentally stand in for queue readiness.

## Candidate gates

1. exact current-main source identity;
2. source diff limited to restore path and compact tests;
3. inactive queue test;
4. partial multi-queue test;
5. active queue index-preservation test;
6. malformed ready-queue error-propagation test;
7. immediate clean rerun;
8. `cargo fmt --all -- --check`;
9. focused `virtio-devices` unit tests;
10. broader project gate appropriate to the touched crate before promotion.

## Evidence boundary

- Canonical issue 8693 provides the real reported panic and an AArch64 patched runtime result from its reporter.
- Current upstream source still contains the unconditional double `used_idx(...).unwrap()` at the inspected head.
- Current activation source proves a device may activate based on any ready queue while individual unready queues are skipped.
- Virtio 1.3 supplies the per-queue enable contract.
- Linux Fieldwork has not produced candidate source bytes or executed the restore scenario in this pass.
- Closed upstream PR 8702 is design/review context, not an accepted patch.

## Next step

Create one minimal owned-fork candidate from current canonical `main` around the queue-ready guard and error propagation. Run the four distinguishing unit cases first. Only then spend runtime effort on a full snapshot/restore reproducer.

## Authority

No upstream issue, pull request, comment, review, or other interaction was created or modified by this Fieldwork pass.