# MMIO BAR reserve-NEW-first candidate

Updated: 2026-08-15

Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact Cloud Hypervisor source: `69d4c0a82ef15b2660906013bd87ae32668e7998`
Owned-fork research branch: `research/ch-pci-bar-r599-new-first`
External-contact state: false

## The simplification

Current MMIO BAR relocation frees OLD before allocating NEW:

```text
free OLD
-> allocate NEW
-> update bus / metadata / KVM / device state
```

That publication order is the source of the address-reuse race: another allocator client can receive OLD before old-address ioeventfd or memslot state is gone.

The deeper source pass shows that MMIO does not need this free-first step.

`PciConfiguration::add_pci_bar()` requires BAR size to be a power of two. `AddressManager::move_bar()` asks the selected `AddressAllocator` to allocate the new MMIO address with alignment equal to the BAR length:

```text
allocate(Some(new_base), len, Some(len))
```

Therefore a successful NEW target is `len`-aligned. The existing OLD allocation was created under the same BAR-size alignment. Equal-size aligned ranges are either identical or disjoint. Unchanged BAR writes are filtered by PCI configuration before relocation, while partially overlapping unaligned targets are rejected by allocation.

So the stronger local lifecycle is simply:

```text
OLD remains allocator-owned
-> reserve NEW
-> update bus
-> update metadata
-> retire/install ioevent or memslot state
-> update device-local BAR state
-> success: free OLD last
```

No allocator mutex needs to remain held across KVM or device calls.

## Candidate representation

The experiment uses a small `MmioBarRelocationReservation` owned by `AddressManager::move_bar()`.

Creation reserves NEW while OLD remains reserved. `commit()` frees OLD only after the complete relocation succeeds. Dropping the reservation after a later error performs no allocator release, so both OLD and NEW remain unavailable to unrelated allocator clients.

That failure direction is intentionally conservative:

```text
success      -> NEW reserved, OLD free
late failure -> OLD reserved, NEW reserved
early NEW rejection -> OLD reserved, NEW absent
```

This is an address-reuse safety contract, not yet a complete retry/recovery policy.

## Planned / active executable controls

The exact-main owned-fork run exercises:

1. success keeps OLD and NEW reserved during relocation and frees OLD only on commit;
2. dropping after a simulated late error leaves both ranges quarantined;
3. a partially overlapping target such as `OLD + len/2` is rejected without releasing OLD;
4. the reservation itself does not hold the allocator mutex;
5. all existing `device_manager::unit_tests` remain green;
6. the complete KVM-flavoured `vmm` test suite compiles;
7. project quality and formatting gates run on the materialized candidate.

Run identity and final result should be appended after execution stabilizes.

## Why this is smaller than the lease-guard variant

The earlier mutex-held experiment used the allocator lock as the publication lease. That works mechanically, but it lengthens a lock chain through bus, DeviceTree, KVM, and device callbacks.

NEW-first keeps the actual allocator reservations as the lease instead:

```text
reservation state, not mutex duration, prevents reuse
```

That makes the invariant visible in the allocator map and keeps ordinary allocation concurrency available for unrelated addresses.

## Remaining correctness question

A late error leaves both addresses reserved. This safely prevents a reuse collision, but the current allocator has no reservation identity and the caller currently restores the BAR config register to OLD. A subsequent retry may therefore need an explicit way to recognize or clean the quarantined NEW reservation.

Do not hide this as a leak. It is the next discriminator:

> can the existing relocation path deterministically unwind NEW-side state and free NEW on each failure class, or does `AddressManager` need a small explicit pending-relocation record/token?

The first real failure class to execute should be virtio config-BAR ioevent relocation:

```text
OLD ioevent unregister failure
NEW ioevent register failure after OLD unregister succeeds
```

At each error boundary, assert which external address state survives and which allocator reservations must remain.

## Scope boundary

This candidate is currently MMIO-only. PIO relocation uses different allocator/alignment semantics and must be audited independently.

The generic `vm-device::Bus` failure/concurrency/arithmetic repairs (#677/#678/#679) also remain separately evidenced. If this MMIO ordering stabilizes, compose it with the clean Bus stack before any upstream packet.
