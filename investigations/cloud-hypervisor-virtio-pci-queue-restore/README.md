# Cloud Hypervisor virtio-pci queue-index restore

Updated: 2026-08-11

Upstream issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8693
Closed upstream fix attempt: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8702
Research round: `research/rounds/2026-08-11-cloud-hypervisor-lifecycle-scout/`

Canonical source under investigation: `cloud-hypervisor/cloud-hypervisor` `main`
Exact source head: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
Primary owner: `virtio-devices/src/transport/pci_device.rs`, `VirtioPciDevice::new()` restore path
Current state: **source-confirmed candidate; execution pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Snapshot restore rebuilds each virtqueue's saved `ready` bit and ring addresses, then unconditionally reads `used_idx()` from guest memory. A saved non-ready queue can have zero ring addresses, so the read targets guest address `0x2` and the current `.unwrap()` panics. Later activation already skips queues whose `ready` bit is false.

The bounded question is therefore:

> Which saved-state predicate should gate queue-index restoration so restore reads only the queues that can participate in resumed activation?

The leading hypothesis is `device_activated && queue.ready()`. It requires execution before selection.

## Explain like I'm five

A virtio device can remember several queues. Some queues are ready to use; some are asleep.

Restore currently does this to every queue:

```text
put the queue back
then read a number from the queue's memory
```

For an asleep queue, there may be no queue memory address at all. Its saved address is zero. Reading the queue number then means reading near address zero, and Cloud Hypervisor crashes.

A few lines later, the code that starts the device already says:

```text
if this queue is asleep, skip it
```

The investigation asks whether restore should use that same lifecycle decision before reading queue memory.

## Why care

A default VM can contain a virtio device the guest never uses. The upstream reproducer uses the default virtio-rng device when the guest never opens `/dev/hwrng`. A snapshot of that valid VM state can therefore become unrestorable through a VMM panic.

This also has a multiqueue consequence: an activated device can have only some queues configured. A device-level check alone may still touch an inactive queue.

## Current-main source observation

At exact head `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`, the restore loop does the following for every queue:

```rust
queue.set_size(state.queues[i].size);
queue.set_ready(state.queues[i].ready);
queue.try_set_desc_table_address(...).unwrap();
queue.try_set_avail_ring_address(...).unwrap();
queue.try_set_used_ring_address(...).unwrap();
queue.set_next_avail(queue.used_idx(...).unwrap().0);
queue.set_next_used(queue.used_idx(...).unwrap().0);
```

The important property is sequencing, not the duplicated `used_idx()` call: the saved readiness state is already known before the guest-memory dereference.

Later, `prepare_activator()` does:

```rust
for (queue_index, queue) in self.queues.iter().enumerate() {
    if !queue.ready() {
        continue;
    }

    if !queue.is_valid(...) {
        ...
        continue;
    }
    ...
}
```

So activation treats `ready` as the queue participation boundary while restore currently does not.

## Upstream reproducer and failure

The upstream issue reports:

1. boot a VM with the default virtio-rng;
2. leave `/dev/hwrng` unused;
3. pause and snapshot;
4. restore the snapshot.

Reported failure:

```text
called `Result::unwrap()` on an `Err` value:
GuestMemory(InvalidGuestAddress(GuestAddress(2)))
```

The saved inactive queue has zero descriptor, available-ring, and used-ring addresses. `used_idx()` reads the used-ring `idx` field two bytes after the ring base, hence `0 + 2`.

Evidence type: upstream target-native report. This Fieldwork round has not reproduced it locally yet.

## Review evidence from the closed fix attempt

The closed PR proposed a one-file fix around the restore loop and regression tests. Maintainer review explicitly confirmed that the bug was genuine and described the needed fix as simple, while rejecting the submitted implementation package as excessive.

That review gives two useful constraints:

- the defect itself is accepted as real;
- proportionality matters strongly for the next carrier.

Do not inherit the closed PR as a canonical implementation. Re-derive the predicate from current source and prove it with the smallest discriminator.

## State matrix to execute

The first fixture should make both device state and queue state independently visible:

| case | `device_activated` | queue 0 `ready` | queue 1 `ready` | expected memory reads |
|---|---:|---:|---:|---|
| A | false | false | — | none |
| B | false | true | — | determine contract |
| C | true | true | false | queue 0 only |
| D | true | true | true | both queues |

Case C is the primary discriminator. It defeats a guard that only checks `device_activated`.

The fixture should map guest RAM away from address zero so any accidental low-address access fails visibly.

For ready queues, write a known used index into the used ring and assert that both `next_avail` and `next_used` restore to that value.

For skipped queues, assert that restore succeeds and their next indexes remain at the expected initial value.

## Candidate predicates

### Candidate A — lifecycle predicate

```text
state.device_activated && queue.ready()
```

Why it leads:

- device restoration later auto-activates only a previously activated device;
- `prepare_activator()` consumes only ready queues;
- the decision is expressed in saved lifecycle state instead of inferred from an address sentinel.

Question still open: whether a valid saved state can have `device_activated = false` and `queue.ready() = true`, and what restore should do with that state.

### Candidate B — address sentinel

```text
state.device_activated && state.queues[i].used_ring != 0
```

This was used by the closed PR.

It avoids the reported zero-address failure and handles a partially configured queue whose `used_ring` is zero. Its weakness is semantic: it infers participation from one address field even though the snapshot already stores the queue's readiness bit and activation later uses that bit.

Keep it alive until the fixture proves whether valid queue states can separate readiness from address presence.

### Candidate C — unconditional read, propagate the error

Replace `.unwrap()` with `?` / mapped error but keep reading every queue.

This converts the panic into a restore failure, but an ordinary inactive queue would still make a valid snapshot unrestorable. That conflicts with the upstream report's intended successful restore and therefore currently looks like a negative control, not the fix.

## Adjacent contexts

### Partially configured multiqueue device

Highest-value adjacent case. Device activation can be true while only a subset of queues are ready. Any device-wide-only predicate loses here.

### Ready-but-invalid queue

`prepare_activator()` checks `queue.is_valid()` after readiness and skips invalid queues. Decide whether restore should similarly avoid dereferencing an invalid ready queue or fail the snapshot earlier. This can change whether the candidate guard uses readiness alone or a stronger validity predicate.

Do not broaden into general snapshot validation unless this state is constructible through supported runtime behavior or a real compatibility contract requires accepting it.

### Queue reset / stale addresses

Check whether a queue can become non-ready while retaining nonzero saved ring addresses. If yes, `used_ring != 0` is demonstrably weaker than the saved readiness bit. If no supported state can do this, record that evidence and keep the smaller predicate decision explicit.

### Other transports

Current repository search found the restore-time `used_idx(memory...)` pattern in this virtio-pci path. A broad transport rewrite has no evidence yet. Reopen only if an adjacent transport owns the same failure contract.

## Negative controls

A useful candidate run should include failures that distinguish tempting shortcuts:

1. **Device-only guard loses:** activated device + queue 0 ready + queue 1 non-ready.
2. **Error-propagation-only loses:** inactive zero-address queue should restore successfully rather than return an error.
3. **No-read proof:** guest memory starts away from zero, so accidental access through an inactive ring fails instead of silently reading mapped low memory.
4. **Active path preserved:** ready queue with known used index restores both runtime indexes exactly.

## Evidence boundary

Established in this investigation:

- current-main source still performs the unconditional read;
- current-main source restores the `ready` bit before that read;
- current-main activation skips non-ready queues;
- upstream issue supplies a concrete target-native panic report;
- maintainer review independently confirms the bug is genuine;
- closed PR demonstrates one attempted fix direction and an overgrown packaging failure.

Still unproven here:

- local reproduction on exact head `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`;
- the full valid-state relation among `device_activated`, `ready`, and ring addresses;
- the selected predicate;
- regression behavior on x86_64/aarch64;
- any current CI result.

## Stop condition

Stop source widening and select a candidate when:

1. the four-state fixture runs on the exact source head or a freshly reconciled successor;
2. the partial-multiqueue case establishes the required per-queue boundary;
3. queue-reset/validity review either confirms or defeats `queue.ready()` as the semantic predicate;
4. the active path remains byte-for-byte equivalent in observed runtime indexes;
5. the candidate fits in the restore loop plus compact regression proof.

If those conditions select a simple guard, move to a clean candidate carrier. Do not add helpers, generalized snapshot validators, or unrelated unwrap cleanup without a new discriminator.

## Reopening trigger

Reopen wider design work if any of these occur:

- a supported queue-reset sequence produces `ready = false` with ring state that must still have indexes restored;
- a valid snapshot can contain `device_activated = false, ready = true` and requires a different action;
- another transport shows the same restore ownership defect;
- current upstream main changes queue snapshot or activation semantics.

## Next safe action

Build and execute the compact four-state unit fixture against the current exact upstream head. Preserve baseline failure, passing active control, partial-multiqueue discriminator, and exact head before changing product code.
