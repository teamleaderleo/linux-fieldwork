# PIO BAR relocation scope boundary

Updated: 2026-08-15

Fieldwork issue: `teamleaderleo/linux-fieldwork#599`
Exact Cloud Hypervisor source reviewed: `69d4c0a82ef15b2660906013bd87ae32668e7998`
External-contact state: false

## Why this is separate

The MMIO NEW-first simplification relies on a geometric property:

```text
BAR size = power of two
NEW allocator request alignment = BAR size
OLD and NEW have equal size
=> accepted distinct ranges are disjoint
```

That lets MMIO reserve NEW while OLD remains allocated and free OLD only after successful relocation.

PIO does not currently have the same allocator contract.

`PciConfiguration` still requires an I/O BAR size to be a power of two and masks the PCI BAR's reserved low address bits. But `AddressManager::move_bar()` uses `SystemAllocator::allocate_io_addresses(..., None)`, whose default alignment is one byte. The allocator therefore does not require NEW to be aligned to the BAR length.

Consequently, two equal-size PIO ranges can be distinct and partially overlap. A blanket MMIO-style `reserve NEW while OLD remains reserved` change could reject a PIO move that current free-first behavior can represent.

## Decision

Keep #599's NEW-first candidate MMIO-only.

Do not use the MMIO alignment proof to rewrite the PIO branch merely because the two branches currently share similar free/allocate code.

If PIO relocation becomes a target, give it its own discriminator:

1. establish which I/O BAR bases a guest can actually publish after PCI configuration masking;
2. determine whether partially overlapping PIO moves are intentional/required or merely representable;
3. reproduce a current PIO move whose NEW range overlaps OLD;
4. choose a reuse/publication rule from that evidence.

Until then, preserving current PIO sequencing is the smaller compatibility claim.

## Process lesson

This is a useful stop example for the reasoning-radius rule: the nearby code looks symmetric, but a different allocator alignment contract breaks the proof used for MMIO. Same function and similar syntax are not enough to merge the invariants.
