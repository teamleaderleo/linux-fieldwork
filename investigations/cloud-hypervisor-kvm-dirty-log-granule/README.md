# Cloud Hypervisor KVM dirty-log granule investigation

Controlling issue: #617

External-contact state: disabled. Cloud Hypervisor upstream remained read-only throughout this lane.

## Source boundary

Final refresh of canonical `cloud-hypervisor/cloud-hypervisor` `main`:

`1af93ac7035cda77cd87b0c18b1134ebb0928052`

All preferred-candidate work is directly based on this exact canonical commit.

## Question

Does `MemoryManager::dirty_log()` decode KVM dirty bitmap bits with a hardcoded 4096-byte unit even when KVM's base page size is 16K or 64K, and can the conversion consume a backend-owned page unit while preserving MSHV's fixed-4K dirty-log semantics?

## Source proof

At canonical `1af93ac...`, `vmm/src/memory_manager.rs` merges the hypervisor dirty bitmap with the VMM bitmap and calls:

```rust
MemoryRangeTable::from_dirty_bitmap(dirty_bitmap, r.gpa, 4096)
```

`MemoryRangeTable::from_dirty_bitmap()` already accepts an explicit byte unit and scales GPA/length by that unit. KVM dirty bits follow the host base page size. The pinned VMM bitmap dependency, `vm-memory 0.18.0`, constructs `AtomicBitmap` with `sysconf(_SC_PAGE_SIZE)`.

MSHV uses a different contract. Cloud Hypervisor pins `mshv-ioctls 0.6.9`; its dirty-log implementation counts pages in `HV_PAGE_SIZE` units. `HV_PAGE_SIZE` is derived from `HV_HYP_PAGE_SIZE`, and the matching Hyper-V header defines `HV_HYP_PAGE_SHIFT` as 12, i.e. 4096 bytes.

## Synthetic discriminator

For `BASE_GPA = 0x4000_0000`, bitmap bit 1:

| Granule | Expected GPA | Expected length |
|---|---:|---:|
| 4K | `0x4000_1000` | `0x1000` |
| 16K | `0x4000_4000` | `0x4000` |
| 64K | `0x4001_0000` | `0x10000` |

The 16K row is the controlling discriminator. Hardcoded `4096` produces the wrong address/length on a 16K host.

## Preferred candidate

Source branch:

`linux-fieldwork/kvm-dirty-log-granule-repair-v2`

Candidate commit:

`f1e892815ae6a71ffc18e5d18fd7fef1f030e048`

Parent:

`1af93ac7035cda77cd87b0c18b1134ebb0928052`

The source branch contains one commit above exact canonical main.

The candidate pairs bitmap data with its meaning:

```rust
pub struct DirtyLog {
    pub bitmap: Vec<u64>,
    pub bytes_per_bit: NonZeroU64,
}
```

KVM returns its bitmap with a checked host base-page unit. MSHV returns its bitmap with the fixed Hyper-V 4K unit. `MemoryManager` obtains the VMM bitmap host-page unit, then validates before merging:

- backend and VMM bitmap granularity match;
- page unit is a power of two;
- GPA and memory size are aligned;
- range arithmetic does not overflow;
- both bitmap vectors have the exact required word count;
- no dirty tail bits lie outside the memory region.

Only after those checks are the two bitmaps ORed and converted into byte-addressed migration ranges. This also removes the old silent `.zip()` truncation risk.

The earlier minimal candidate `bfe83f56e61a4a0c28d9c78f6ec24a6972639a01` demonstrated the smallest correction, but the paired `DirtyLog` candidate above is preferred because it keeps bitmap data and bitmap granularity together and fails closed on inconsistent inputs.

## Changed-file fence

Preferred candidate product/test files:

```text
hypervisor/src/kvm/mod.rs
hypervisor/src/lib.rs
hypervisor/src/mshv/mod.rs
hypervisor/src/vm.rs
vmm/src/memory_manager.rs
```

Disposable validation workflow files exist only on disposable execution branches, not on the preferred source candidate.

## Focused validation

The repair-v2 validation already recorded on #617 passed all configured gates, including:

- formatting and `git diff --check`;
- seven focused dirty-log conversion/negative tests;
- existing `MemoryRangeTable` control test;
- native x86_64 KVM and MSHV builds;
- AArch64 KVM and MSHV cross-builds;
- KVM and MSHV Clippy with `-D warnings`;
- exact five-file fence, ancestry check, and full-diff inspection.

Synthetic coverage includes 4K, 16K, 64K, VM/VMM merging, same-word and cross-word coalescing, granularity mismatch, word-count mismatch, out-of-region tail bits, alignment errors, and overflow.

## Real KVM live migration

Preferred-candidate live validation used a disposable branch based on exact candidate `f1e892...`.

Run: `31567234922`
Job: `94021476274`
Runner: GitHub-hosted `ubuntu-24.04` x86_64
Kernel: `6.17.0-1020-azure`
Host base page size: `4096`
`/dev/kvm`: present and usable

Command:

```sh
scripts/dev_cli.sh tests --integration -- --test-filter test_live_migration_basic
```

Results:

```text
PASS cloud-hypervisor::integration common_parallel::test_live_migration_basic
PASS cloud-hypervisor::integration common_parallel::test_live_migration_basic_paused
Summary: 2 tests run: 2 passed, 303 skipped
```

This is an end-to-end live KVM migration check of the preferred candidate on a normal 4K host.

## Non-4K hardware attempt

A native hosted ARM64 runner was explicitly probed:

Run: `31567178564`
Job: `94021305797`
Runner: `ubuntu-24.04-arm`
Architecture: aarch64
Host base page size: `4096`
`/dev/kvm`: absent

Kernel config reported:

```text
CONFIG_ARM64_4K_PAGES=y
# CONFIG_ARM64_16K_PAGES is not set
# CONFIG_ARM64_64K_PAGES is not set
```

Therefore this controlled ARM runner cannot provide real 16K/64K KVM validation.

Canonical Cloud Hypervisor CI publicly declares a self-hosted `bookworm-arm64` runner for full ARM integration. It was only inspected as public configuration; no upstream workflow, issue, branch, PR, or comment was triggered by this lane.

Issue #8582 independently records Cloud Hypervisor unit-test failures on a real 16K-page kernel around unrelated hardcoded 4096 assumptions, confirming that 16K hosts are an active environment class.

## Evidence boundary

- Defect at the dirty-bitmap conversion seam: proven synthetically.
- 4K/16K/64K conversion semantics: covered at the production conversion helper.
- MSHV fixed 4K contract: supported by the pinned MSHV/Hyper-V interface.
- Preferred candidate builds/lints/tests across KVM/MSHV and x86_64/AArch64: green.
- Preferred candidate real 4K KVM live migration: green.
- Real 16K/64K KVM live migration: not completed because no controlled non-4K host with usable `/dev/kvm` is available in this environment; the available native ARM hardware path was explicitly probed and documented.
- Candidate is bot-authored/unsigned and still needs a human DCO sign-off before upstream handoff.
- Cloud Hypervisor upstream received no mutation or contact.

## Disposition

The defect is proven, the preferred paired-granularity candidate is green through focused validation and a real 4K KVM live-migration run, and the remaining evidence gap is specifically an end-to-end migration on a real 16K/64K KVM host.

PROVEN + CANDIDATE
