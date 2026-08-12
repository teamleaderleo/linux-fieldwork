# Cloud Hypervisor — QCOW fresh-L2 ENOSPC reopen refcount

Updated: 2026-08-12
State: EXECUTING / SOURCE BOUNDARY MAPPED
Owning issue: #612
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

Merged upstream PR 8637 fixed an in-run QCOW double-allocation path but explicitly left a reopen-time gap: a fresh metadata cluster can be wired into tables while its refcount increment remains only in a caller-local deferred vector. A later ENOSPC error drops that vector. Current main still has that ordering.

The smallest current case is a brand-new L2 table. `cache_l2_cluster_alloc()` allocates the L2 and immediately updates L1, then returns the new address so `map_write()` can defer `(new_l2, 1)`. If the subsequent data-cluster allocation fails, L1 keeps the pointer and the refcount stays zero.

Clean shutdown persists L1 and clears the DIRTY bit. Clean reopen therefore skips refcount rebuild and constructs `avail_clusters` from zero refcounts, making the still-referenced L2 allocator-eligible.

The first executable gate is a block-unit fixture that forces exactly this sequence and asserts the clean reopen does **not** publish the L2 as free. Current baseline should fail; the narrow candidate makes the fresh-L2 refcount durable before L1 wiring.

## Explain like I'm five

QCOW has a map that points to little index pages called L2 tables. It also keeps a counter saying which disk blocks are in use.

Current code can do this:

```text
reserve block for new L2
point the map at it
plan to set its used-counter later
run out of space before “later”
```

When the VM closes cleanly, the map is saved but the counter is still zero. Next time the image opens, zero means “free”, so the allocator can hand out a block that the map is still using.

## Why care

This is a latent metadata double-allocation path. The original ENOSPC operation can return an ordinary error, yet a later clean reopen can make live metadata eligible for overwrite.

The failure class matches the dangerous family investigated under upstream issue 8606, where reused live metadata led to silent guest filesystem corruption.

## Historical intent

Public context:

- https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8606
- https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8637
- https://github.com/cloud-hypervisor/cloud-hypervisor/commit/a5e145bdefe72f3f4a7dd98186aee50f5e2fdf2b

PR 8637 explicitly says the same ENOSPC unwind can drop a deferred refcount update for a cluster already wired into tables, naming a fresh L2 from `cache_l2_cluster_alloc()` as an example. It deliberately left that larger transactional problem out of scope.

Current source still has the fresh-L2 deferred-refcount ordering. The only later reviewed commit touching `metadata.rs`, `53ee9ebb...`, changes when the DIRTY bit is cleared; it does not repair the wiring/refcount transaction.

## Exact current source

### `map_write()`

Current ordering:

```text
set_refcounts = []
if cache_l2_cluster_alloc(...) returns new_l2:
    set_refcounts.push((new_l2, 1))

allocate/map data cluster ?
update L2 ?

for deferred refcounts:
    apply
```

Any `?` after the fresh L2 is wired can discard the local vector.

### `cache_l2_cluster_alloc()`

When L1 has no L2 yet:

```text
new_addr = get_new_cluster(None)?
l1_table[l1_index] = new_addr
insert empty L2 cache
return Some(new_addr)
```

The durable ownership counter is not changed here.

### Clean shutdown/reopen

`QcowMetadata::shutdown()` calls `sync_caches()` and clears DIRTY.

`parse_qcow()` on a clean writable image builds `avail_clusters` by scanning the on-disk refcount table and including every cluster whose refcount is zero.

So the defect crosses a process lifetime boundary.

## First executable fixture

The fixture stays inside `block/src/formats/qcow/metadata.rs` and uses the existing QCOW test helpers.

1. Create and cleanly close a fresh QCOW image.
2. Parse it to `QcowState`; L1[0] is zero.
3. Extend the host file by one cluster and cap the refcount horizon at that exact file size.
4. Put only that one appended cluster in `avail_clusters`.
5. Call `map_write(0, None)`.
6. Expected current sequence:
   - the sole free cluster becomes the new L2 and is wired into L1;
   - the data-cluster allocation cannot extend past the capped horizon and returns ENOSPC;
   - the local deferred `(new_l2, 1)` update is dropped.
7. Wrap/drop `QcowMetadata` to use the normal clean-shutdown path.
8. Reopen with `parse_qcow()`.
9. Assert the reopened L1 still points to the L2 but the allocator does **not** list it as free and its refcount is 1.

Baseline should fail on the free-list/refcount invariant. Candidate should pass.

## Candidate boundary

For the fresh-L2 path only:

```text
allocate L2
set L2 refcount = 1
wire L1
insert cache
```

`cache_l2_cluster_alloc()` should own that transaction instead of returning the address for a deferred caller-side increment.

If the immediate refcount update fails, do not wire L1. A leaked newly allocated cluster is safer than a durable pointer to a refcount-zero cluster.

This first candidate deliberately does not change relocated-L2 old-cluster release. That adjacent path should be tested separately because its best failure behavior is likely “new table refcount committed, old table refcount release deferred/leaked on failure.”

## Evidence boundary

Established:

- exact current source retains the fresh-L2 deferred-refcount ordering;
- clean shutdown can persist L1 while clearing DIRTY;
- clean reopen builds the free list from refcount zero;
- upstream history explicitly identifies this as a known remaining gap.

Pending:

- deterministic exact-current baseline;
- candidate focused test;
- full block tests, io_uring block tests, rustfmt, Clippy;
- relocated-L2 adjacent error test.

## Next step

Execute the exact-current fresh-L2 ENOSPC/reopen fixture. If it fails as source predicts, apply the immediate-refcount candidate and run block crate gates.

## Authority

No upstream issue, pull request, review, comment, email, reaction, or other external interaction is authorized or performed by this investigation.
