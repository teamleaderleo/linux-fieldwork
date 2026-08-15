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
success             -> NEW reserved, OLD free
late failure         -> OLD reserved, NEW reserved
early NEW rejection  -> OLD reserved, NEW absent
```

This is an address-reuse safety contract, not yet a complete retry/recovery policy.

## Authoritative hosted execution

Authoritative validation:

- workflow: `PCI BAR new-first hosted validation v3`
- run: `31898220133`
- job: `95044720650`
- branch head used to materialize the candidate: `29fb341274047813ad1bd0bf00720aa76e088886`
- artifact: `9250420377`
- artifact digest: `sha256:0689e4ecb3332b3a002785ae5b7efe238858121da5715ac9451c17fbfb92d710`

The run rechecked that `vmm/src/device_manager.rs` and `pci/src/configuration.rs` were pristine against exact upstream `69d4c0...` before materialization.

### Focused lifecycle controls

All four NEW-first controls passed under Rust `1.89.0`:

```text
mmio_bar_reservation_success_releases_old_last                    PASS
mmio_bar_reservation_error_quarantines_old_and_new                PASS
mmio_bar_reservation_rejects_partial_overlap_without_releasing_old PASS
mmio_bar_reservation_does_not_hold_allocator_mutex                PASS
```

All `device_manager::unit_tests` passed: **7 passed, 0 failed**.

The complete KVM-flavoured `vmm` test suite compiled successfully with the project MSRV using `cargo test --no-run`.

### Project-shaped quality gates

Cloud Hypervisor quality CI uses stable/beta Clippy rather than the MSRV compiler's Clippy. The authoritative run therefore used the repository's stable KVM shape:

```text
cargo +stable clippy --locked --all --all-targets \
  --no-default-features --tests --examples --features kvm -- -D warnings
```

Result: **PASS**.

Nightly rustfmt and `git diff --check` also passed.

Earlier red hosted runs are retained as harness/toolchain evidence:

- a generic runner cannot execute all KVM-backed `vmm` tests because `/dev/kvm` is unavailable;
- Rust 1.89 Clippy reports an existing unfulfilled `collapsible_match` expectation that stable CI does not;
- test-only fixture style warnings were corrected without changing candidate product semantics.

## History check

Two recent history points make NEW-first easier to justify:

- `15d1f1d7fdd7b0698ace412c2398fbc3d515bcba` (February 2026) consolidated multiple allocator lock acquisitions around the already-existing `free OLD -> allocate NEW` sequence. It documents allocator-operation serialization, not an MMIO requirement to release OLD first.
- `e65cca3bf55ea51c34a1cb9c7a23ed9f59e15d88` (May 2026) added OLD re-allocation when NEW allocation fails because free-first could otherwise leave allocator state inconsistent with the bus.

NEW-first removes the MMIO premise that created the May rollback path: OLD never leaves allocator ownership before NEW is known reservable.

## Why this is smaller than the lease-guard variant

The earlier mutex-held experiment used the allocator lock as the publication lease. That works mechanically, but it lengthens a lock chain through bus, DeviceTree, KVM, and device callbacks.

NEW-first keeps the actual allocator reservations as the lease instead:

```text
reservation state, not mutex duration, prevents reuse
```

That makes the invariant visible in the allocator map and keeps ordinary allocation concurrency available for unrelated addresses.

See `MMIO_LEASE_GUARD_EXPERIMENT.md` for the superseded comparison.

## PIO boundary

This proof is intentionally MMIO-only.

PIO uses a different allocator contract: `SystemAllocator::allocate_io_addresses(..., None)` defaults to byte alignment, so equal-size PIO ranges can be distinct and partially overlap. The MMIO geometry proof therefore cannot be copied into the PIO branch.

See `PIO_SCOPE_BOUNDARY.md`.

## Remaining correctness question

A late error leaves both addresses reserved. This safely prevents a reuse collision, but the current allocator has no reservation identity and the caller restores the BAR config register to OLD. A subsequent retry may therefore need an explicit way to recognize or clean the quarantined NEW reservation.

Do not hide this as a leak. It is the next discriminator:

> can each external relocation step restore the old state locally, allowing NEW to be released after rollback, or does `AddressManager` need a small explicit pending-relocation record/token?

The first external class under execution is virtio config-BAR ioevent relocation. Its local transaction is:

```text
unregister OLD ioevents
-> register NEW ioevents
```

A separate exact-current experiment injects failure at every primary operation and attempts local rollback by removing any NEW registrations already installed and restoring every OLD registration already removed.

If that rollback itself fails, NEW-first's allocator quarantine remains the safety fallback.

## Next composition

Once the ioevent helper and this NEW-first ordering have independent green receipts, compose them with the clean generic Bus stack:

- `review/ch-bus-r677-r678-r679-clean`
- `2edcf22f0bd35beff06ab2b4e132cf240e54d2f9`

The combined claim should remain layered:

```text
Bus:       route-map mutation is failure/concurrency safe
Allocator: OLD is never published reusable before successful MMIO relocation
Ioevents:  config-BAR registration move restores OLD after a primary failure
```

Only after that composition should the work return to KVM-backed hotplug reproduction or any upstream packet.
