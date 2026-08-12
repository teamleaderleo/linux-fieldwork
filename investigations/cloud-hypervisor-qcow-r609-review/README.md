# Cloud Hypervisor QCOW L2 ownership repair review

Updated: 2026-08-12
Owning issue: #609
Role: independent repair design and candidate review
Disposition: ACCEPT CANDIDATE FOR HUMAN REVIEW
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Canonical source and candidate

- Cloud Hypervisor current `main`: `1af93ac7035cda77cd87b0c18b1134ebb0928052`.
- Owned fork candidate branch: `linux-fieldwork/qcow-l2-refcount-ownership-r609`.
- Candidate head: `12cb3db040362b5dc0656e6fc1eb6ebe2da6bd1c`.
- Candidate parent / merge base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`.
- Candidate relation: one commit ahead, zero behind exact current upstream source.
- Candidate source file: `block/src/formats/qcow/metadata.rs` only.
- Candidate diffstat: 168 insertions, 17 deletions.
- Candidate file SHA-256: `3bf9ff485f9c0d90bc5da51214f9741949f9954f2e15fca6e2f1af23439db921`.
- Candidate Git blob: `6646461c309558f1644b43921b27c0b08ecb7b5f`.
- Candidate-only diff SHA-256: `f7ba8b378a9d48f8a8c7f9620d4bb2beeab3365baf4e761d6150ed335fcab7d7`.

The source commit was reconstructed from the exact bytes exercised by the independent workflow. The materializer verified both the expected SHA-256 and Git blob before pushing the one-file candidate branch. Its temporary workflow was kept on a separate fork branch and removed after materialization.

The candidate commit carries `Assisted-by: ChatGPT:GPT-5.6 Sol`. It intentionally lacks a human `Signed-off-by` because no configured human Git identity was available to this worker. A human reviewer must amend/sign before any upstream submission.

## Defect and ownership boundary

The fresh-L2 defect is execution-proven on exact current source: a first write can allocate a fresh L2, publish it through L1, fail later with ENOSPC before the deferred L2 refcount update, clean-close, reopen with the L2 still at refcount 0, and hand that exact L1-referenced cluster back out through the allocator.

Independent source review found the same ownership-before-publication invariant violated at two new-L2 publication sites:

1. `cache_l2_cluster_alloc()` for the first L2 under an empty L1 entry;
2. `update_cluster_addr()` when a clean L2 table is relocated before an L2-entry update.

The pre-existing helper-only candidate repairs (1) but leaves (2) deferred. On the compressed-write path, `update_cluster_addr()` can publish the replacement L2 and then encounter fallible data write / compressed-cluster deallocation before `map_write()` applies deferred refcounts. A deliberately dropped-deferred-update test is red on baseline with relocated L2 refcount 0 after clean reopen.

The smallest repair reviewed here therefore follows one rule at both publication sites:

```text
allocate new L2 cluster
-> establish refcount=1 ownership
-> publish L1 pointer
-> later fallible work
```

Old-L2 release remains deferred. This preserves PR-8637's allocate-before-release safety ordering while preventing the replacement table itself from becoming live with refcount 0.

## Caller and sentinel audit

`cache_l2_cluster_alloc()` has exactly two callers on current source:

- `map_write()`;
- the `l2_addr_disk == 0 && zero_marker` branch of `deallocate_cluster()`.

Both caller-side fresh-L2 refcount operations are removed when ownership moves into the helper, preventing redundant ownership writes. The helper becomes `io::Result<()>`.

`update_cluster_addr()` is reached from the compressed-entry and empty/zero-entry branches of `map_write()`. A fresh L2 created earlier in the same `map_write()` is dirty, so `update_cluster_addr()` does not immediately relocate and double-own it. A cached clean existing L2 takes the relocation branch and now owns its replacement before the L1 switch.

L1 value 0 remains the absent-table sentinel. `get_new_cluster()` rejects cluster address 0. If immediate ownership fails, the L1 sentinel remains unchanged.

`set_cluster_refcount_track_freed(addr, 1)` is an absolute set to 1, not an arithmetic increment. The value fits every valid QCOW refcount width, including one-bit refcounts. Existing callers do not already hold an owner for these newly allocated metadata clusters.

## Failure-path review

### Fresh L2

- `get_new_cluster()` ENOSPC/error: L1 remains zero.
- zeroing / file-growth failure inside allocation: L1 remains zero.
- immediate refcount ownership failure, including refcount-block COW/ENOSPC/I/O: L1 remains zero. The prospective L2 can become an unreachable leak or partial allocation; it cannot become a reachable refcount-0 L2 through this path.
- ownership succeeds, then L2-cache insertion/dirty-eviction write fails: L1 can name the new table, but the table already has refcount 1 and was zero-filled. This is an error/leak outcome, not live-free aliasing.
- later data allocation ENOSPC after publication: the fresh L2 remains owned and clean reopen excludes it from `avail_clusters`.

### Relocated L2

- replacement allocation failure: old L1 remains unchanged and old-L2 release has not started.
- immediate replacement-owner failure: old L1 remains unchanged and old-L2 release has not started; the new cluster can leak unreachable.
- replacement ownership succeeds, L1 publishes new table, then compressed data write/deallocation fails: the new live L2 remains refcount 1. The old table can leak because its deferred refcount-0 update is lost; this is the conservative failure direction.
- applying the deferred old-table refcount-0 later fails: the new live table remains owned; old metadata can remain allocated.

## Cache, reopen, shutdown, and concurrency

QCOW metadata mutations run under the `QcowMetadata` write lock, so concurrent guest requests cannot race two fresh-L2 allocations for one L1 index. A successful cache insertion makes repeated writes hit the same L2. If insertion fails after publication, a later operation can reload the owned zero-filled table from its L1 address.

Successful `sync_caches()` writes dirty L2/refcount metadata before committing L1/refcount-table pointer state. The focused tests use final-owner `QcowMetadata` drop followed by production `parse_qcow()` reopen and verify the new owner survives clean close/reopen.

Adjacent issue #611 tracks a different shutdown invariant: `shutdown()` ignores `sync_caches()` errors and can clear DIRTY after a metadata flush failure. This candidate does not claim crash/power-loss atomicity or repair that error path. On successful cache sync, it repairs #609's logical owner-before-publication defect.

## Independent execution receipt

Fieldwork execution branch: `research/r609-qcow-l2-owner-review`
Frozen execution head: `0c440c3812326c8af7973cd45ab7a5740f34e55a`
Workflow run: `31562514755`
Job: `94007596780`
Result: success
Artifact: `9128269811`, `r609-qcow-l2-owner-review`
Artifact digest: `sha256:d215afe599807042c4f80cbe52249bb1c5fdf136f6431b8edbc031b7b94eefab`
Runner: Ubuntu 24.04
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Rustfmt: `rustfmt 1.10.0-nightly (3d6c19bb9a 2026-08-11)`
Exact source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`

Baseline discriminators:

- `fresh_l2_enospc_reopen_does_not_reuse_live_table`: expected red, exit 101. Reopened allocator returned the live L2 at `327680`.
- `relocated_l2_dropped_deferred_updates_keeps_refcount_owner`: expected red, exit 101. Reopened replacement L2 refcount was 0.
- `zero_marker_fresh_l2_keeps_refcount_owner`: pass on baseline.

Candidate focused results:

- fresh-L2 ENOSPC -> clean reopen -> actual allocator reuse exclusion: pass;
- relocated-L2 dropped-deferred-update -> clean reopen ownership: pass;
- zero-marker fresh-L2 ownership: pass;
- existing `failed_l2_relocate*` controls: 2 passed.

Quality gates on the exact candidate bytes:

- `cargo +nightly fmt --all -- --check`: pass;
- `git diff --check`: pass;
- `cargo check --locked -p block --all-targets --tests`: pass;
- `cargo test --locked -p block`: 298 passed, 0 failed;
- `cargo test --locked -p block --features io_uring`: 326 passed, 0 failed;
- `cargo clippy --locked -p block --all-targets --tests -- -D warnings`: pass.

Execution limits: deterministic block-unit fixtures on a hosted Linux runner; no host-wide ENOSPC, power-cut injection, KVM integration suite, or failpoint for every individual filesystem write. Source ordering plus focused red/green probes cover the owner-before-L1 boundary; #611 remains the flush-error recovery boundary.

## Review disposition

**ACCEPT CANDIDATE FOR HUMAN REVIEW.**

The defect is proven, the helper-only candidate is too narrow for the stated invariant, and the one-file two-publication-site candidate preserves the conservative rollback direction: ownership failure happens before L1 publication; later failures can leak metadata but cannot expose the newly allocated L2 as allocator-free through these paths.
