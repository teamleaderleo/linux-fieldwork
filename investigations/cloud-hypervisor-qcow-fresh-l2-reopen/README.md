# Cloud Hypervisor — QCOW fresh-L2 ENOSPC reopen refcount

Updated: 2026-08-12
State: CANDIDATE READY FOR HUMAN REVIEW
Owning issue: #609
Disposition: ACCEPT CANDIDATE FOR HUMAN REVIEW
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
Owned source candidate: `teamleaderleo/cloud-hypervisor@f50d82af46753719a8fab7209a01e2d5460d3ace`
Source branch: `linux-fieldwork/qcow-fresh-l2-refcount`
External-contact state: false; none occurred

## Result

The defect is executable on exact-current Cloud Hypervisor source. A failed first write can publish a fresh L2 through L1 while that L2 still has refcount zero. A successful clean close persists the L1 reference and clears DIRTY. Clean reopen then treats the still-referenced cluster as free, and the allocator can return the exact live L2 address.

The smallest safe repair moves fresh-L2 ownership into `cache_l2_cluster_alloc()`: allocate and zero the fresh L2, set its refcount to 1, then publish the L1 pointer and insert the table into the L2 cache. The two callers no longer add a separate fresh-L2 refcount.

The clean source candidate is one commit directly on the exact upstream head and changes one file:

```text
block/src/formats/qcow/metadata.rs
```

Candidate compare against `1af93ac7035cda77cd87b0c18b1134ebb0928052`: ahead 1, behind 0, one changed file, 174 additions and 17 deletions. The additions include three focused regression/control tests.

## Independent baseline proof

Fieldwork run `31562343911` used exact upstream `1af93ac7035cda77cd87b0c18b1134ebb0928052` with Rust 1.89.0 and nightly rustfmt `1.99.0-nightly (3d6c19bb9 2026-08-11)`.

Two independent discriminators fail on baseline as required:

- clean-reopen allocator reuse: test exits 101 after the allocator returns the exact still-referenced L2 (`left: 327680`, `right: 327680`);
- ownership ENOSPC: test exits 101 because baseline leaves L1 published (`left: 262144`) when the invariant requires zero.

Artifact `9128231893` has digest `sha256:cb1e4306167a58fd83d6d8ab4453ac77962bc6e18e9416a7b700958446691f5a`.

A later retained receipt, run `31562528682`, records:

```text
source=1af93ac7035cda77cd87b0c18b1134ebb0928052
rustc 1.89.0 (29483883e 2025-08-04)
rustc 1.99.0-nightly (3d6c19bb9 2026-08-11)
BASELINE_REUSE_RC=101
BASELINE_OWNERSHIP_RC=101
candidate_reuse=pass
candidate_ownership=pass
nightly_fmt=pass
block_tests=pass
block_io_uring_tests=pass
clippy=pass
```

Artifact `9128392578` has digest `sha256:7df373e4db09f16699c7f8d59350005bbefa7669262e3e046eaeff1aa319fc6a`.

## Exact candidate-tree validation

Owned-fork materializer run `31563067456` applied the reviewed probe and repair to exact upstream `1af93ac7035cda77cd87b0c18b1134ebb0928052`, then passed:

- `git diff --check`;
- `cargo +nightly fmt --all -- --check`;
- `fresh_l2_enospc_reopen_keeps_live_table_out_of_free_list`;
- `fresh_l2_refcount_enospc_does_not_publish_l1`;
- `zero_marker_fresh_l2_keeps_refcount_owner`;
- `cargo test --locked -p block`: 298 passed;
- `cargo test --locked -p block --features io_uring`: 326 passed;
- `cargo clippy --locked -p block --all-targets -- -D warnings`.

The exact tested `metadata.rs` blob is `7f6559490fdbd133ba64f44c4dcad1441f05f4e4`. The clean one-commit candidate `f50d82af46753719a8fab7209a01e2d5460d3ace` reuses that exact blob on the upstream base tree. Temporary materializer commits were removed from the candidate branch history.

## Full-diff review

### Ownership boundary

`cache_l2_cluster_alloc()` is the right owner for fresh-L2 allocation because it is the routine that creates the metadata cluster and publishes its L1 address. The candidate performs `set_cluster_refcount_track_freed(new_addr, 1)` before `self.l1_table[l1_index] = new_addr`.

The helper has exactly two write-side callers in current source:

1. `map_write()`;
2. `deallocate_cluster()` when a zero marker needs a fresh L2.

Both caller-side fresh-L2 increments are removed, preventing double counting. Existing-L2 cache population never receives a new ownership increment.

### ENOSPC and rollback

- Allocation failure before a fresh L2 exists leaves L1 unchanged.
- Refcount-COW ENOSPC after allocating the fresh L2 but before securing ownership is covered by `fresh_l2_refcount_enospc_does_not_publish_l1`; L1 remains zero.
- Data/refcount failure after successful fresh-L2 ownership can leave an allocated empty L2, but that cluster has refcount 1 before L1 exposure.
- Cache insertion/eviction failure occurs after ownership and L1 publication. The fresh L2 is zero-filled and refcount-owned, so reopen cannot classify it as free; the failure can retain an empty allocated table.
- The generic recursive refcount setter can itself allocate and relocate refcount metadata. Deeper failures can conservatively orphan allocation/refcount work. That pre-existing refcount transaction behavior remains a residual risk, while the fresh L2 stays unpublished until its own ownership call returns success.

### Zero-marker and sentinels

`l2_addr_disk == 0` is the absent-L2 sentinel. Physical cluster zero is rejected by the allocator. The zero-marker caller now relies on helper ownership and passes the focused refcount-1 control.

### Relocation

The candidate leaves `update_cluster_addr()` relocation logic unchanged. Existing relocation ENOSPC regressions, compressed-write relocation controls, metadata reuse tests, and the full block suites pass. A fresh `VecCache` is already dirty, so the immediate fresh-L2 path does not enter the clean-L2 relocation branch.

### Refcount overflow

Fresh ownership sets refcount to 1, which is valid for every accepted QCOW refcount width. Existing `refcount_overflow_returns_error` passes in the full suite, and overflow still maps through the existing refcount error path.

### Cache, concurrency, and repeated allocation

Metadata writes take the `QcowMetadata` write lock. A cache hit or nonzero L1 address bypasses fresh allocation, so repeated writes do not increment L2 ownership again. Cache eviction and L2-eviction/refcount-order tests pass in the full suites.

### Shutdown and reopen

On successful flush/clean close, the candidate persists refcount ownership before the L1 table can be durably committed, so clean reopen keeps the live L2 out of the free list. Dirty reopen already rebuilds refcounts from reachability.

Issue #611 tracks the adjacent shutdown path that clears DIRTY even when `sync_caches()` fails. That separate failed-flush problem remains outside this candidate.

## Candidate history / DCO

The review candidate is intentionally unsigned because the API execution path cannot create a commit with the repository-configured human author/signoff. The commit carries the required AI-assistance trailer. Before any upstream submission, the human owner should set the recorded contributor identity and amend/sign off:

```bash
git config user.name "Leo Li"
git config user.email "cheerleaderleo@outlook.com"
git commit --amend --reset-author -s --no-edit
```

No Cloud Hypervisor upstream issue, pull request, review, comment, reaction, or other contact occurred.
