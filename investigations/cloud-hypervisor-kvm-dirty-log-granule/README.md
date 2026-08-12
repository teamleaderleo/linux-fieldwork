# Cloud Hypervisor KVM dirty-log granule investigation

Controlling issue: #617

External-contact state: disabled. Cloud Hypervisor upstream remained read-only throughout this lane.

## Source boundary

Final refresh of canonical `cloud-hypervisor/cloud-hypervisor` `main`:

`1af93ac7035cda77cd87b0c18b1134ebb0928052`

Final refresh of owned fork `teamleaderleo/cloud-hypervisor` `main`:

`538237492941914440eec589ae4d2bfe33f7f108`

All candidate validation checks out canonical `1af93ac...` directly. The owned-fork `main` is older and was excluded as a source base.

## Question

Does `MemoryManager::dirty_log()` decode KVM dirty bitmap bits with a hardcoded 4096-byte unit even when KVM's base page size is 16K or 64K, and can the conversion consume a backend-owned page unit while preserving MSHV's fixed-4K dirty-log semantics?

## Current source proof

At canonical `1af93ac...`, `vmm/src/memory_manager.rs` merges the KVM/MSHV bitmap with the VMM bitmap and calls:

```rust
MemoryRangeTable::from_dirty_bitmap(dirty_bitmap, r.gpa, 4096)
```

`vm-migration/src/protocol.rs` is already generic: `MemoryRangeTable::from_dirty_bitmap()` accepts an explicit `page_size`, coalesces adjacent dirty bits, and scales both GPA and length by that unit. The migration range wire representation is byte-addressed (`gpa`, `length`), so the correction fits the existing migration protocol representation.

The KVM backend returns `VmFd::get_dirty_log()` unchanged. Current Linux KVM memslot setup derives `base_gfn` and `npages` with host `PAGE_SHIFT`, so the KVM dirty bitmap bit unit follows the host base page size. MSHV has a distinct fixed `PAGE_SHIFT = 12` dirty-log path.

## Synthetic production-seam discriminator

The candidate extracts only the existing bitmap OR plus `MemoryRangeTable::from_dirty_bitmap()` call into `dirty_bitmap_to_range_table()`. Tests invoke that production helper directly.

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
- This bitmap API represents base pages rather than sub-page dirty intervals. Final dirty-run emission is the relevant edge case and is covered above.

## Minimal candidate

Source branch:

`linux-fieldwork/kvm-dirty-log-granule-typed-candidate`

Candidate commit:

`bfe83f56e61a4a0c28d9c78f6ec24a6972639a01`

Parent:

`1af93ac7035cda77cd87b0c18b1134ebb0928052`

The branch contains one source commit from exact canonical main.

The candidate carries the unit through the hypervisor backend API:

```rust
fn dirty_log_page_size(&self) -> Result<NonZeroU64>;
```

KVM reads `_SC_PAGESIZE`, checks the signed-to-unsigned conversion, rejects zero, and returns a validated `NonZeroU64`. MSHV explicitly returns `1 << PAGE_SHIFT`, preserving its existing fixed-4K decode. `MemoryManager::dirty_log()` asks for the unit once per collection pass and feeds it into the existing range converter. Page-size calculation remains backend-owned and migration protocol code remains generic.

An earlier transient source branch, `linux-fieldwork/kvm-dirty-log-granule` at `701c59afaa35dbfd6d7e2b452558dbf830e99b9d`, used a raw `u64` and direct `sysconf()` cast. Review exposed the `-1 -> u64::MAX` failure mode. The typed candidate above supersedes it.

## Changed-file fence

The source candidate contains exactly:

```text
hypervisor/src/kvm/mod.rs
hypervisor/src/mshv/mod.rs
hypervisor/src/vm.rs
vmm/src/memory_manager.rs
```

Validation workflow files exist only on disposable execution branches and are absent from the source candidate.

## Validation

Disposable repaired validation branch:

`linux-fieldwork/validate-kvm-dirty-log-granule-final2`

Run: `31563891373`
Job: `94011662858`
Runner: native `ubuntu-24.04-arm`
Canonical checkout: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Host base page size: `4096`

Executed commands/gates:

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

All gates passed. The workflow also rechecked the exact four-file fence, printed the full diff, committed only those four source files, asserted exactly one commit above canonical `1af93ac...`, and pushed the source candidate only after every gate succeeded.

Synthetic seam tests passed for 4K, the exact 16K discriminator, 64K, VM/VMM source merging, same-word adjacency, cross-word adjacency, and final-run emission. The existing `vm-migration` dirty-range control passed. Native-AArch64 KVM `cargo check` and Clippy passed. x86_64 MSHV cross-build and Clippy passed.

## Public overlap / adjacent evidence

A final Cloud Hypervisor issue/PR/code refresh found no exact public fix for this KVM migration hardcoded-4K conversion seam and no `dirty_log_page_size` implementation on canonical main.

Current issue #8582 independently demonstrates unrelated Cloud Hypervisor sparse unit tests failing on a 16K-page kernel around hardcoded 4096 assumptions, confirming 16K AArch64 hosts as an active execution environment class.

Recent VFIO migration work is an API precedent: device dirty logging records the granularity applied by the backend and uses that reported unit when decoding its bitmap. The KVM candidate follows the same ownership principle.

The concurrent #617 review was re-read before disposition. It independently reproduced the discriminator and flagged the raw `sysconf()` cast, bitmap-vector `zip` truncation, a hypothetical MSHV/VMM mixed-granule merge, arithmetic bounds, and DCO. This lane repaired the raw-page-size API and keeps the remaining items explicit below instead of broadening the KVM candidate.

## Limitations / adjacent invariants

- Controlled live 16K/64K KVM migration execution is unavailable in this session. The native AArch64 hosted runner uses a 4K base page and has no usable `/dev/kvm`; 16K/64K evidence is synthetic at the real conversion seam.
- Existing `vm_dirty_bitmap.iter().zip(vmm_dirty_bitmap.iter())` truncates unequal vectors. The candidate preserves that pre-existing behavior; bitmap-length validation is a separate hardening item.
- MSHV's backend bitmap remains explicitly 4K. A hypothetical non-4K MSHV host could give the VMM-side `AtomicBitmap` a different host-page unit; proving or normalizing that merge invariant is separate from the KVM defect.
- Existing range arithmetic/bounds behavior is unchanged.
- Cloud Hypervisor upstream requires DCO sign-off for submission. This internal candidate was generated as a review artifact without inventing a contributor sign-off identity.
- Cloud Hypervisor upstream received no mutation, comment, issue, PR, branch, or other contact from this lane.

## Disposition

The production conversion defect is synthetically proven at the real `MemoryManager` conversion seam. The minimal typed/backend-owned source candidate is green across focused tests, KVM build/Clippy, MSHV cross-build/Clippy, changed-file fence, ancestry check, and full-diff inspection.

PROVEN + CANDIDATE
