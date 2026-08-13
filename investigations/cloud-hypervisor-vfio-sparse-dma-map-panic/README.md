# Cloud Hypervisor — guest virtio-IOMMU MAP can panic across a sparse VFIO BAR subregion

Updated: 2026-08-13
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Security-oriented question

Can a malicious guest issue a virtio-IOMMU MAP request whose GPA range is inside a VFIO BAR as a whole but crosses the boundary of one host-mapped sparse BAR subregion, causing Cloud Hypervisor to panic inside the unsafe GPA-to-host-pointer translator instead of returning a mapping error?

This is a guest-triggerable VMM availability boundary. No host-memory corruption or guest escape is claimed.

## Exact-current ownership chain

`virtio-devices/src/iommu.rs` parses guest `VirtioIommuReqMap` fields and computes `size = virt_end - virt_start + 1` with checked arithmetic and page-alignment checks. For each attached endpoint it calls:

```rust
ext_map.map(req.virt_start, req.phys_start, size)
```

For VFIO, `ExternalDmaMapping::map()` first checks ordinary guest RAM. If the GPA is not RAM, it allows a VFIO MMIO path when:

```rust
self.mmio_regions.lock().unwrap().check_range(gpa, size)
```

and then calls:

```rust
find_user_address(gpa, size)
```

before passing the returned host pointer to `vfio_dma_map()`.

## Mismatched validation domains

`MmioRegionRange::check_range()` validates against each whole `MmioRegion`:

```text
BAR start <= gpa
and
gpa + size <= BAR end
```

But one `MmioRegion` may contain multiple smaller `user_memory_regions`. Cloud Hypervisor deliberately creates these from VFIO sparse-mmap capabilities and when carving/trapping MSI-X table/PBA ranges.

`find_user_address()` chooses a `user_memory_region` containing only the starting GPA, then currently executes:

```rust
assert!(size <= len - offset_from_start, ...);
```

So the outer whole-BAR check does not imply the inner subregion assertion.

## Reduced discriminator

Create one logical BAR:

```text
BAR:             [0x1000, 0x5000)
user mapping A:  [0x1000, 0x2000)
hole:            [0x2000, 0x3000)
user mapping B:  [0x3000, 0x4000)
```

Request:

```text
gpa  = 0x1800
size = 0x1000
```

The range `[0x1800,0x2800)` is inside the BAR, so `check_range()` returns true. It starts inside mapping A but only 0x800 bytes remain there, so current `find_user_address()` hits the assertion.

Controls:

- `[0x1800,0x2000)` fits in mapping A and returns a valid pointer;
- a request starting in the hole returns an ordinary error.

No VFIO hardware is needed to reproduce the first-failing owner because the panic occurs before the VFIO ioctl.

## Minimum candidate

Inside `find_user_address()`, if the requested size does not fit wholly inside the selected `user_memory_region`, do not assert. Continue searching and ultimately return the existing `unable to find user address` error if no single actual host mapping contains the full range.

This preserves the unsafe trait's documented contract: return either an error or a pointer valid for the complete requested size.

Do not relax whole-BAR checks, alter virtio-IOMMU map policy, stitch non-contiguous host mappings, or change VFIO ioctl behavior.

## Gates

- exact source pin;
- source gate proving guest MAP -> `ext_map.map(... phys_start, size)`;
- source gate proving sparse/MSI-X BARs create multiple `user_memory_regions`;
- baseline in-subregion success control;
- baseline hole error control;
- baseline crossing-range panic witness;
- no-panic invariant expected red;
- restore exact source;
- candidate returns an ordinary error for crossing range;
- in-subregion control remains valid;
- full `pci` library tests with `kvm` feature;
- dependent `virtio-devices` compile check;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only diff hash.
