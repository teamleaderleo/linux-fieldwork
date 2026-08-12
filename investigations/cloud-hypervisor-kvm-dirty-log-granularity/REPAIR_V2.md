# Cloud Hypervisor dirty-log granularity repair v2

Updated: 2026-08-12
Owning issue: #617
Canonical Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Execution branch: `teamleaderleo/cloud-hypervisor:fieldwork/kvm-dirty-log-granule-repair-v2`
Execution head: `d94b9469ce0dc99e83017899eca37112c2edf199`
Current hosted run: `31563474390` — queued at this checkpoint
External-contact state: `false; none occurred`

## Goal

Repair the current untyped dirty-log API so the bitmap's byte unit travels with the bitmap, KVM host-page dirty bits decode correctly on 4K/16K/64K Linux hosts, and MSHV remains explicitly fixed at its 4K Hyper-V page unit.

## Selected API

The candidate changes `Vm::get_dirty_log()` from a bare `Vec<u64>` to:

```rust
pub struct DirtyLog {
    pub bitmap: Vec<u64>,
    pub bytes_per_bit: NonZeroU64,
}
```

This makes the producer's unit part of the returned value. `MemoryManager` consumes that value and independently identifies the VMM `AtomicBitmap` unit from the host Linux page size before combining bitmaps.

### KVM

KVM returns the kernel bitmap together with checked `_SC_PAGESIZE`:

- reject `sysconf()` failure instead of casting `-1` to `u64::MAX`;
- require a nonzero power-of-two page size;
- preserve the bitmap unchanged.

### MSHV

MSHV returns the bitmap with `1 << PAGE_SHIFT`, preserving its current fixed 4K contract.

If the Linux VMM bitmap unit differs from MSHV's unit, the merge fails with a typed migration error instead of OR-ing unrelated bit positions.

## Merge invariants

Before OR/coalescing, the candidate validates:

1. backend and VMM `bytes_per_bit` equality;
2. power-of-two granularity;
3. nonzero region size aligned to the granularity;
4. GPA alignment to the granularity;
5. checked `start_gpa + memory_size`;
6. exact expected `u64` word count for both bitmap producers;
7. zero tail bits outside the memory region.

Only after these checks does it OR the words and call the existing `MemoryRangeTable::from_dirty_bitmap()` with the backend byte granularity.

The exact word-count check removes the current `zip()` truncation hazard. The range and tail checks bound the existing dirty-range arithmetic to the registered RAM range.

## Synthetic review discriminator

A Python model matching the candidate's invariants was executed locally before hosted Rust validation.

Observed positive cases:

```text
bit 1 @ 4K:   gpa=0x40001000 len=0x1000
bit 1 @ 16K:  gpa=0x40004000 len=0x4000
bit 1 @ 64K:  gpa=0x40010000 len=0x10000

VM bit 1 + VMM bit 2 @ 16K:
  gpa=0x40004000 len=0x8000

cross-word adjacent bits 63/64 @ 16K:
  gpa=0x400fc000 len=0x8000
```

Observed negative cases each reject as intended:

```text
backend/VMM granularity mismatch
bitmap word-count mismatch
set tail bit outside region
non-power-of-two granularity
misaligned memory size
misaligned GPA
GPA end overflow
```

The model caught a draft test-oracle error before Rust execution: the cross-word 16K GPA is `0x400f_c000`, not `0x403f_0000`. The disposable validation harness now applies the corrected oracle.

## Intended source scope

A green execution publishes a clean technical candidate containing only:

```text
hypervisor/src/kvm/mod.rs
hypervisor/src/lib.rs
hypervisor/src/mshv/mod.rs
hypervisor/src/vm.rs
vmm/src/memory_manager.rs
```

Temporary workflows and transformer scripts remain only on the disposable execution branch.

## Planned gates

The current hosted workflow is configured to run:

```text
cargo +nightly fmt --all
git diff --check
exact five-file product-scope fence
cargo test -p vmm --features kvm dirty_log_ -- --nocapture
cargo test -p vm-migration test_memory_range_table_from_dirty_ranges_iter -- --nocapture
cargo check -p vmm --features kvm
cargo check -p vmm --features mshv
cargo check -p vmm --features kvm --target aarch64-unknown-linux-gnu
cargo check -p vmm --features mshv --target aarch64-unknown-linux-gnu
cargo clippy -p vmm --features kvm --all-targets --tests -- -D warnings
complete final diff inspection
```

At this checkpoint GitHub Actions has a queue backlog and the repaired run `31563474390` has not allocated a job. No Rust gate is recorded as passed yet.

## Harness history

- Run `31563176729`: failed before job allocation because the initial embedded Python transformer made the workflow YAML invalid. Harness failure; zero product evidence.
- The transformer was moved to a separate disposable script and the workflow became syntactically valid.
- Independent arithmetic review then found the cross-word test-oracle typo and corrected it before execution.
- Run `31563474390` is the current corrected validation run.

## Candidate branch / DCO boundary

On a green run the workflow targets `linux-fieldwork/kvm-dirty-log-granule-repair-v2` for the five-file technical commit.

The execution environment does not expose a verified configured human Git identity. Therefore the technical candidate is intentionally left without a manufactured `Signed-off-by:` identity. Before any human upstream handoff, reset/amend the commit with the contributor's configured identity and `git commit -s`, preserving the same product bytes and required `Assisted-by: ChatGPT:GPT-5.6 Sol` disclosure.

No upstream pull request, comment, issue mutation, or other Cloud Hypervisor upstream interaction is authorized or performed.

## Evidence boundary

The source contract and the repaired API semantics are synthetic/source-review evidence. Real 16K/64K KVM live migration, direct kernel dirty-bitmap observation on those hosts, guest-visible stale-memory reproduction, and a real 4K KVM control remain outside the available controlled environments.

Reopen the API design if exact-source Rust gates expose an ownership/type incompatibility, a backend returns a bitmap with a different cardinality contract, or a real KVM/MSHV environment disproves the assumed producer unit.
