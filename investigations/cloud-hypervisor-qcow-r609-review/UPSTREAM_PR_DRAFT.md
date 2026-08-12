# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: `cloud-hypervisor/cloud-hypervisor`  
Proposed base branch: `main`  
Candidate branch: `teamleaderleo/cloud-hypervisor:linux-fieldwork/qcow-l2-refcount-ownership-r609`  
Candidate head at drafting: `12cb3db040362b5dc0656e6fc1eb6ebe2da6bd1c`  
Candidate base at drafting: `1af93ac7035cda77cd87b0c18b1134ebb0928052`  
External contact authorized: `false`

## Proposed title

`block: Own new QCOW L2 tables before L1 publication`

## Draft

`map_write()` defers some L2 refcount changes until the end of the mapping operation. A newly allocated L2 can therefore be installed into L1 before its `refcount=1` update has been applied.

If later fallible work returns early, the deferred refcount update is dropped while the L1 mutation remains. After shutdown, an image whose DIRTY bit is clear can reopen without rebuilding refcounts. The still-referenced L2 is then seen with refcount 0 and becomes eligible for normal allocator reuse.

The same ownership ordering exists both when creating the first L2 for an empty L1 slot and when allocating a replacement L2 during relocation.

This change gives each newly allocated L2 refcount ownership before L1 can reference it. Release of the old relocated L2 remains deferred, preserving the ordering introduced by PR #8637: the replacement is secured before the previous live table is released.

If ownership fails, L1 remains unchanged. If something fails after ownership has been established, the result can conservatively leave an allocated cluster behind, but it can't expose a still-referenced L2 as free space.

The added regressions cover fresh-L2 ENOSPC followed by reopen and allocator reuse, replacement-L2 ownership when later deferred updates are lost, and the zero-marker fresh-L2 path. The existing failed-relocation regressions remain green.

### Validation

```text
cargo +nightly fmt --all -- --check                         PASS
git diff --check                                           PASS
cargo check --locked -p block --all-targets --tests        PASS
cargo test --locked -p block                               298 passed, 0 failed
cargo test --locked -p block --features io_uring           326 passed, 0 failed
cargo clippy --locked -p block --all-targets --tests -- -D warnings  PASS
```

The focused candidate regressions also passed:

```text
fresh_l2_enospc_reopen_does_not_reuse_live_table
relocated_l2_dropped_deferred_updates_keeps_refcount_owner
zero_marker_fresh_l2_keeps_refcount_owner
failed_l2_relocate_keeps_live_table_off_free_lists
failed_l2_relocate_after_compressed_write_keeps_live_table
```

No KVM boot test, host-wide ENOSPC run, or power-loss test has been run for this candidate.

AI assistance: ChatGPT (GPT-5.6 Sol) was used for source review, test design, and patch refinement.

## Internal reviewer notes

The deferred `set_refcounts` pattern predates the current Cloud Hypervisor QCOW structure and was present in the crosvm-derived implementation imported in 2019. A later L2-cache helper extraction explicitly preserved the existing logic. The deferred vector is useful for collecting metadata updates, but it isn't a transaction: L1 and free-list state can survive an error after the corresponding deferred refcount update has been dropped.

The repair is intentionally framed as `ownership before reachability`, not as a transactional rewrite. It doesn't add a rollback/commit protocol.

The source candidate changes only `block/src/formats/qcow/metadata.rs`. The candidate remains one commit ahead of the exact upstream base at the time of this draft.

Issue #611 remains a separate shutdown durability problem: metadata flush failure can interact with DIRTY-bit clearing. This candidate doesn't claim to repair that path.

## Submission checklist

- [x] Candidate is one source commit on the current intended upstream base at drafting time.
- [x] Complete candidate diff reviewed.
- [x] Baseline fresh-L2 regression fails and candidate passes.
- [x] Baseline relocated-L2 ownership regression fails and candidate passes.
- [x] Block tests and io_uring block tests pass.
- [x] Check, Clippy, rustfmt, and diff-check pass.
- [x] Existing PR #8637 relocation regressions remain green.
- [x] Fork/branch delivery path exists.
- [ ] Candidate commit has the human `Signed-off-by` trailer.
- [ ] Upstream base rechecked immediately before submission.
- [ ] Explicit authorization for upstream contact recorded.
- [ ] Submitted head and public PR recorded after submission.
