# Virtio queue readiness contract notes

Updated: 2026-08-11

Companion investigation: `README.md`
Upstream source head reviewed: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`

## Question

Does the virtio protocol give us a semantic queue-participation signal that is stronger than testing whether a saved used-ring address happens to be nonzero?

## Cloud Hypervisor maps PCI `queue_enable` directly to queue readiness

Current source:

`virtio-devices/src/transport/pci_common_config.rs`

Pinned source:
https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/virtio-devices/src/transport/pci_common_config.rs

The file documents PCI common-config offset `0x1c` as:

```text
le16 queue_enable; // 0x1C // read-write (Ready)
```

Read behavior returns:

```rust
0x1c => u16::from(self.with_queue(queues, |q| q.ready()).unwrap_or(false))
```

Write behavior derives readiness from `value == 1` and calls `q.set_ready(ready)`.

So the `QueueState.ready` bit saved/restored in `pci_device.rs` is not an incidental local flag. It is Cloud Hypervisor's representation of the virtio-pci queue-enable state.

## Virtio 1.3 PCI contract

Primary specification:
https://docs.oasis-open.org/virtio/virtio/v1.3/virtio-v1.3.html

Relevant common-configuration semantics:

- `queue_enable` lets the driver selectively enable or disable device execution for one virtqueue: `1` enabled, `0` disabled.
- queue configuration fields are configured before the queue is enabled.
- device reset presents `queue_enable = 0`.
- when per-queue reset is supported and completes, the device presents both `queue_reset = 0` and `queue_enable = 0`.

The general virtqueue-reset contract says that after reset the device must reset queue state, including available and used state, and the driver may release resources associated with that queue.

This strengthens the lifecycle interpretation:

```text
queue ready / queue_enable == 1
        ↓
queue participates in device execution

queue ready / queue_enable == 0
        ↓
queue is outside current execution
```

A nonzero used-ring address is configuration data. It is not the protocol's enable/disable signal.

## Implication for the restore candidate

Current restore does this in order:

```text
restore QueueState.ready
restore ring addresses
read used_idx unconditionally
```

Current activation later does this:

```text
if !queue.ready(): skip queue
```

Given the PCI mapping and spec, the leading candidate becomes stronger:

```text
device was activated && queue is ready
```

as the condition for reading a queue runtime index during resumed activation.

The address-sentinel candidate:

```text
device was activated && used_ring != 0
```

still prevents the reported address-0 panic, but it encodes participation through a data address rather than through the saved queue-enable state.

## Important evidence limit: per-queue reset reachability

The Virtio 1.3 spec provides a powerful counterexample in principle: after a negotiated queue reset, queue enable is cleared and the driver may release queue resources. That is exactly the sort of lifecycle where a stale/nonzero address must not define whether the queue is active.

A repository search at the inspected Cloud Hypervisor head did not find `VIRTIO_F_RING_RESET` support. Therefore this record does **not** claim that a guest can currently produce a per-queue-reset snapshot through Cloud Hypervisor.

Use the reset contract as protocol evidence for why readiness owns participation, and as a reopening test if ring-reset support lands later.

## Current discriminator after the spec pass

The most valuable current fixture remains an activated multiqueue device with:

- queue 0: `ready = true`, valid used ring with known index;
- queue 1: `ready = false`, no usable ring memory.

Expected behavior under the protocol-aligned hypothesis:

- queue 0 index is read/restored;
- queue 1 guest memory is untouched;
- device restore succeeds.

A device-level-only guard loses this fixture.

An address-sentinel guard may pass it, so a second discriminator should look for a supported current state where `ready = false` and ring addresses remain nonzero. If no such current state is reachable, record that limit instead of inventing one.

## Stop rule update

Selection can proceed once current-main execution establishes:

1. non-ready queues require no runtime-index read;
2. ready queues still restore their index;
3. partially configured multiqueue devices behave per queue;
4. no supported current lifecycle requires index restoration when `ready = false`.

At that point prefer the predicate that names the lifecycle contract directly, provided it stays a tiny local change and the regression test remains compact.
