# Cloud Hypervisor — KVM dirty-log page granularity on non-4K hosts

Updated: 2026-08-12
State: SOURCE / ABI CONFIRMED; SYNTHETIC CANDIDATE EXECUTION NEXT
Owning issue: #617
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

Cloud Hypervisor currently converts every dirty-bitmap bit into a 4096-byte memory range in `MemoryManager::dirty_log()`.

For KVM, both dirty inputs being ORed there are host-base-page-granular:

- Linux KVM memslots count pages with `memory_size >> PAGE_SHIFT` and expose one dirty bit per memslot page;
- `vm-memory 0.18.0` `AtomicBitmap` uses `sysconf(_SC_PAGE_SIZE)`.

Cloud Hypervisor's KVM backend returns the kernel bitmap unchanged, so the final hardcoded `4096` is wrong on 16K/64K KVM hosts.

MSHV is different in current source: it explicitly uses 4K PFNs (`PAGE_SHIFT=12`). Therefore the fix must make dirty-log granularity a backend contract rather than globally replacing `4096` with host page size.

## Explain like I'm five

Each dirty bit means “this page changed; copy it again.”

On a 16K KVM host, one bit means 16K. Cloud Hypervisor currently reads the bit and copies only 4K, and it computes later bit addresses as if every page were 4K apart.

That can leave changed guest memory behind during migration.

## Why care

Live migration depends on dirty logging to transfer writes that happened after the first memory copy. Wrong page indexing can make the destination retain stale RAM while the migration protocol itself succeeds.

Example on a 16K host:

```text
slot base = 0x4000_0000
KVM dirty bit 1 means:
  GPA 0x4000_4000, length 0x4000

current hardcoded 4K conversion sends:
  GPA 0x4000_1000, length 0x1000
```

Bit 0 is already under-copied by 12K. Bit 1 is both under-sized and sent from the wrong address.

## Current source

`vmm/src/memory_manager.rs`:

```text
vm_dirty_bitmap = vm.get_dirty_log(...)
vmm_dirty_bitmap = region.bitmap().get_and_reset()
combined = zip(...).map(or)
MemoryRangeTable::from_dirty_bitmap(combined, region_gpa, 4096)
```

`MemoryRangeTable::from_dirty_bitmap()` uses the supplied page size to compute both GPA and range length.

## KVM granularity evidence

Cloud Hypervisor KVM backend:

```text
self.fd.get_dirty_log(slot, memory_size as usize)
```

No bit-index normalization occurs.

Linux KVM current source computes memslot page count with the host kernel page shift:

```text
base_gfn = guest_phys_addr >> PAGE_SHIFT
npages = memory_size >> PAGE_SHIFT
```

The dirty bitmap is sized from `memslot->npages`, so one bit represents one host base page.

## VMM bitmap granularity

Pinned dependency:

```text
vm-memory = 0.18.0
```

`AtomicBitmap::with_len()` obtains page size from:

```text
sysconf(_SC_PAGE_SIZE)
```

and creates one bitmap bit per that page size.

Thus KVM and VMM bitmaps share host-page meaning in the current KVM path.

## MSHV boundary

Current `hypervisor/src/mshv/mod.rs` defines:

```text
PAGE_SHIFT = 12
```

and dirty-log PFNs are formed with that fixed shift.

So a blind host-page substitution at `MemoryManager` would conflate backend contracts. The dirty-log granule must come from the backend.

## Leading candidate

Add a small method to the hypervisor `Vm` interface:

```text
dirty_log_page_size() -> u64
```

Default:

```text
4096
```

This preserves MSHV's current 4K semantics without touching that backend.

KVM override:

```text
sysconf(_SC_PAGESIZE)
```

`MemoryManager::dirty_log()` then passes:

```text
self.vm.dirty_log_page_size()
```

to `MemoryRangeTable::from_dirty_bitmap()`.

A typed dirty-log result carrying `{ bitmap, page_size }` would be harder to misuse long-term, but the trait method is the smaller first candidate.

## Synthetic proof

A no-hardware unit control should establish the conversion semantics explicitly:

```text
bitmap = 0b10
base = 0x4000_0000
page_size = 16K
=> range GPA = base + 16K, length = 16K
```

Also retain:

- 4K current behavior;
- adjacent 16K bits coalesce to 32K;
- KVM current-host granule is nonzero/power-of-two;
- MSHV compile path retains 4K default.

## Runtime boundary

Do not claim end-to-end migration correction from an x86_64 hosted runner.

Required before upstream-ready confidence:

- AArch64 KVM host with 16K or 64K base pages;
- dirty a known byte/page after the initial memory copy;
- live migrate;
- verify destination receives the full host-page update at the correct GPA;
- include an adjacent-page negative control.

## Evidence boundary

Established:

- current hardcoded 4096 product conversion;
- KVM kernel bitmap is host-page-granular;
- Cloud Hypervisor KVM passes it through unchanged;
- VMM `AtomicBitmap` is host-page-granular;
- MSHV current dirty-log PFNs are fixed 4K.

Pending:

- candidate build/unit/cross-build gates;
- real non-4K KVM execution;
- final API shape review.

## Authority

No upstream issue, pull request, comment, review, reaction, email, or other external interaction was created by Fieldwork for this lane.
