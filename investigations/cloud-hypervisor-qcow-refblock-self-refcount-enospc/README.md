# Cloud Hypervisor QCOW refcount-block ownership ENOSPC audit

Updated: 2026-08-12
State: EXECUTION PENDING
Worker/variant: LF-R609F-adjacent
Originating audit: #609 candidate failure-boundary review
Fieldwork base: `883a874568f48ea79c4341e0828c90de7bb8e260`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream is read-only

## Separate theory

This is **not** the fresh-L2 bug in #609 and does not depend on the #609 candidate.

Exact-current `QcowState::set_cluster_refcount()` handles refcount-block copy-on-write roughly as:

```text
target refcount update needs a replacement refcount block
-> allocate replacement block Y
-> RefCount::set_cluster_refcount(..., new_cluster=Y)
   -> publish refcount_table[region] = Y
   -> mutate cached replacement contents
-> recursively release old refcount block
-> target update is now logically complete
-> recursively set refcount(Y) = 1
```

The last step can itself need a new refcount block if `Y` lies in a different refcount region whose table entry is zero. If that recursive ownership allocation fails with ENOSPC, the outer call returns an error **after the refcount table already points to Y**.

Leading invariant to disprove:

> A refcount-table entry must never become durable/reachable to a replacement refcount block while that block's own refcount remains zero.

If the theory is correct, a clean reopen can classify the live refcount block as free and the ordinary allocator can zero/reuse it, destroying the refcounts stored inside it.

## Why this is plausibly reachable

For a normal 64 KiB QCOW image with 16-bit refcounts, one refcount block covers 32,768 clusters. A replacement refcount block allocated at or beyond cluster 32,768 belongs to refcount-table region 1 even if it is replacing the block for region 0.

On a sufficiently large/sparse image, or under free-list reuse, that placement is normal. If region 1 has no refcount block yet and the filesystem then reports ENOSPC while trying to allocate one, recursive ownership of the replacement block can fail.

## Deterministic discriminator

The test uses the real 64 KiB / 16-bit geometry (`32,768` entries per refcount block) and unmodified current source.

It temporarily creates a sparse two-region allocation horizon so `add_cluster_end()` deterministically returns ENOSPC instead of relying on host disk exhaustion:

1. parse a fresh QCOW image and assert refcount-table entry 0 is populated while entry 1 is zero;
2. construct an in-memory `RefCount` over exactly two real refcount regions (same geometry, only a smaller logical horizon);
3. sparse-extend the file to the end of those two regions so extension beyond the horizon is rejected;
4. make two free clusters available in LIFO order:
   - target X in region 0;
   - replacement refblock Y at the first cluster of region 1;
5. allocate X normally, then request `refcount(X)=1`;
6. X's clean region-0 refblock relocates to Y and refcount-table entry 0 switches to Y;
7. recursive `refcount(Y)=1` needs a region-1 refblock, but no free cluster remains and horizon extension returns ENOSPC;
8. require the outer call to return ENOSPC;
9. remove only the unused sparse tail, clean-close, and reopen through the real parser;
10. prove:
    - on-disk refcount-table entry 0 == Y;
    - Y's refcount == 0 because region-1 entry remains zero;
    - `avail_clusters` contains Y and Y is the next allocator cluster;
11. call the real allocator, require it returns and zeroes Y while the refcount table still points at Y;
12. clean-close/reopen again and prove X's formerly-1 refcount is now zero because allocator reuse destroyed the live refcount block.

The artificial horizon only supplies deterministic ENOSPC. The table-region crossing, copy-on-write ordering, recursive ownership, clean close/reopen, free-list reconstruction, and allocator reuse all use normal product paths and real format geometry.

## Stop condition

FALSIFY if any current mechanism prevents `refcount_table[0]` from surviving pointed at Y with `refcount(Y)==0`, or if clean reopen repairs/excludes Y before allocator publication.

If execution reaches allocator reuse of Y and a second reopen observes loss of X's refcount, create a separate canonical Fieldwork issue rather than enlarging #609.
