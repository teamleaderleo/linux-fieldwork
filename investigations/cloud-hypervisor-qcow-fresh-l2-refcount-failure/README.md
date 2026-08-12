# Cloud Hypervisor QCOW fresh-L2 immediate-refcount failure audit

Updated: 2026-08-12
State: EXECUTION PENDING
Worker/variant: LF-R609F
Owning issue: #609
Fieldwork base/carrier source: `research/ch-qcow-fresh-l2-reopen-exec` at `d44a007b8395a7ffc6ffdb28815d4e2bc5bffc74`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream is read-only

## Question

The already-validated candidate moves fresh-L2 ownership into `cache_l2_cluster_alloc()` before L1 publication:

```text
new_addr = get_new_cluster(None)?
set_cluster_refcount_track_freed(new_addr, 1)?
publish L1 -> new_addr
```

This pass asks what happens when that **new immediate refcount acquisition itself fails**.

The primary safety invariant is narrower than leak-freedom:

> If fresh-L2 ownership cannot be established, the L1 pointer must remain zero. An unreferenced refcount-0 cluster may be temporarily unavailable in-process, but a clean reopen may safely rediscover it because no metadata pointer reaches it.

## Discriminator

The focused fixture extends a disposable QCOW image by exactly one cluster, replaces the in-memory `RefCount` horizon so that cluster is the highest valid address, and makes it the sole entry in `avail_clusters`.

With the ownership-before-publication candidate applied:

1. `cache_l2_cluster_alloc()` pops the sole cluster and zeroes it for the prospective L2;
2. immediate `set_cluster_refcount_track_freed(new_l2, 1)` loads the existing clean refcount block;
3. refcount relocate-on-write requests a new cluster;
4. the free list is already empty and extending past the artificial horizon returns ENOSPC;
5. the helper returns before assigning `l1_table[l1_index]`.

The test then requires:

```text
map_write -> ENOSPC
L1[0] == 0
no L2 cache entry for index 0
prospective L2 refcount == 0
prospective L2 absent from current-process avail/unref lists
clean close + clean reopen
L1[0] == 0
prospective L2 refcount == 0
reopened avail_clusters contains prospective L2
normal allocator returns that cluster safely because it is unreachable
```

This deliberately distinguishes **safe delayed reclamation** from the original #609 failure, where clean reopen returned a cluster still referenced by L1.

## Adjacent recursive-refcount audit

`QcowState::set_cluster_refcount()` can allocate replacement/new refcount-block clusters and records those addresses in `added_clusters`. After the requested target refcount is set, it recursively establishes refcount 1 for each added metadata cluster.

That means an error from `set_cluster_refcount_track_freed(new_l2, 1)` is not globally equivalent to “the L2 refcount never changed”: an error could theoretically occur after the target refcount is already 1 while recursive refcount metadata bookkeeping is still in progress. For the fresh-L2 candidate this still prevents L1 publication, so the primary L1/L2 invariant remains safe; the worst direct outcome for the prospective L2 is an unreachable allocated leak.

Whether a separately reachable refcount-block cluster can itself be left refcount 0 on such a recursive failure is a distinct refcount-metadata invariant. This carrier will not fold that separate theory into #609 without a concrete reachable state and discriminator.

## Stop condition

The ownership-before-publication candidate is narrowed but not invalidated if the focused execution shows ENOSPC leaves L1 zero and clean reopen safely reclaims the prospective L2.

If L1 becomes nonzero before the immediate refcount call returns successfully, the candidate is unsafe and must be rejected.
