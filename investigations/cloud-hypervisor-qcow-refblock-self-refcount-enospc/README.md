# Cloud Hypervisor QCOW refcount-block ownership ENOSPC audit

Updated: 2026-08-12
State: EXECUTED — THEORY VERIFIED, PARSER-FREE-LIST CONTROL VERIFIED
Worker/variant: LF-R609F-adjacent
Originating audit: #609 candidate failure-boundary review
Fieldwork base: `883a874568f48ea79c4341e0828c90de7bb8e260`
Latest execution carrier head: `8d854dbd767eb7a152fd36f9218baddc2ec48b62`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
Canonical Fieldwork issue: #634
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Separate theory

This is **not** the fresh-L2 bug in #609 and does not depend on the #609 candidate.

Exact-current `QcowState::set_cluster_refcount()` handles refcount-block copy-on-write roughly as:

```text
target refcount update needs replacement refcount block
-> allocate replacement block Y
-> RefCount::set_cluster_refcount(..., new_cluster=Y)
   -> publish refcount_table[region] = Y
   -> mutate cached replacement contents
-> recursively release old refcount block
-> target update is logically complete
-> recursively set refcount(Y) = 1
```

If Y lies in a different refcount region whose table entry is zero, that final ownership step itself needs another refcount block. ENOSPC there returns an error **after the refcount table already points to Y**.

Invariant under test:

> A refcount-table entry must never become durable/reachable to a refcount block while that block's own refcount is zero.

## Deterministic discriminator

The focused test uses unmodified exact-current product source plus test-only state construction. It keeps the real 64 KiB / 16-bit geometry, where one refcount block covers 32,768 clusters.

The fixture chooses:

- X = `0x40000`, a target cluster in refcount region 0;
- Y = `0x80000000`, the first cluster in refcount region 1 and the sole replacement available for the clean region-0 refblock.

It uses an in-memory two-region `RefCount` and a sparse file horizon only to make the final allocation deterministically return ENOSPC instead of depending on host disk exhaustion. It then removes the unused sparse tail before the clean-close/reopen checks.

Sequence:

1. allocate X;
2. request `refcount(X)=1`;
3. clean region-0 refblock relocates to Y and `refcount_table[0]` switches to Y;
4. X's refcount is now 1 inside Y;
5. recursive `refcount(Y)=1` needs a region-1 refblock because `refcount_table[1]==0`;
6. no cluster remains and the artificial horizon rejects extension -> ENOSPC;
7. outer call returns ENOSPC while `refcount_table[0] -> Y` and `refcount(Y)==0`;
8. clean close flushes the dirty refblock to Y, flushes the top-level refcount table, and clears DIRTY;
9. clean reopen trusts the mismatch and publishes Y to `avail_clusters`;
10. ordinary allocator returns Y and overwrites it with `0xa5` bytes while `refcount_table[0]` still points to Y;
11. clean close/reopen again sees first refcount `0xa5a5` rather than zero, so the legacy broken-refcount heuristic does not rebuild; guest-like bytes are trusted as region-0 refcounts.

## Primary execution

Workflow run: `31563576905`
Job: `94010721286`
Artifact: `9128652740` (`ch-qcow-refblock-self-refcount-enospc-r609f`)
Artifact digest: `sha256:418815ed7c6b5c2a5d4be3968bb36c2800554bd8d8a2a1f412aa5a44a19c0fc7`

All source-pin, probe-only, test discovery, focused execution, rustfmt, and `git diff --check` gates passed.

Exact witness:

```text
REFBLOCK_OWNERSHIP_FAIL pre_close target=0x40000 target_refcount=1 replacement=0x80000000 replacement_refcount=0 in_avail=false in_unref=false
REFBLOCK_OWNERSHIP_FAIL reopened table0=0x80000000 table1=0x0 target_refcount=1 replacement_refcount=0 free_contains=true free_tail=Some(0x80000000)
REFBLOCK_OWNERSHIP_FAIL allocator_reuse reused=0x80000000 table0=0x80000000 marker=[a5, a5, a5, a5, a5, a5, a5, a5]
REFBLOCK_OWNERSHIP_FAIL second_reopen table0=0x80000000 first_refcount=0xa5a5 target_refcount=0xa5a5 replacement_refcount=0 replacement_free=true
```

Focused result: `1 passed; 0 failed`.

## Parser-built free-list realism control

The first witness directly selected X/Y in `avail_clusters`. A follow-up removed that reachability objection.

The control creates a normal 4 GiB virtual QCOW image with no guest data, sparse-extends its physical file across two real 64 KiB/16-bit refcount regions, and **reopens it through the current parser before selecting X/Y**. The parser itself reported both X and Y as refcount-0/free. Only after that proof does the test reduce the parser-built free list to those two entries to force a deterministic LIFO allocation order. The same two-region max-valid horizon remains solely to make the final recursive allocation return deterministic ENOSPC.

Workflow run: `31563978567`
Job: `94011927652`
Carrier head: `8d854dbd767eb7a152fd36f9218baddc2ec48b62`
Artifact: `9128778453` (`ch-qcow-refblock-self-refcount-enospc-r609f`)
Artifact digest: `sha256:2fad8d039eb84de26ee12ceb999eaa573e8f1e3c3740b8e6f61ac49253a00436`

Every workflow gate passed, including both the original witness and the parser-free-list control plus final rustfmt / `git diff --check` hygiene.

Exact realism output:

```text
REFBLOCK_REALISM parser_free target=0x40000 target_free=true replacement=0x80000000 replacement_free=true free_count=65532
REFBLOCK_REALISM pre_close target_refcount=1 replacement_refcount=0 table0_pending=0x80000000
REFBLOCK_REALISM reopened table0=0x80000000 table1=0x0 replacement_refcount=0 free_contains=true free_tail=Some(0x80000000)
REFBLOCK_REALISM allocator_reuse reused=0x80000000 table0=0x80000000
```

Control result: `1 passed; 0 failed`.

This materially narrows the remaining artificiality: **X and Y are genuine parser-reconstructed free clusters in a valid sparse image.** The test still retains only those two proven-free entries to make allocation order deterministic, and the artificial max-valid horizon still supplies deterministic final ENOSPC. The region crossing, refcount relocation/recursion, clean shutdown, parser reopen/free-list reconstruction, and live-refblock allocator reuse are product paths.

## Countermechanisms checked

- **Same-process free-list exclusion works initially:** after ENOSPC, Y is absent from both `avail_clusters` and `unref_clusters`.
- **Clean shutdown does not roll back the refcount-table pointer:** it persists table0 -> Y and clears DIRTY.
- **Clean reopen does not reconcile refcount-table reachability with Y's refcount:** Y enters the free list because table1 says its refcount is zero.
- **DIRTY rebuild remains a potential crash-recovery defense**, but this witness deliberately follows a successful clean close, so it does not run.
- **The legacy first-cluster-refcount-zero heuristic is not a reliable post-reuse defense:** allocator reuse with nonzero guest-like bytes makes the next first refcount `0xa5a5`, and the parser trusts the overwritten block.

## Adjacent history

Upstream PR 8597 (`https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8597`) fixed a nearby runtime accounting bug: old relocated refcount blocks had their refcount dropped to zero but were not returned to `unref_clusters`. Its functional commit `02ec5b397625b626b74e1346e09eb81ea6c66a99` makes those freed old blocks reusable in-process. That change does not make a replacement refcount block own itself before publication and does not roll back a published replacement on recursive ownership failure.

PR 8637 (`https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8637`) fixed L2 relocation release-before-replacement ordering and separately documented the fresh-L2 gap tracked by #609. The refcount-block recursion here is a different metadata layer.

A search of current Cloud Hypervisor issues/PRs for QCOW refcount-block/`NeedNewCluster` ENOSPC did not find a direct existing record of this recursive self-ownership failure.

## Repair boundary

A one-line reorder is not obviously sufficient because refcount-block ownership is recursive. Setting Y's refcount before publishing table0 -> Y can itself require allocating/publishing another refcount block Z.

Minimum invariant:

> No refcount-table pointer may become durable or allocator-relevant until the pointed-to refcount block has nonzero ownership, and any failure while establishing the recursive ownership chain must leave every not-yet-owned replacement unreachable (or roll the whole pointer/refcount/free-list/cache transaction back).

Two full-repair design families are worth evaluating separately:

1. pre-resolve and own the entire refcount-block dependency chain before publishing any new `ref_table` pointer; or
2. make refcount-block relocation transactional, with rollback of `ref_table` swaps, cache mutations, ownership updates, and free-list bookkeeping on recursive failure.

A smaller **containment** direction is also worth a separate test: if a refcount mutation has partially changed metadata and then errors, poison the metadata session so final shutdown cannot clear DIRTY. Same-process free-list exclusion already keeps Y unavailable; retaining DIRTY would make writable reopen rebuild refcounts. That can block the clean-reopen allocator corruption chain, but it is recovery containment rather than the stronger ownership invariant above and must not be presented as the complete transactional repair without execution.

## Evidence limit

A natural host-disk-exhaustion workload has not been run. Deterministic tests still constrain allocator ordering and use a two-region max-valid horizon for the final ENOSPC. The parser-free-list control establishes that the critical X/Y addresses themselves arise from normal parser reconstruction rather than invented allocator membership.

## Conclusion

**VERIFIED THEORY — separate from #609, strengthened by parser-free-list control.**

Exact current main permits a refcount-block relocation to publish Y in the top-level refcount table before recursive ownership of Y succeeds. If that recursive allocation ENOSPCs, a clean close/reopen can offer still-referenced Y to the allocator. Reusing Y with nonzero guest-like bytes destroys live refcount metadata and can evade the current first-refcount-zero rebuild heuristic on the following clean reopen.
