# Cloud Hypervisor QCOW fresh-L2 ENOSPC reopen execution

Updated: 2026-08-12
State: EXECUTING
Worker/variant: LF-R609E
Owning issue: #609
Fieldwork base: `82788b0edf0d8499b781eae60ae6722eec5179fa`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; no third-party interaction is authorized or performed

## Question

Can exact-current Cloud Hypervisor execute this complete sequence deterministically?

```text
failed write / later allocation
-> fresh L2 reachable from L1
-> fresh L2 refcount remains 0
-> clean metadata shutdown
-> clean reopen
-> live L2 appears in avail_clusters
-> get_new_cluster() returns that exact live L2 address
```

The decisive baseline witness must execute the final allocator call. Free-list membership alone is supporting evidence.

## Existing evidence inspected before this carrier

The canonical issue, every current issue comment, duplicate #612, the prior carrier `research/ch-qcow-reopen-refcount`, and its complete four-file diff were read before creating this branch. The prior hosted run `31552807399` stopped during probe application/format checking, before build or product execution. Its result is therefore classified as a fixture/workflow failure, with no product conclusion.

Public Cloud Hypervisor history was read only. Merged PR 8637 explicitly records the fresh-L2/refcount-0 reopen gap as remaining work after its relocation fix. Current upstream `main` still resolves to the exact source SHA above.

A repository-wide QCOW search also found the Landlock/QCOW and direct-backing investigations. Those cover different call paths and do not supply an allocator/refcount close-reopen witness for this question.

## Exact-current source invariant

On the empty-L1 path, `cache_l2_cluster_alloc()` currently allocates a fresh cluster, stores it in L1, creates the L2 cache entry, and returns its address. `map_write()` stores the required `(new_l2, 1)` refcount change only in its local deferred vector. A later fallible `append_data_cluster()` / refcount operation can return through `?` before the vector is applied.

Clean `QcowMetadata::shutdown()` syncs caches and clears the DIRTY bit. Clean `parse_qcow()` then scans physical clusters in ascending offset order and pushes every `refcount == 0` cluster to `avail_clusters`. `get_new_cluster()` pops from the end of that vector.

The fixture deliberately makes the fresh L2 the highest physical zero-refcount cluster, so reopening makes that exact L2 the next allocator return if the hypothesis is correct.

## Probe design

`apply_probe.py` adds four focused tests to the exact source tree:

1. `fresh_l2_enospc_reopen_allocator_reuses_live_table`
   - ignored by default because it is an intentionally corrupting baseline witness;
   - reserves exactly two appended allocator-visible clusters;
   - forces the post-publication write failure;
   - records fresh-L2 address and pre-close refcount;
   - cleanly drops `QcowMetadata`;
   - reparses the file through the production parser;
   - records reopened L1 address, refcount, and free-list tail;
   - calls `get_new_cluster(None)` and requires the returned address to equal the still-live L2.

2. `fresh_l2_enospc_reopen_keeps_live_table_owned`
   - invariant test expected to fail on baseline and pass on the candidate;
   - requires the cleanly reopened live L2 to have refcount 1 and stay off the free list.

3. `fresh_l2_success_reopen_keeps_live_table_owned`
   - valid/non-failing control using an ordinary successful first write and clean reopen.

4. `zero_marker_fresh_l2_keeps_refcount_owner`
   - adjacent caller control because `deallocate_cluster(... zero_marker=true)` shares `cache_l2_cluster_alloc()`.

The existing upstream regression `failed_l2_relocate_keeps_live_table_off_free_lists` is executed unchanged on both baseline and candidate.

## Candidate under test

The narrow candidate moves fresh-L2 ownership into `cache_l2_cluster_alloc()`:

```text
allocate new L2
set refcount(new L2) = 1
publish L1 -> new L2
insert/cache zero L2 table
```

Caller-side fresh-L2 increments are removed from `map_write()` and the zero-marker deallocation path. Relocation bookkeeping in `update_cluster_addr()` stays unchanged.

This carrier materializes the candidate only inside a disposable exact-source Actions checkout. Cloud Hypervisor upstream remains read-only.

## Execution gates

The workflow records exact source and Rust versions, formats the injected probe before checking format, builds and discovers every focused test, then runs:

```text
# baseline controls / witness
cargo test --locked -p block --lib fresh_l2_success_reopen_keeps_live_table_owned -- --exact --nocapture
cargo test --locked -p block --lib failed_l2_relocate_keeps_live_table_off_free_lists -- --exact --nocapture
cargo test --locked -p block --lib fresh_l2_enospc_reopen_allocator_reuses_live_table -- --ignored --exact --nocapture
cargo test --locked -p block --lib fresh_l2_enospc_reopen_keeps_live_table_owned -- --exact --nocapture   # expected red

# candidate focused controls
cargo test --locked -p block --lib fresh_l2_enospc_reopen_keeps_live_table_owned -- --exact --nocapture
cargo test --locked -p block --lib fresh_l2_success_reopen_keeps_live_table_owned -- --exact --nocapture
cargo test --locked -p block --lib zero_marker_fresh_l2_keeps_refcount_owner -- --exact --nocapture
cargo test --locked -p block --lib failed_l2_relocate_keeps_live_table_off_free_lists -- --exact --nocapture

# broader gates
cargo test --locked -p block
cargo test --locked -p block --features io_uring
cargo clippy --locked -p block --all-targets -- -D warnings
cargo fmt --all -- --check
git diff --check
```

All logs and complete probe/candidate diffs are retained as the run artifact. The workflow uploads artifacts even after a failing gate.

## Evidence classes

- Source/history: exact-current and already established.
- Fixture/workflow: this carrier repairs the prior pre-execution failure by formatting injected Rust before the format check and by retaining always-uploaded receipts.
- Product reproduction: pending hosted execution.
- Candidate: pending hosted execution.

## Stop / disposition rule

- **PROVEN** if the baseline witness records L1 -> fresh L2, refcount 0 before and after clean reopen, free-list publication, and `get_new_cluster()` returning that exact L2.
- **FALSIFIED** if exact-current execution demonstrates a product owner restores ownership or excludes the live L2 before allocator return.
- **REPAIR** if the fixture or workflow fails before the product discriminator executes.

A candidate result is accepted only after the focused invariant/control matrix, the unchanged relocation regression, full block tests, io_uring block tests, Clippy, rustfmt, and complete-diff inspection agree on the same exact source generation.
