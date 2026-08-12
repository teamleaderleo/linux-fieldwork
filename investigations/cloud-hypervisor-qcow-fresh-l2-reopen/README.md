# Cloud Hypervisor — fresh L2 ownership across failed writes and clean reopen

Updated: 2026-08-12
State: EXECUTION QUEUED
Owning issue: #609
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
Carrier branch: `research/ch-migration-rollback-probes`
External-contact state: false; none occurred

## TL;DR

A QCOW ENOSPC gap that upstream PR 8637 explicitly left unresolved is still structurally present on current main.

For a previously empty L1 slot, `cache_l2_cluster_alloc()` allocates a fresh L2 cluster and publishes its address into L1 before that cluster owns a refcount. `map_write()` defers the fresh L2's `(addr, 1)` update in a local vector. If a later allocation fails, that vector is dropped while the L1 pointer remains.

Clean shutdown can flush the L1/L2 pointer state and clear DIRTY. A later clean reopen then rebuilds `avail_clusters` directly from `refcount==0`, offering the still-referenced L2 for reuse.

The queued exact-current block test is designed to prove the final allocator consequence, not merely the missing refcount: after clean reopen, `get_new_cluster()` should return the live L2 address.

## Explain like I'm five

QCOW keeps a directory that points to little mapping tables. Those tables live in disk clusters, and refcounts tell the allocator which clusters are already owned.

Today a new table can be put in the directory first, while its “owned” mark is delayed until later.

If the guest write runs out of disk space before that mark is written, the directory still points at the table but the allocator later thinks the cluster is free.

After reopening the image, a new write can reuse and overwrite the table that the directory still needs.

## Why care

This violates the allocator's core safety rule:

> A cluster reachable from QCOW metadata must never be returned as free storage.

The failure is durable across a clean process exit. The image does not need to stay DIRTY or crash during the first failed write.

## Historical intent

Relevant upstream history:

- https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8606
- https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8637

PR 8637 fixed the older failed-L2-relocation ordering bug. Its own description retained a separate known gap: a fresh L2 from `cache_l2_cluster_alloc()` can be wired into the tables, lose its deferred refcount update on ENOSPC, and re-enter the free list after reopen.

The merge commit is `a5e145bdefe72f3f4a7dd98186aee50f5e2fdf2b`.

Current main is well beyond that commit, but current `metadata.rs` retains the same fresh-L2 ordering. The only later metadata commit relevant to shutdown ownership, `53ee9ebb7769626207ca7b85d7fd3f375771236f`, does not change fresh-L2 refcount publication.

## Current source path

`map_write()`:

```text
set_refcounts = []
if cache_l2_cluster_alloc() returned fresh_addr:
    set_refcounts.push((fresh_addr, 1))

perform later fallible data allocation / mapping work

for deferred refcount update:
    apply it
```

`cache_l2_cluster_alloc()` for `l2_addr_disk == 0`:

```text
new_addr = get_new_cluster(None)?
self.l1_table[l1_index] = new_addr
create zero L2 cache entry
return Some(new_addr)
```

The L1 assignment marks the L1 cache dirty immediately.

A later empty-L2 data allocation runs through `append_data_cluster(...) ?`. If that fails after the only free cluster was consumed by the new L2, `map_write()` returns before the deferred fresh-L2 refcount loop.

## Clean close and reopen

`QcowMetadata::shutdown()` calls `sync_caches()` and then clears DIRTY for writable images.

The fresh zero L2 cache is dirty and the L1 table is dirty, so successful cache synchronization can persist:

```text
L1 -> fresh L2
fresh L2 contents = valid zero table
fresh L2 refcount = 0
```

The deferred refcount vector no longer exists.

On a clean reopen, `parse_qcow()` does not rebuild refcounts merely because a live pointer and refcount disagree. It scans physical clusters and adds `refcount==0` clusters to `avail_clusters`.

The live L2 is therefore eligible for allocation.

## Exact execution probe

Workflow:

```text
.github/workflows/ch-qcow-fresh-l2-reopen.yml
```

Run:

```text
31551917322
```

Exact test:

```text
formats::qcow::metadata::unit_tests::failed_fresh_l2_becomes_reusable_after_clean_reopen
```

Tracked applicator:

```text
apply_probe.py
```

Fixture shape:

1. create a fresh writable QCOW image with an empty L1 slot;
2. append exactly one physical free cluster;
3. cap the refcount/allocation horizon at the current file size so allocator growth cannot hide ENOSPC;
4. leave only that cluster in `avail_clusters`;
5. call `map_write(0, None)`;
6. fresh L2 consumes the only free cluster and is published to L1;
7. data allocation returns ENOSPC;
8. assert the published L2 still has refcount 0;
9. cleanly shut down metadata;
10. reopen with the real parser;
11. assert the same L1 pointer survives and the L2 address is in `avail_clusters`;
12. call `get_new_cluster(None)` and require it to return the live L2 address.

The last cell is the corruption-capability discriminator.

## Leading candidate boundary

Fresh-L2 ownership belongs inside `cache_l2_cluster_alloc()` itself.

For the empty-L1 path, establish refcount ownership **before** publishing the L1 pointer:

```text
new_addr = get_new_cluster(None)?
set_cluster_refcount_track_freed(new_addr, 1)?
publish L1 -> new_addr
create/insert fresh zero L2 cache
```

Then remove the caller-side fresh-L2 refcount work.

This helper has two current callers:

- `map_write()`;
- `deallocate_cluster(... zero_marker=true)`.

Moving ownership into the helper fixes their shared publication-before-refcount boundary instead of patching only one caller.

The existing `update_cluster_addr()` relocation transaction should stay separate: it replaces a previously-live L2 and has different old/new ordering requirements already fenced by PR 8637.

### Failure policy

If fresh-L2 refcounting fails before L1 publication, an unreferenced cluster may be temporarily leaked, but a reachable refcount-0 table is avoided.

If refcount succeeds and a later cache insertion fails after publication, the L1 points at a zero-filled valid L2 with refcount 1. That may leave a harmless empty table allocated after a failed guest write, but it preserves allocator safety.

The preferred invariant is therefore:

> establish ownership before reachability; prefer a bounded safe leak over a reachable free cluster.

## Controls

Candidate validation must keep:

- successful first write into an empty L1 slot;
- zero-marker deallocation caller behavior;
- PR 8637 failed-relocation regression;
- normal reopen free-list construction;
- no unrelated QCOW metadata rewrite.

## Evidence boundary

Source-established:

- current main retains the known deferred fresh-L2 refcount ordering;
- upstream history explicitly identifies the reopen-time gap;
- clean shutdown can persist pointer caches independently of the dropped local vector;
- clean reopen builds free clusters from zero refcounts.

Execution pending:

- deterministic exact-current ENOSPC/reopen/reuse proof;
- product candidate;
- block tests / Clippy.

No guest, production image, destructive external operation, or upstream interaction is involved.

## Authority

No upstream issue, pull request, comment, review, reaction, email, or other interaction was created by Fieldwork for this lane.
