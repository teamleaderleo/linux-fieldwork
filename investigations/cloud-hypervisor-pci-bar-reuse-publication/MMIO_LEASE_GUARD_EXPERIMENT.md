# MMIO allocator lease-guard experiment

Updated: 2026-08-15

Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact Cloud Hypervisor source: `69d4c0a82ef15b2660906013bd87ae32668e7998`
Owned-fork research branch: `research/ch-pci-bar-r599-lease-guard`
External-contact state: false

## Question

Can the existing MMIO `AddressAllocator` mutex itself serve as the old-address reuse publication lease during `AddressManager::move_bar()`?

The experimental ordering was:

```text
lock selected allocator
-> free OLD and reserve NEW internally
-> keep allocator mutex locked through bus / metadata / KVM / device relocation
-> success: unlock with NEW reserved and OLD free
-> late failure: re-reserve OLD before unlock while keeping NEW reserved
```

The goal was deliberately narrower than cross-registry rollback: while the allocator mutex is held, competing allocator clients cannot observe the temporary free OLD state.

## Executed result

Candidate diff SHA-256:

`0ef510b599b403ecaf82d6fdeb01648479ee3ebc59f21fd062cebda6572ea533`

The focused lease tests passed with the normal KVM feature enabled:

```text
mmio_bar_relocation_lease_commit_publishes_only_new       PASS
mmio_bar_relocation_lease_failure_keeps_both_ranges_reserved PASS
mmio_bar_relocation_lease_rejected_new_restores_old      PASS
```

A hosted validation then ran all `device_manager::unit_tests`: 6 passed, 0 failed. The complete KVM-flavoured `vmm` test suite also compiled successfully with `cargo test --no-run`.

A direct full `vmm` test execution on the generic hosted runner reached 106 tests; 89 passed and 17 existing KVM-dependent tests failed because VM creation returned `Permission denied`. The three new lease tests passed there too. Treat those 17 failures as environment capability, not candidate signal.

The hosted Clippy experiment stopped on:

1. one test-only absolute-path lint in the experimental `TryLockError` assertion; and
2. an existing `#[expect(clippy::collapsible_match)]` becoming unfulfilled under the ad-hoc package/feature Clippy invocation.

No product-semantic failure was observed before this design was superseded.

## Why this is no longer the preferred candidate

The mutex experiment proved a useful principle:

> allocator visibility can be used as the address-reuse publication boundary.

But source review then removed the reason to hold the mutex across the entire relocation.

For MMIO BARs:

- PCI BAR size is required to be a power of two;
- `AddressManager` requests `AddressAllocator::allocate(new_base, len, Some(len))`;
- therefore a successful NEW address is `len`-aligned;
- OLD was admitted under the same BAR-size alignment.

Two equal-size, size-aligned intervals are either identical or disjoint. An unchanged BAR write is filtered before relocation; a partially overlapping target is rejected by alignment/allocation.

So successful MMIO relocation does not require freeing OLD to make room for NEW.

The smaller ordering is:

```text
OLD remains reserved
-> reserve NEW
-> perform relocation
-> free OLD last on success
```

That preserves the same publication safety without a long `PCI bus -> device -> allocator -> KVM/device` critical section.

## Retained lesson

The mutex experiment is useful comparative evidence, not wasted work. It established that:

- the allocator is the correct arbitration surface for unrelated reuse;
- late failure must never free an address that may already have external state;
- a conservative failure state can reserve both OLD and NEW;
- the right next question is whether OLD must be temporarily freed at all.

That final question produced the NEW-first candidate recorded in `MMIO_NEW_FIRST.md`.
