# Cloud Hypervisor — guest virtio-IOMMU MAP can panic across a sparse VFIO BAR subregion

Updated: 2026-08-13
Owning Fieldwork issue: #659
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — running-guest-triggerable VMM DoS; minimum candidate verified**

## Security boundary

A malicious running guest using virtio-IOMMU with an attached VFIO endpoint can submit a MAP request whose GPA range fits inside a logical VFIO BAR but crosses the boundary of one actually host-mapped sparse BAR subregion. Exact-current Cloud Hypervisor accepts the whole-BAR range and then panics inside the unsafe GPA-to-host-pointer translator.

Demonstrated impact is **VMM denial of service**. No host-memory corruption, cross-VM access, or guest escape has been established.

## Ownership chain

`virtio-devices/src/iommu.rs` parses guest `VirtioIommuReqMap` and calls:

```rust
ext_map.map(req.virt_start, req.phys_start, size)
```

VFIO's external DMA mapping permits the MMIO path after:

```rust
self.mmio_regions.lock().unwrap().check_range(gpa, size)
```

then calls `find_user_address(gpa, size)` before `vfio_dma_map()`.

The mismatch is that `check_range()` validates the entire logical BAR, while a BAR may contain multiple smaller `user_memory_regions` created for VFIO sparse-mmap capability and MSI-X table/PBA carving. Exact-current `find_user_address()` selects a subregion containing only the starting GPA and then asserts that the full requested size fits there.

## Executable discriminator

```text
BAR:             [0x1000, 0x5000)
user mapping A:  [0x1000, 0x2000)
hole:            [0x2000, 0x3000)
user mapping B:  [0x3000, 0x4000)

guest MAP GPA:   0x1800
size:             0x1000
```

The whole range `[0x1800,0x2800)` fits inside the BAR, but only 0x800 bytes remain in mapping A.

Baseline witness:

```text
Attempt to read 4096 bytes at offset 2048 into a region of size 4096
VFIO_SPARSE_DMA_BASELINE crossing_panicked=true
VFIO_SPARSE_BASELINE_INVARIANT_RC=101
```

Controls:
- a range wholly inside mapping A returns a valid host pointer;
- a range beginning in the sparse hole returns an ordinary error.

No VFIO hardware is needed because the first failing owner occurs before the VFIO ioctl.

## Minimum candidate

Replace the subregion assertion with a containment check:

```rust
if size > len - offset_from_start {
    continue;
}
```

If no actual host mapping contains the complete range, the existing `unable to find user address` error is returned. This preserves the unsafe mapper contract: return either an error or a pointer valid for the complete requested size.

Candidate-only SHA-256:

```text
acce404b520229080b0eea3185892d05e8b02003c62af608d0594a85eecc19b7
```

Complete candidate diff: one file, `pci/src/vfio.rs`, 3 insertions / 5 deletions. Reviewed in full; no unrelated product changes.

## Execution receipt

Baseline product run:

```text
run=31669892039
job=94352152390
```

Final all-green candidate carrier:

```text
fieldwork_head=70b159cedfd271ef6d958a0ccfb88e0c7cbebd20
run=31670217043
job=94353102520
source=1af93ac7035cda77cd87b0c18b1134ebb0928052
candidate_sha=acce404b520229080b0eea3185892d05e8b02003c62af608d0594a85eecc19b7
artifact=9169420439
artifact_digest=sha256:f31492dbb665e686a29a2d5c831fede5c7320550932e8b76a6d8c1e61a7ea127
```

Final gates:
- crossing-range candidate returns ordinary error;
- in-subregion control remains valid;
- PCI library: 42 passed, 0 failed, 1 intentionally ignored baseline witness;
- dependent `virtio-devices --features kvm` compile green;
- Clippy green;
- nightly rustfmt green;
- `git diff --check` green;
- immutable candidate hash matched exactly.

## Disposition

**PROVEN.** This is the first finding in the current security-oriented pass with a direct running-guest → host VMM process failure chain. Current evidence supports a guest-triggerable availability issue, not an isolation escape.
