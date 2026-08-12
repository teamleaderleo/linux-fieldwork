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

## Local Apple-silicon/Lima hardware attempt

A second non-4K attempt used an operator-owned Apple-silicon MacBook Air with Lima `2.2.0`. The host macOS version was not recorded in the transcript. The guest path used Apple Virtualization (`vmType: vz`), AArch64 Ubuntu 24.04, `plain: true`, and Lima nested virtualization.

### Clean 4K nested-KVM baseline

A fresh guest was created with:

```sh
limactl start -y \
  --name ch-kvm-clean \
  --vm-type vz \
  --arch aarch64 \
  --nested-virt \
  --plain \
  --cpus 6 \
  --memory 8 \
  --disk 80 \
  template:ubuntu-24.04
```

Observed guest state:

```text
Architecture: aarch64
Kernel: 6.8.0-134-generic
getconf PAGESIZE: 4096
/dev/kvm: present, root:kvm
KVM_GET_API_VERSION: 12
```

The user was added to the guest `kvm` group before the KVM ioctl check. This proves that the M5/Lima/VZ path can expose a real usable nested KVM device to an ARM64 Linux guest on the ordinary 4K kernel.

### 64K kernel artifacts

Inside the clean Ubuntu guest, `linux-generic-64k` was installed. The installed package set identified the 64K flavor as `6.8.0-137.137` for arm64, with kernel `6.8.0-137-generic-64k`.

The packaged boot artifacts copied to macOS were:

```text
vmlinuz-64k sha256 1585ab2c1575e1adbf0f9ebaa0917d1a9fa07d8654241a1a9155d3df9c655373
initrd-64k  sha256 52cb51653d49510b27eb7d90c1daab13b3170ca0d1ebc81a2f0041e57e805bf7
```

The packaged `vmlinuz` was gzip-compressed. Passing it directly to Lima/VZ's Linux boot loader failed immediately with:

```text
Error Domain=VZErrorDomain Code=1
Internal Virtualization error. The virtual machine failed to start.
```

After `gzip -dc`, `file` identified the result as an ARM64 Linux kernel boot executable and VZ accepted it far enough to enter VM state `running`.

### Direct-boot A/B discriminator

To separate a bad direct-boot harness from a 64K-specific failure, the same stopped Lima clone, disk, initrd/cmdline scheme, and VZ direct-Linux boot path were tested with a freshly extracted known-good 4K kernel from a separate pristine Ubuntu guest.

The 4K direct-boot control reached Lima `READY` in about seven seconds and reported:

```text
uname -r: 6.8.0-134-generic
getconf PAGESIZE: 4096
```

The 64K direct-boot attempt with nested virtualization enabled behaved differently:

```text
VZ VM state: running
Lima ready/SSH: not reached within 90 seconds
serialv.log: 0 bytes
```

No Cloud Hypervisor binary or migration test ran in this 64K attempt because the Linux guest never became usable.

A final follow-up set `nestedVirtualization = false` and started the same 64K direct-boot configuration. VZ again entered VM state `running`, but no successful guest-ready or SSH result was captured before the experiment was stopped. Treat that no-nested-virtualization sub-test as incomplete rather than as a definitive pass/fail discriminator.

### Interpretation of the local attempt

The local experiment establishes two things:

1. ARM64 nested KVM on the operator-owned M5/Lima/VZ setup works on a 4K Ubuntu kernel.
2. The tested Ubuntu 64K kernel did not reach a usable Linux guest under the tested VZ direct-boot setup, while an otherwise equivalent 4K direct-boot control did.

This is an environment/boot-path limitation for the attempted hardware validation. It is not evidence that the Cloud Hypervisor candidate fails on 64K KVM, because Cloud Hypervisor never executed in the failed 64K guest.

## Evidence boundary

- Defect at the dirty-bitmap conversion seam: proven synthetically.
- 4K/16K/64K conversion semantics: covered at the production conversion helper.
- MSHV fixed 4K contract: supported by the pinned MSHV/Hyper-V interface.
- Preferred candidate builds/lints/tests across KVM/MSHV and x86_64/AArch64: green.
- Preferred candidate real 4K KVM live migration: green.
- GitHub-hosted native ARM64 hardware was probed and is 4K-only with no usable `/dev/kvm`.
- Operator-owned M5/Lima/VZ hardware was probed and does expose usable nested KVM on a 4K ARM64 Ubuntu guest (`KVM_GET_API_VERSION = 12`).
- A direct-boot A/B check showed the same Lima/VZ disk and boot path reaches `READY` with the known-good 4K kernel, while the tested Ubuntu `6.8.0-137-generic-64k` kernel did not reach SSH/userspace under the nested-VZ setup.
- The follow-up 64K boot with nested virtualization disabled was started but did not produce a captured usable-guest result before the experiment ended; do not classify that sub-test more strongly.
- Real 16K/64K KVM live migration remains uncompleted. The local 64K attempt failed before Cloud Hypervisor execution, so it neither validates nor falsifies the candidate on real non-4K KVM hardware.
- Candidate is bot-authored/unsigned and still needs a human DCO sign-off before upstream handoff.
- Cloud Hypervisor upstream received no mutation or contact.

## Disposition

The defect is proven, the preferred paired-granularity candidate is green through focused validation and a real 4K KVM live-migration run, and the remaining evidence gap is specifically an end-to-end migration on a real 16K/64K KVM host. The M5/Lima attempt narrowed the local limitation to getting the tested 64K Ubuntu kernel into a usable VZ guest; it did not reach Cloud Hypervisor execution.

PROVEN + CANDIDATE
