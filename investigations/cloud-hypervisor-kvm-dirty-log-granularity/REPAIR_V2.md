# Cloud Hypervisor dirty-log granularity repair v2

Updated: 2026-08-12
Owning issue: #617
Canonical Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Final validation run/job: `31564829024` / `94014411511`
Execution recipe head: `011ae4eb9ae3c3035372cd053e08672b036a098e`
Published technical candidate: `teamleaderleo/cloud-hypervisor:linux-fieldwork/kvm-dirty-log-granule-repair-v2` @ `f1e892815ae6a71ffc18e5d18fd7fef1f030e048`
External-contact state: `false; none occurred`

## Disposition

`CANDIDATE API ACCEPTABLE`

The selected repair couples each backend dirty bitmap with its byte granularity and validates the VMM/backend compatibility boundary before any bitmap OR or range conversion.

Real 16K/64K KVM live migration remains hardware-blocked in the controlled environments available to this investigation. The disposition above is an API/source-candidate disposition, not an end-to-end hardware claim.

## Selected API

`Vm::get_dirty_log()` changes from a bare `Vec<u64>` to:

```rust
pub struct DirtyLog {
    pub bitmap: Vec<u64>,
    pub bytes_per_bit: NonZeroU64,
}

fn get_dirty_log(...) -> Result<DirtyLog>;
```

The bitmap and its semantic byte unit are returned as one value, preventing the unit from drifting independently from the bitmap-producing call.

### KVM

KVM returns the kernel bitmap unchanged together with checked host `_SC_PAGESIZE`.

The candidate rejects:

- signed conversion failure, including `sysconf()` returning `-1`;
- zero page size;
- a non-power-of-two page size.

This preserves KVM's host-base-page dirty-log contract for 4K, 16K, and 64K Linux kernels.

### MSHV

MSHV returns its bitmap together with `1 << PAGE_SHIFT`, preserving the backend's current fixed 4K dirty-log unit.

If the VMM `AtomicBitmap` host-page unit differs from MSHV's backend unit, migration fails at the merge boundary instead of OR-ing unrelated bit indices.

## Merge invariants

Before the backend bitmap and VMM bitmap are combined, `MemoryManager` validates:

1. backend and VMM `bytes_per_bit` equality;
2. power-of-two granularity;
3. nonzero memory size aligned to the granularity;
4. GPA alignment to the granularity;
5. checked `start_gpa + memory_size`;
6. exact expected `u64` word count for both bitmap producers;
7. zero tail bits outside the registered memory range.

Only after those checks does the candidate OR the bitmap words and call `MemoryRangeTable::from_dirty_bitmap()` with the explicit backend byte granularity.

The exact word-count check removes the prior silent `Iterator::zip()` truncation hazard. The coverage, tail-bit, alignment, and checked-end validation also bounds the existing dirty-range arithmetic to the registered RAM mapping.

## Dependency contract

Pinned Cloud Hypervisor dependency `kvm-ioctls 0.25.0` allocates the KVM dirty bitmap as:

```text
memory_size.div_ceil(page_size * 64)
```

`u64` words after validating `_SC_PAGESIZE`.

Repair v2 computes, for aligned mappings:

```text
page_count = memory_size / bytes_per_bit
expected_words = ceil(page_count / 64)
```

With KVM `bytes_per_bit == page_size`, the formulas are equivalent. Exact word-count equality therefore matches the pinned KVM userspace API contract.

See `DEPENDENCY_CONTRACT.md` for the pinned dependency review.

## Synthetic and unit discriminators

The repair covers these positive cases:

```text
bit 1 @ 4K:   gpa=0x40001000 len=0x1000
bit 1 @ 16K:  gpa=0x40004000 len=0x4000
bit 1 @ 64K:  gpa=0x40010000 len=0x10000

VM bit 1 + VMM bit 2 @ 16K:
  gpa=0x40004000 len=0x8000

cross-word adjacent bits 63/64 @ 16K:
  gpa=0x400fc000 len=0x8000
```

It also tests rejection of:

```text
backend/VMM granularity mismatch
bitmap word-count mismatch
set tail bit outside region
non-power-of-two granularity
misaligned memory size
misaligned GPA
GPA end overflow
```

Independent arithmetic review caught a draft cross-word test-oracle error before final validation: the correct 16K GPA for bit 63 is `0x400f_c000`. The final candidate carries the corrected oracle.

## Final validation receipt

Run `31564829024`, job `94014411511`, succeeded completely on exact canonical source `1af93ac7035cda77cd87b0c18b1134ebb0928052`.

Passed gates:

```text
exact canonical checkout
exact workflow-head transformer receipt
candidate application
nightly formatting
git diff --check
exact five-file product-scope fence
cargo test -p vmm --features kvm dirty_log_ -- --nocapture
  -> 7 passed, 0 failed
cargo test -p vm-migration test_memory_range_table_from_dirty_ranges_iter -- --nocapture
  -> passed
cargo check -p vmm --features kvm
cargo check -p vmm --features mshv
cargo check -p vmm --features kvm --target aarch64-unknown-linux-gnu
cargo check -p vmm --features mshv --target aarch64-unknown-linux-gnu
cargo clippy -p vmm --features kvm --all-targets --tests -- -D warnings
cargo clippy -p vmm --features mshv --all-targets --tests -- -D warnings
complete final diff inspection
clean technical candidate publication
```

The validation workflow fetches its transformer scripts by exact `GITHUB_SHA`, so the successful run proves the transformer bytes recorded by run head `011ae4eb9ae3c3035372cd053e08672b036a098e` rather than a moving branch tip.

## Published source candidate review

Candidate head:

```text
f1e892815ae6a71ffc18e5d18fd7fef1f030e048
```

Parent / merge base:

```text
1af93ac7035cda77cd87b0c18b1134ebb0928052
```

The candidate is exactly one commit ahead of canonical source and changes exactly these five files:

```text
hypervisor/src/kvm/mod.rs
hypervisor/src/lib.rs
hypervisor/src/mshv/mod.rs
hypervisor/src/vm.rs
vmm/src/memory_manager.rs
```

No workflow, transformer, receipt, or Fieldwork-only file exists in the technical candidate diff.

The commit message contains no external issue/PR references and includes:

```text
Assisted-by: ChatGPT:GPT-5.6 Sol
```

## DCO boundary

The technical candidate was materialized by the owned-fork validation workflow and currently has a bot author/committer with no human `Signed-off-by:` footer.

The execution environment does not expose a verified configured human Git identity. No identity was inferred or manufactured.

Before any human upstream handoff, preserve the validated product bytes and amend/reset the commit using the contributor's configured identity with `git commit -s`, while retaining the AI disclosure.

No upstream pull request, issue comment, review, or other Cloud Hypervisor upstream interaction occurred.

## Controlled hardware boundary

Local execution host:

```text
Debian GNU/Linux 13
Linux 6.18.35
x86_64
getconf PAGESIZE = 4096
/dev/kvm absent
Rust toolchain absent
outbound DNS blocked
```

Native ARM hosted probe `31562577130` / `94007782330`:

```text
Ubuntu 24.04.4 LTS
aarch64
Linux 6.17.0-1020-azure
getconf PAGESIZE = 4096
CONFIG_ARM64_4K_PAGES=y
CONFIG_KVM=y
CONFIG_KVM_GENERIC_DIRTYLOG_READ_PROTECT=y
arm64 KVM built into the kernel
/dev/kvm absent before and after sudo modprobe -v kvm
```

The hosted ARM VM therefore contains KVM kernel support while withholding virtualization device access. It also uses 4K base pages.

No controlled AArch64 16K/64K KVM environment was available, so the following remain unexecuted:

- real 16K/64K KVM `KVM_GET_DIRTY_LOG` observation;
- Cloud Hypervisor guest boot/live migration on such a host;
- guest-visible stale-memory baseline reproduction;
- candidate guest-preservation confirmation on such a host;
- real KVM 4K live-migration control.

Those limitations preserve the hardware evidence boundary while the repaired API/source candidate is acceptable for further servicing.
