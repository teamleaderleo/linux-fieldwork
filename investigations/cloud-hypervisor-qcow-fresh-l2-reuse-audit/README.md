# Cloud Hypervisor QCOW fresh-L2 reuse audit

Updated: 2026-08-12
State: FINISHED
Canonical issue: #609
Worker: LF-R609C
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
Execution branch: `research/ch-qcow-fresh-l2-reuse-audit-r609c`
Workflow run: `31562147006`
Job: `94006498021`
Artifact: `9128122394`
Artifact digest: `sha256:939a02704683658fb0bfb80d9cc83d3fa30cdb9d260e1224a87c18ab1c2032eb`
Toolchain: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; none occurred

## Result

VERIFIED THEORY, narrowed to the clean-close boundary.

Exact-current Cloud Hypervisor can return from a failed first write with an L1 entry pointing at a fresh L2 whose refcount is still zero. That L2 is inert inside the same process because allocation already removed it from the current free lists. Final-owner clean shutdown then flushes the L2/L1 caches and clears DIRTY. A clean reopen trusts the on-disk zero refcount, inserts the still-referenced L2 into `avail_clusters`, and the normal data allocator can return and overwrite that exact cluster while L1 still points to it.

The paired dirty-image control repairs the mismatch. When the same L1/refcount mismatch is persisted while DIRTY remains set, `parse_qcow()` rebuilds refcounts from L1/L2 reachability, restores the L2 refcount to 1, and excludes it from `avail_clusters`.

This means dirty-bit recovery is a real protection for dirty reopen. The defect requires a path that reaches a clean image with the mismatched pointer/refcount pair, and ordinary final-owner shutdown provides exactly that transition after a successful `sync_caches()`.

## Exact execution

The probe uses two appended physical clusters and caps the refcount horizon at that file size. The higher appended cluster becomes the fresh L2. Later work consumes the other cluster and reaches ENOSPC while updating metadata, before `map_write()` reaches its local deferred fresh-L2 refcount loop.

Clean arm output:

```text
post_enospc live_l2=0x50000 refcount=0 in_avail=false in_unref=false
post_shutdown dirty=false live_l2=0x50000
clean_reopen l1=0x50000 refcount=0 free_contains=true free_last=0x50000
allocator_reuse returned=0x50000 l1_still=0x50000 marker=[a5, a5, a5, a5, a5, a5, a5, a5, a5, a5, a5, a5, a5, a5, a5, a5]
```

The real `append_data_cluster()` allocator returned `0x50000`, the exact cluster still referenced by L1, and marker bytes physically replaced the beginning of the L2 cluster.

Dirty-recovery control output:

```text
post_enospc live_l2=0x50000 refcount=0 in_avail=false in_unref=false
dirty_reopen l1=0x50000 recovered_refcount=1 free_contains=false
```

Both exact tests passed. The workflow also built the block unit-test target with the injected probe and confirmed test discovery before running each test by exact name.

## Source audit conclusions

### Fresh L2 allocation and publication

`get_new_cluster(None)` zeroes a reused cluster before returning it. `cache_l2_cluster_alloc()` then writes the new cluster address into the in-memory L1 table and creates a dirty empty L2 cache entry. It returns the new address to `map_write()`, which records `(new_addr, 1)` only in a local deferred `set_refcounts` vector.

A later `?` in `map_write()` can therefore return before that vector is applied. There is no rollback of the L1 pointer or fresh cache entry on that unwind. There is also no implicit refcount owner attached to the L1 cache entry.

### Flush and clean shutdown

`sync_caches()` writes dirty L2 tables, refcount blocks, and then L1. Its L1 encoder preserves the L2 cluster address when the cluster refcount is zero; only the copied/refcount-one flag is clear. It does not reconcile L1 reachability against refcounts.

`QcowMetadata::shutdown()` runs `sync_caches()` and then clears DIRTY for writable images. The later final-owner shutdown change controls *when* this happens; it does not recover a dropped caller-local refcount update.

### Reopen and allocator

Writable dirty reopen sets `refcount_rebuild_required` and rebuilds ownership from reachability before free-cluster discovery. Clean reopen skips that recovery and builds `avail_clusters` by scanning on-disk refcounts for zero. The clean probe demonstrated the resulting live-L2 entry and subsequent real allocator reuse.

The explicit QCOW CORRUPT feature check does not catch this pair on clean reopen because no reachability-vs-refcount consistency scan runs in that path.

## Upstream-history boundary

Merged PR 8637 fixed a different ENOSPC ordering bug in L2 *relocation*: it now allocates the replacement before releasing the old referenced L2. Its final description explicitly calls out the fresh-L2/deferred-refcount unwind as a remaining gap whose failure appears after reopen. Current main still carries that fresh-L2 ordering.

The earlier stale punch-hole fix quarantines a deallocated cluster until the destructive host punch completes. The pointer-table cursor fix makes table writes independent of callback cursor movement. Neither supplies ownership for a newly published fresh L2.

The post-8637 metadata shutdown change moves DIRTY clearing to the final `QcowMetadata` owner. It leaves `map_write()` and fresh-L2 refcount publication ordering unchanged.

## Precise invariant and minimum ordering

Invariant:

> Every L1-reachable L2 cluster must hold nonzero refcount ownership before the pointer can survive a later fallible operation or become durable.

Minimum safe ordering for the fresh-L2 path:

```text
allocate + zero fresh L2
-> establish refcount ownership
-> publish L1 pointer
-> later fallible mapping work
```

Equivalent safety is possible with a transaction that rolls the fresh L2 allocation, cache state, L1 pointer, and refcount back together on every failure. Ownership-before-publication is the smaller local boundary. If later publication/cache work fails after ownership is acquired, a bounded leak is safer than making a reachable metadata cluster allocator-free.

Terminology correction for #609: the fresh L2 allocation itself succeeds. The failing operation is later work in the same first write after the fresh L2 has already been published into L1.

## Evidence boundary

Proven on exact-current source:

- fresh L2 published in L1 with only deferred refcount ownership;
- later ordinary ENOSPC unwinds before the deferred update;
- same-process free lists do not yet contain the live L2;
- final-owner shutdown persists the L1/L2 and clears DIRTY;
- clean reopen retains L1 -> L2 with refcount 0 and classifies the L2 free;
- normal `append_data_cluster()` returns that exact live L2 and overwrites it;
- DIRTY-preserving reopen rebuilds refcounts, restoring the L2 to refcount 1 and excluding it from allocation;
- PR 8637 fixed relocation ordering and explicitly left this fresh-L2 reopen case open.

No product candidate was applied in this branch. No third-party upstream mutation or contact occurred.
