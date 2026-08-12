# Cloud Hypervisor KVM dirty-log granule investigation

Controlling issue: #617

External-contact state: disabled. Cloud Hypervisor upstream remains read-only.

## Source boundary

Canonical `cloud-hypervisor/cloud-hypervisor` `main` was refreshed during this lane and remains:

`1af93ac7035cda77cd87b0c18b1134ebb0928052`

Owned fork `teamleaderleo/cloud-hypervisor` `main` was observed at:

`538237492941914440eec589ae4d2bfe33f7f108`

All candidate validation checks out canonical `1af93ac...` directly; the stale fork `main` is not used as a source base.

## Question

Does `MemoryManager::dirty_log()` decode KVM dirty bitmap bits with a hardcoded 4096-byte unit even when KVM's base page size is 16K or 64K, and can the conversion consume a backend-owned page unit without changing MSHV's fixed-4K dirty-log semantics?

## Current source proof

At canonical `1af93ac...`, `vmm/src/memory_manager.rs` merges the KVM/MSHV bitmap with the VMM bitmap and calls:

```rust
MemoryRangeTable::from_dirty_bitmap(dirty_bitmap, r.gpa, 4096)
```

`vm-migration/src/protocol.rs` is already generic: `MemoryRangeTable::from_dirty_bitmap()` accepts an explicit `page_size`, coalesces adjacent dirty bits, and scales both GPA and length by that unit. The migration range wire representation is byte-addressed (`gpa`, `length`), so this correction does not require a migration protocol format change.

The KVM backend returns `VmFd::get_dirty_log()` unchanged. Linux KVM memslots use host `PAGE_SHIFT` to derive `base_gfn` and `npages`, so the bitmap bit unit follows the host base page size. MSHV has a distinct fixed `PAGE_SHIFT = 12` dirty-log path.

## Synthetic production-seam discriminator

The candidate extracts only the existing bitmap OR + `MemoryRangeTable::from_dirty_bitmap()` call into `dirty_bitmap_to_range_table()`, leaving the production converter unchanged. Unit tests invoke that helper directly.

For `BASE_GPA = 0x4000_0000`, bitmap `0b10`:

| Granule | Expected GPA | Expected length |
|---|---:|---:|
| 4K | `0x4000_1000` | `0x1000` |
| 16K | `0x4000_4000` | `0x4000` |
| 64K | `0x4001_0000` | `0x10000` |

The 16K row is the controlling discriminator. Current hardcoded `4096` decodes bit 1 as `0x4000_1000 / 0x1000`; the correct 16K decode is `0x4000_4000 / 0x4000`.

Additional synthetic cases:

- VM bit 1 plus VMM bit 2 at 16K coalesce to one range at `0x4000_4000`, length `0x8000`.
- VM word-0 bit 63 plus VMM word-1 bit 0 at 64K coalesce across the bitmap word boundary to one range at `0x403f_0000`, length `0x20000`. This also exercises final-run emission.
- Partial sub-page dirty ranges are not represented by this bitmap API: each bit denotes a base page. The relevant final-edge case is final dirty-run emission, covered above.

## Minimal candidate direction

The current repaired candidate carries the unit through the hypervisor backend API:

```rust
fn dirty_log_page_size(&self) -> Result<NonZeroU64>;
```

KVM reads `_SC_PAGESIZE`, rejects negative conversion and zero, and returns a validated `NonZeroU64`. MSHV explicitly returns `1 << PAGE_SHIFT`, preserving its existing fixed-4K decode. `MemoryManager::dirty_log()` asks for the unit once per collection pass and feeds it into the existing range converter. Page-size calculation therefore stays backend-owned and the migration protocol code remains generic.

An earlier transient `u64` candidate cast `sysconf()` directly and was superseded after review exposed the `-1 -> u64::MAX` failure mode.

## Changed-file fence

The source candidate is restricted to:

```text
hypervisor/src/kvm/mod.rs
hypervisor/src/mshv/mod.rs
hypervisor/src/vm.rs
vmm/src/memory_manager.rs
```

Execution workflows live only on disposable validation branches.

## Validation

Disposable repaired validation branch:

`linux-fieldwork/validate-kvm-dirty-log-granule-final2`

Run: `31563891373`, native `ubuntu-24.04-arm`, exact canonical checkout.

Commands/gates:

```text
cargo +nightly fmt --all
git diff --check
cargo test -p vmm --features kvm dirty_bitmap_ -- --nocapture
cargo test -p vm-migration test_memory_range_table_from_dirty_ranges_iter -- --nocapture
cargo check -p vmm --features kvm
cargo check -p vmm --features mshv --target x86_64-unknown-linux-gnu
cargo clippy -p vmm --features kvm --all-targets --tests -- -D warnings
cargo clippy -p vmm --features mshv --target x86_64-unknown-linux-gnu --all-targets --tests -- -D warnings
git diff --stat
git diff --check
git diff
```

At this checkpoint: exact checkout, candidate application, nightly formatting, the four-file fence, host-page query, and all three synthetic seam tests are green. The hosted AArch64 runner reports `getconf PAGESIZE = 4096`, so 16K/64K coverage is synthetic. Remaining build/Clippy/full-diff gates are tracked by the same run and this record will be amended after completion.

A previous AArch64 validation of the raw-`u64` form passed the synthetic tests, migration control, KVM build, KVM Clippy, fence, and full-diff inspection; that form is superseded and is not the final candidate.

## Public overlap / adjacent evidence

A fresh Cloud Hypervisor issue/PR search found no public fix for this exact KVM migration hardcoded-4K conversion seam. Current issue #8582 independently demonstrates unrelated Cloud Hypervisor unit tests failing on a 16K-page kernel because of hardcoded 4096 assumptions, so non-4K AArch64 hosts are an active environment class.

Recent VFIO migration work is a useful API precedent: device dirty logging records the granularity actually applied by the backend and reuses that reported value when decoding its bitmap. That supports backend ownership of KVM's dirty-log unit.

## Limitations / adjacent invariants

- No controlled 16K/64K KVM host with `/dev/kvm` is available in this session. There is no live non-4K KVM migration execution here.
- The hosted native-AArch64 runner is 4K and lacks `/dev/kvm`; it provides compile/test coverage only.
- Existing `vm_dirty_bitmap.iter().zip(vmm_dirty_bitmap.iter())` truncates unequal vectors. This candidate preserves that pre-existing behavior; bitmap-length validation is a separate hardening item.
- MSHV's backend bitmap is explicitly retained at 4K. A hypothetical non-4K MSHV host could give the VMM-side `AtomicBitmap` a different host page unit; proving or normalizing that merge invariant is separate from the KVM defect.
- Existing range arithmetic/bounds behavior is unchanged.
- Cloud Hypervisor upstream requires DCO sign-off for a submission. This internal candidate is generated as a review artifact without inventing a contributor sign-off identity.

## Disposition checkpoint

The production conversion defect is synthetically proven at the real conversion seam. A typed backend-owned repair is under final validation.
