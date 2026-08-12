# Cloud Hypervisor QCOW fresh-L2 immediate-refcount failure audit

Updated: 2026-08-12
State: EXECUTED — SAFE FAILURE BOUNDARY CONFIRMED
Worker/variant: LF-R609F
Owning issue: #609
Fieldwork base/carrier source: `research/ch-qcow-fresh-l2-reopen-exec` at `d44a007b8395a7ffc6ffdb28815d4e2bc5bffc74`
Execution carrier head: `281ea4449b84171899520250fd8ee92480c3664c`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Question

The already-validated candidate moves fresh-L2 ownership into `cache_l2_cluster_alloc()` before L1 publication:

```text
new_addr = get_new_cluster(None)?
set_cluster_refcount_track_freed(new_addr, 1)?
publish L1 -> new_addr
```

This pass asked what happens when that **new immediate refcount acquisition itself fails**.

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

## Execution

Workflow run: `31563175285`
Job: `94009568361`
Artifact: `9128513264` (`ch-qcow-fresh-l2-refcount-failure-r609f`)
Artifact digest: `sha256:77d390f050c84ed6a69bbac3d1031fb8f18cb4090709c5141b4203390049de6a`
Runner: Ubuntu 24.04.4

All source-pin, candidate-application, probe, discovery, focused-test, rustfmt, and `git diff --check` gates passed.

Focused output:

```text
FRESH_L2_REFCOUNT_FAIL pre_close prospective_l2=0x40000 l1=0x0 refcount=0 in_avail=false in_unref=false
FRESH_L2_REFCOUNT_FAIL reopened prospective_l2=0x40000 l1=0x0 refcount=0 free_contains=true free_tail=Some(0x40000)
FRESH_L2_REFCOUNT_FAIL allocator_return reused=0x40000 prospective_l2=0x40000 l1=0x0
```

The test passed: `1 passed; 0 failed`.

## Result

**The ownership-before-publication candidate survives the immediate-refcount ENOSPC boundary.**

The prospective fresh L2 is consumed and temporarily absent from both free lists in the failing process, but L1 remains zero and no L2 cache entry is published. Clean close/reopen rediscovers the refcount-0 cluster and the ordinary allocator returns it. That reuse is safe because the cluster is unreachable.

This is the desired asymmetry compared with the original #609 baseline:

```text
original bug:  reachable + refcount 0 -> reopen reuse is corruption
candidate failure: unreachable + refcount 0 -> reopen reuse is reclamation
```

So the minimum correctness requirement is ownership-before-reachability, not immediate leak-free rollback of every failed allocation.

## Adjacent recursive-refcount audit

`QcowState::set_cluster_refcount()` can allocate replacement/new refcount-block clusters and records those addresses in `added_clusters`. After the requested target refcount is set, it recursively establishes refcount 1 for each added metadata cluster.

Therefore an error from `set_cluster_refcount_track_freed(new_l2, 1)` is not globally equivalent to “the L2 refcount never changed”: an error can occur after the target refcount is already 1 while recursive refcount-metadata ownership is still in progress. For the fresh-L2 candidate this still prevents L1 publication, so the primary L1/L2 invariant remains safe; the direct prospective-L2 outcome can at worst be an unreachable allocated leak.

Source review also exposed a separate, stronger question: a newly published **refcount-block** address can be installed into the refcount table before its own recursive refcount ownership is established. If that recursive ownership crosses into a refcount-table region that itself needs a new block and then ENOSPCs, the refcount table may remain pointed at a refcount-0 cluster. That is a distinct metadata invariant and is being tested independently rather than folded into #609 without execution.

## Conclusion

For #609's fix boundary: **VERIFIED SAFE FAILURE ORDERING**.

The candidate should retain:

```text
allocate/zero fresh L2
-> establish refcount ownership
-> publish L1
-> permit later fallible mapping work
```

An ownership failure before publication may defer reclamation, but it does not recreate the reachable-free corruption class.
