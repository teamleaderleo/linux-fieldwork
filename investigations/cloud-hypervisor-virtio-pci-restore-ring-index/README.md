# Cloud Hypervisor — virtio-pci restore ring-index lifecycle

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #563
Parent research pass: #559
Canonical Cloud Hypervisor source: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
External-contact state: `false; none occurred`

## TL;DR

Cloud Hypervisor currently restores the next available/used queue indexes for **every** serialized virtio-pci queue by reading `used_idx()` from guest memory, even when that queue was not ready and its ring addresses are zero. That is the direct cause of upstream issue #8693 for a wholly inactive device.

A bounded adjacent-state pass shows the lifecycle invariant is more precise than the issue title: it is **per queue, not per device**. Cloud Hypervisor considers a device activatable when any queue is ready, and its activator deliberately skips unready queues. An activated multi-queue device can therefore still serialize an unready zero-address queue. A device-wide-only guard would leave the same address-2 failure mechanism reachable.

The next safe action is a tiny three-state unit fixture on exact current main: inactive queue, active valid queue, and activated device with one ready plus one unready queue. Only after that baseline should a minimal transport-local candidate be tested.

## Explain like I'm five

A virtio device can have several little work rings. Some rings may be switched on while others are still unused.

Cloud Hypervisor saves all of them. During restore it currently asks every ring, including unused ones, “what job number were you on?” An unused ring has address zero, so that question turns into a read near memory address `2` and can crash the VMM.

The fix must ask only rings that were actually ready, not assume that if the whole device was active then every ring was active.

Literal example:

`queue0 ready at valid address + queue1 not ready at address 0 -> snapshot -> restore currently reads both -> queue1 read targets address 2`

## Why care

This is a VM lifecycle robustness defect in the restore constructor. A snapshot that contains an unused virtio queue can panic the VMM instead of restoring or returning an ordinary error.

The upstream report demonstrates the simplest form with the default virtio-rng device. Source review adds a second reachable shape: a multi-queue transport with at least one active queue and at least one unready queue.

## Current state

- State: `SCOPING`
- Exact working head: upstream `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
- Latest authoritative gate or artifact: current-main source review plus upstream issue/rejected-PR history
- First incomplete step: execute the three-state constructor-level baseline fixture
- Cleanup state: no runtime resources created
- Next safe action: materialize a controlled fork carrier and run baseline/candidate unit tests on the exact reviewed head
- External-contact state: false; no upstream issue, comment, review, PR, or email created by Fieldwork

## Intent and precedent

Canonical upstream issue:

- https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8693

Prior upstream pull request:

- https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8702

The issue contains a real snapshot from an unused virtio-rng device with:

```text
device_activated=false
ready=false
desc_table=0
avail_ring=0
used_ring=0
```

and reports the restore panic as `InvalidGuestAddress(GuestAddress(2))` from `used_idx()`.

The prior PR was closed unmerged. Maintainer review nevertheless explicitly says the bug is genuine, the repair deserves to exist, and the core change should be a simple conditional; hoisting the duplicate `used_idx()` call was also considered useful. The review strongly argues for a small successor rather than a broad validation rewrite.

## Question

What is the smallest restore-time condition that prevents ring-index reads for queues that did not participate in the saved device activation, while preserving correct index recovery for active queues and returning ordinary errors for genuinely invalid active queue memory?

## Source

- Project: Cloud Hypervisor
- Requested revision: current `main` sampled 2026-08-11
- Resolved commit: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
- Candidate source commit: none yet
- Local source path: none available in this pass
- Import metadata: no current imported Cloud Hypervisor tree found in Fieldwork during this pass

Primary owner:

- `virtio-devices/src/transport/pci_device.rs`

Current restore behavior:

1. deserialize `VirtioPciDeviceState`;
2. iterate every saved queue;
3. restore size, `ready`, and ring addresses;
4. unconditionally read `queue.used_idx(...)` twice with `unwrap()`;
5. later recreate the transport and activate only if the saved device and driver state permit it.

Current snapshot behavior serializes every queue's:

- `max_size`;
- `size`;
- `ready`;
- descriptor table address;
- available-ring address;
- used-ring address.

## Source-level adjacent-state result

The upstream issue frames the bug as an inactive-device failure, but current source makes a stronger distinction necessary.

`needs_activation()` is true when:

```text
!device_activated && driver_ready && any(queue.ready())
```

`prepare_activator()` then walks all queues and explicitly skips every queue whose `ready()` is false. It activates only the ready, valid subset.

Therefore this state is structurally permitted by the transport:

```text
device_activated = true
queue0.ready = true,  queue0.used_ring = valid
queue1.ready = false, queue1.used_ring = 0
```

Snapshot state records both queues. Current restore then reads `used_idx()` from queue1 anyway.

### Consequence for candidate selection

A predicate based only on `state.device_activated` is insufficient.

The operation owner is the individual serialized queue. The strongest lifecycle signal already present in the snapshot is that queue's `ready` bit. A configured used-ring address can be used as a defensive discriminator, but address presence alone is not the lifecycle contract.

For a saved queue that claims to be ready, an invalid/nonresident used ring should not be silently treated as unused. That condition should remain distinguishable and return through the existing constructor error boundary rather than panic.

## Baseline behavior

At exact source `a18a2b3f...`, the restore loop does this for every queue:

```text
set saved queue size
set saved ready bit
set saved ring addresses
read used_idx from guest memory -> unwrap
read used_idx from guest memory again -> unwrap
```

For an unused queue whose used-ring base is zero, `used_idx()` reaches the used-ring `idx` field at offset two and can attempt a guest-memory read at address `0x2`.

Upstream #8693 provides runtime evidence for the inactive-device form. Fieldwork has not yet executed the mixed-queue form; that result is currently a source-derived reachability claim based on the activation and snapshot contracts above.

## Hypothesis or candidate

### Preferred behavior

For each serialized queue:

- restore static queue configuration fields;
- restore ring progress only when that queue's saved lifecycle state says it was active/ready;
- perform `used_idx()` once and apply the same value to both `next_avail` and `next_used`;
- propagate a real used-ring memory-read failure for a saved ready queue through `VirtioPciDeviceError::CreateVirtioPciDevice` rather than `unwrap()`.

### Candidate boundary

Keep product scope inside the existing restore loop in `virtio-devices/src/transport/pci_device.rs` unless execution proves another owner is required.

Do not:

- add device-specific rng logic;
- turn the change into generic snapshot validation;
- add explanatory source comments that only narrate the historical bug;
- alter queue activation policy;
- alter snapshot format;
- contact upstream without explicit human authorization.

## Reproduction / first probe

The preferred probe is constructor-level and requires guest RAM to start well above zero so accidental low-memory reads cannot pass by reading unrelated bytes.

### Case 1 — inactive queue baseline

```text
device_activated=false
queue0.ready=false
queue0.desc_table=0
queue0.avail_ring=0
queue0.used_ring=0
```

Baseline distinguishing result: restore errors/panics through the address-2 `used_idx()` read.

Candidate result: restore succeeds without reading the ring; next indexes remain zero.

### Case 2 — active positive control

```text
device_activated=true
queue0.ready=true
queue0 ring addresses inside guest RAM
used_ring.idx = 7
```

Candidate must preserve existing behavior:

```text
next_avail = 7
next_used = 7
```

### Case 3 — activated mixed-queue discriminator

```text
device_activated=true
queue0.ready=true, valid used ring, idx=7
queue1.ready=false, zero ring addresses
```

This case can make a device-wide-only guard lose.

Expected candidate result:

```text
queue0 next_avail/next_used = 7
queue1 next_avail/next_used = 0
no read from address 2
```

### Case 4 — malformed ready queue

```text
device_activated=true
queue0.ready=true
queue0.used_ring points outside guest RAM
```

Desired result if kept local and idiomatic: constructor returns an ordinary `CreateVirtioPciDevice` error. It must not panic and must not silently classify the ready queue as inactive.

## Results

### Established by source/history review

- The exact current restore loop still unconditionally reads each queue's used index twice.
- Snapshot state carries queue readiness independently for every queue.
- Device activation is satisfied by any ready queue.
- The activator skips unready queues rather than requiring all queues to be ready.
- Therefore device activation does not imply all serialized queues have valid ring addresses.
- Upstream runtime evidence already demonstrates the zero-address panic for an entirely inactive virtio-rng device.
- The prior proposed fix was not merged; current main retains the defect.

### Not yet executed

- constructor-level inactive baseline on current main;
- mixed-queue baseline;
- positive active control;
- malformed-ready error propagation;
- candidate implementation;
- rustfmt, Clippy, crate tests, architecture builds, or KVM runtime restore.

## Interpretation

The headline defect is not best described as "inactive virtio-rng restore". The reusable invariant is:

> Ring progress belongs to a saved **ready queue**, not to every queue owned by a device and not merely to a device-wide activation bit.

This matters because a minimal patch that checks only `device_activated` can appear to fix #8693 while leaving an adjacent queue-level form reachable.

The current evidence does not yet prove which exact Rust predicate produces the best accepted patch. It does establish what the predicate must distinguish.

## Evidence boundary

This investigation currently contains source and upstream-history evidence only. No Fieldwork runtime reproduced the panic in this pass, and no current Cloud Hypervisor source tree was available locally for execution. The mixed-queue case is source-derived reachability, not yet a fresh observed panic.

No claim is made about virtio-mmio or other transport implementations. No claim is made about arbitrary corrupted snapshot inputs beyond the focused ready/unready queue distinction.

## Reopen / widen triggers

Widen beyond the restore loop only if one of these occurs:

- a saved unready queue legitimately needs nonzero next-index recovery;
- a ready queue can legitimately have no readable used ring at this lifecycle point;
- another transport serializes/restores the same state through a different owner and shows the same failure;
- the minimal local error propagation cannot be expressed through the existing constructor error type;
- runtime proves the mixed-queue state cannot actually be snapshotted despite the source activation model.

## Next step

Create a controlled fork carrier at exact current main, add only the smallest fixture needed to make cases 1-3 distinguishable, run baseline, then apply the minimal per-queue candidate. Add case 4 only if it stays local and does not balloon the patch.

A reviewer should ultimately be choosing between exact candidate predicates with the mixed-queue test as the discriminator, not deciding whether the reported bug exists.

## Authority

No upstream contact is authorized by this investigation. No Cloud Hypervisor issue, comment, review, pull request, email, or patch submission was created by Fieldwork during this pass. Existing upstream #8693 and #8702 are external evidence only.
