# Cloud Hypervisor QCOW fresh-L2 ENOSPC reopen execution

Updated: 2026-08-12
State: PROVEN
Worker/variant: LF-R609E
Owning issue: #609
Fieldwork base: `82788b0edf0d8499b781eae60ae6722eec5179fa`
Validated carrier/candidate head: `f5b213b0c9bc4bde4eebb065ff60eb77c54e7c02`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Hosted run: `31562587843`
Artifact: `9128298908`, digest `sha256:faf2278959b50dda6f28059f58d9e4e8731bd34cb9315263383eba146587705f`
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Result

Exact-current Cloud Hypervisor deterministically executes the full candidate chain:

```text
failed write / later allocation
-> fresh L2 reachable from L1
-> fresh L2 refcount remains 0
-> clean QcowMetadata close
-> production parse_qcow reopen
-> live L2 appears in avail_clusters
-> get_new_cluster(None) returns that exact live L2 address
```

The decisive baseline witness recorded:

```text
pre_close:       live_l2=0x50000 refcount=0 low_free=0x40000 high_free=0x50000
reopened:        live_l2=0x50000 l1=0x50000 refcount=0 free_contains=true free_tail=0x50000
allocator_return reused=0x50000 live_l2=0x50000 l1_still=0x50000
```

This is execution evidence for allocator aliasing, beyond source inspection or free-list membership.

The paired safety invariant returned test status 101 on baseline at the expected assertion after reopen:

```text
FRESH_L2_INVARIANT pre_close live_l2=0x50000 refcount=0
FRESH_L2_INVARIANT reopened live_l2=0x50000 refcount=0 free_contains=true
clean reopen must not classify a still-referenced fresh L2 as free
```

The same invariant passes with the candidate:

```text
FRESH_L2_INVARIANT pre_close live_l2=0x50000 refcount=1
FRESH_L2_INVARIANT reopened live_l2=0x50000 refcount=1 free_contains=false
```

## Controls

A successful ordinary first write and clean reopen passes on baseline and candidate:

```text
FRESH_L2_CONTROL pre_close live_l2=0x40000 refcount=1
FRESH_L2_CONTROL reopened live_l2=0x40000 refcount=1 free_contains=false
```

The adjacent zero-marker caller passes with the candidate:

```text
FRESH_L2_ZERO_MARKER live_l2=0x40000 refcount=1
```

The existing upstream regression `formats::qcow::metadata::unit_tests::failed_l2_relocate_keeps_live_table_off_free_lists` passes unchanged on both baseline and candidate.

## Candidate

The candidate establishes fresh-L2 ownership inside `cache_l2_cluster_alloc()` before publishing the L1 pointer:

```text
new_addr = get_new_cluster(None)?
set_cluster_refcount_track_freed(new_addr, 1)?
publish L1 -> new_addr
insert/cache zero L2 table
```

Caller-side fresh-L2 increments are removed from `map_write()` and the zero-marker deallocation path. Relocation bookkeeping in `update_cluster_addr()` stays unchanged.

The complete candidate-only diff was inspected after formatting. It is 57 lines of diff output and changes only the expected helper/caller sites plus the helper documentation. Candidate-only diff SHA-256:

`2878a2681e5c74e5c9a07747de6a38c0f7cc9072a2ad3ab0647dd03166e38f52`

## Exact commands

The hosted carrier runs the focused names exactly as discovered by `cargo test -- --list`:

```bash
# baseline valid control
cargo test --locked -p block --lib \
  formats::qcow::metadata::unit_tests::fresh_l2_success_reopen_keeps_live_table_owned \
  -- --exact --nocapture

# baseline nearby relocation regression
cargo test --locked -p block --lib \
  formats::qcow::metadata::unit_tests::failed_l2_relocate_keeps_live_table_off_free_lists \
  -- --exact --nocapture

# decisive baseline allocator-reuse witness
cargo test --locked -p block --lib \
  formats::qcow::metadata::unit_tests::fresh_l2_enospc_reopen_allocator_reuses_live_table \
  -- --ignored --exact --nocapture

# paired invariant: expected red on baseline, green on candidate
cargo test --locked -p block --lib \
  formats::qcow::metadata::unit_tests::fresh_l2_enospc_reopen_keeps_live_table_owned \
  -- --exact --nocapture

# candidate zero-marker caller control
cargo test --locked -p block --lib \
  formats::qcow::metadata::unit_tests::zero_marker_fresh_l2_keeps_refcount_owner \
  -- --exact --nocapture

# broader candidate gates
cargo test --locked -p block
cargo test --locked -p block --features io_uring
cargo clippy --locked -p block --all-targets -- -D warnings
cargo fmt --all -- --check
git diff --check
```

## Gate receipt

Run `31562587843` at carrier/candidate head `f5b213b0c9bc4bde4eebb065ff60eb77c54e7c02` completed successfully:

- exact-source checkout / Rust pin: pass
- probe application, rustfmt, `git diff --check`: pass
- focused-test discovery: pass
- baseline successful-write control: pass
- baseline existing relocation regression: pass
- baseline clean-reopen allocator-reuse witness: pass
- baseline safety invariant: expected red, harness classified correctly
- candidate application: pass
- candidate fresh-L2 invariant: pass
- candidate successful-write control: pass
- candidate zero-marker caller control: pass
- candidate existing relocation regression: pass
- `cargo test --locked -p block`: 298 passed, 0 failed, 1 intentionally ignored witness
- `cargo test --locked -p block --features io_uring`: 326 passed, 0 failed, 1 intentionally ignored witness
- `cargo clippy --locked -p block --all-targets -- -D warnings`: pass
- final rustfmt and `git diff --check`: pass

The run artifact retains the full probe diff, candidate-only diff, probe+candidate diff, exact test list, focused logs, full-suite logs, Clippy log, source/Rust versions, status, and receipt.

## Prior carrier classification

The earlier branch `research/ch-qcow-reopen-refcount` was inspected completely before this carrier. Its latest observed run `31552807399` stopped at probe application/format checking, so every build/product/candidate step was skipped. That earlier run is fixture/workflow evidence only. This carrier repaired that owner by formatting the injected Rust before enforcing the format check and by retaining artifacts on every outcome.

## Evidence class

**Product reproduction: PROVEN.** The real block metadata allocator returned the exact cluster still referenced by the reopened L1 table.

**Candidate execution: green on the focused invariant/control matrix and relevant block quality gates.**

## Limitations

This is a deterministic synthetic block-level fixture. It directly constrains `avail_clusters` after extending the disposable QCOW file and reconstructs the in-memory `RefCount` horizon so a later allocation/refcount operation reaches ENOSPC at the desired post-publication point. It therefore proves the product ordering and close/reopen allocator consequence while avoiding dependence on host filesystem fullness.

The witness does not reproduce a production guest workload, host-wide ENOSPC, or an already-populated fresh L2 containing successful guest mappings. The fresh L2 is live metadata because L1 references it; the failed first write leaves its table empty. The allocator call still returns and zeroes that exact L1-referenced metadata cluster.

Dirty-reopen recovery is a separate path. This witness uses the production clean-close owner and a clean reopen, matching the corruption candidate in #609.

## Disposition

**PROVEN**
