# Cloud Hypervisor dirty-log granularity pull request draft

Status: internal draft; do not publish upstream without explicit authorization.

Candidate branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/kvm-dirty-log-granule-repair-v2`

Candidate commit: `2038c3cb262ac27604f647729557893a61510f99`

Compare view: https://github.com/cloud-hypervisor/cloud-hypervisor/compare/main...teamleaderleo:cloud-hypervisor:linux-fieldwork/kvm-dirty-log-granule-repair-v2

## Title

`vmm: Preserve dirty log granularity`

## Body

### Summary

During live migration, KVM reports which guest memory pages changed using a dirty bitmap. Each set bit represents one host base page.

`MemoryManager::dirty_log()` currently converts those bits into memory ranges assuming every page is 4K, which works on normal 4K hosts but produces the wrong addresses and lengths on KVM hosts using 16K or 64K base pages.

For example, on a 16K host, dirty bit 1 represents the 16K range starting at `base + 16K`, while the current conversion treats it as a 4K range starting at `base + 4K`.

This change carries the dirty bitmap together with its byte granularity and uses that value when building migration ranges, and it also checks that the VMM and hypervisor dirty bitmaps describe memory using the same granularity before combining them.

MSHV keeps its existing fixed 4K dirty-log granularity.

### Design

`Vm::get_dirty_log()` now returns the bitmap and its interpretation together as `DirtyLog { bitmap, bytes_per_bit }`, rather than returning the bitmap separately from the value needed to decode it. KVM supplies its checked host base-page size, while MSHV supplies its existing fixed 4K unit.

Before combining the hypervisor and VMM bitmaps, `MemoryManager` checks their granularity, expected bitmap size, alignment, range bounds, and unused tail bits so inconsistent inputs fail instead of silently dropping or misaddressing dirty memory.

### Testing

Added focused tests covering:

- 4K, 16K, and 64K dirty-bit conversion
- merging VM and VMM dirty bits
- adjacent and cross-word range coalescing
- granularity mismatches
- bitmap length mismatches
- out-of-range tail bits
- alignment and overflow cases

The same source tree also passed KVM/MSHV build and Clippy checks on the tested x86_64 and AArch64 targets.

I ran the existing live-migration integration tests on a real 4K KVM host:

```text
PASS common_parallel::test_live_migration_basic
PASS common_parallel::test_live_migration_basic_paused
```

I do not currently have access to a Linux KVM host using a 16K or 64K base page size, so I could not perform the final end-to-end migration test on non-4K KVM hardware. I would appreciate help testing this on such a host.

AI assistance: ChatGPT (GPT-5.6-Sol) was used for source review, test design, and patch refinement.
