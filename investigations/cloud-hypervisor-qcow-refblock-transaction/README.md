# Cloud Hypervisor QCOW recursive refcount transaction audit

Updated: 2026-08-12
State: EXECUTED — SEMANTIC REPAIR VERIFIED; CLONE IMPLEMENTATION PERFORMANCE-RISKED
Worker/variant: LF-R634R
Canonical issue: #634
Fieldwork base: `891b58d9ec6d0a6b93891ca6b9afea417ee46025`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Goal

Test a complete repair for #634's **recursive allocation ENOSPC** failure, rather than relying on the already-verified DIRTY containment.

The exact failure is:

```text
refcount update needs replacement block Y
-> ref_table is switched to Y
-> recursive refcount(Y)=1 needs another refblock
-> allocator ENOSPC
-> caller returns with Y reachable at refcount 0
```

## Candidate

Refactor `QcowState::set_cluster_refcount()` into a top-level transaction wrapper plus recursive inner helper.

The transaction is lazy:

- ordinary refcount writes that do not need a new/refcount-block replacement do not clone state;
- immediately before the first `NeedNewCluster` allocation, clone the in-memory `RefCount` state;
- share that snapshot and a list of transaction-allocated refcount-block clusters through all recursive ownership/refblock-release calls;
- if the complete recursive mutation succeeds, keep the new state;
- if allocator ENOSPC propagates, restore the pre-relocation `RefCount` snapshot and return every refcount-block cluster consumed by the failed transaction to `avail_clusters` in original LIFO order.

The candidate intentionally limits rollback to `ENOSPC`. Arbitrary cache-eviction/write I/O errors may have completed host writes and belong to a broader metadata-safety/dirty-certification problem (adjacent to #611), not to this allocation-atomicity experiment.

The refactor also propagates freed-block lists returned by recursive ownership calls. Exact-current source ignores the `Vec<u64>` returned by recursive `set_cluster_refcount(addr, 1)?` calls in the `added_clusters` ownership loop; the candidate carries those freed old refblocks back to runtime `unref_clusters`.

## Execution

Latest semantic workflow run: `31566317395`
Artifact: `9129591837`
Artifact digest: `sha256:0ae0ca04227c0f1326db82d16a923536a3732e431c6e96f2ee89ab03cde8b295`
Carrier head for that run: `55dab2965566891cfedc9cd3919f61c681d2bfd2`

All gates passed:

- exact source pin;
- candidate application and formatting;
- both semantic discriminator discoveries;
- recursive-ENOSPC rollback witness;
- successful cross-region ownership control;
- full `block` library suite: `297 passed; 0 failed`;
- `cargo clippy --locked -p block --lib -- -D warnings`;
- `cargo fmt --all -- --check`;
- `git diff --check`;
- receipt and artifact upload.

### Exact rollback witness

```text
REFBLOCK_TX_ROLLBACK post_error target=0x40000 target_refcount=0 replacement=0x80000000 replacement_refcount=0 replacement_free=true unref_count=0
REFBLOCK_TX_ROLLBACK post_sync table0=0x30000 table1=0x0 old=0x30000
REFBLOCK_TX_ROLLBACK reopened table0=0x30000 replacement_refcount=0 replacement_free=true free_tail=Some(0x80000000)
REFBLOCK_TX_ROLLBACK allocator_reuse reused=0x80000000 table0=0x30000
```

This is the decisive difference from baseline #634. After recursive ownership ENOSPC, both X and Y are back at refcount 0, Y is allocator-free, **and the top-level refcount table has been restored to the original refblock**. `sync_caches()` preserves that rollback. A normal clean shutdown can clear DIRTY, clean reopen keeps the old refblock reachable, and ordinary allocator reuse of Y no longer aliases live refcount metadata.

### Successful recursive ownership control

```text
REFBLOCK_TX_SUCCESS target=0x40000:1 y=0x80000000:1 z=0x80010000:1 old=0x30000:0 old_tracked=true
REFBLOCK_TX_SUCCESS reopened table0=0x80000000 table1=0x80010000 target=1 y=1 z=1 old=0 old_free=true
```

The successful cross-region dependency remains coherent: Y owns the region-0 replacement, Z supplies region-1 refcounts, X/Y/Z all reopen at refcount 1, and the old refblock is both rc0 and runtime-tracked for later reuse.

## Clone-cost adversarial check

The semantic transaction uses `RefCount::clone()` at the first `NeedNewCluster`. Exact current `RefCount`, `VecCache`, and `CacheMap` all clone their owned data, so this copies the in-memory top-level refcount table and cached refblocks.

A separate exact-source arithmetic workflow reproduced `header.rs::max_refcount_clusters()` and current parser limits.

Clone-cost run: `31566336451`
Artifact: `9129578250`
Artifact digest: `sha256:c3ede6017567cf391f684fe754b93fe64472e770676828742a6915ba74648698`

Adversarial but parser-accepted geometry:

```text
virtual_size=17592186044416
cluster_size=1024
refcount_bits=16
l1_clusters=1048576
refcount_table_entries=33884678
refcount_table_clone_bytes=271077424
refcount_table_clone_mib=258.520
parser_accepted=true
```

Cloud Hypervisor explicitly permits up to 16 TiB and keeps L1/refcount pointer tables in RAM subject to a 35,000,000-entry combined limit. This geometry is below that acceptance limit. Therefore a whole-`RefCount` snapshot can add a roughly 258.5 MiB top-level-table copy on a supported image before counting cached refblocks.

For default 64 KiB clusters the same cost is much smaller, but supported small-cluster images make the whole-state clone an avoidable scaling hazard. The semantic result is useful; this exact implementation should not be treated as ready to ship without addressing the copy cost.

## Required discriminators satisfied

### 1. Exact #634 failure rolls back cleanly

Real 64 KiB / 16-bit geometry with X in region 0 and Y at the first cluster in region 1 now returns ENOSPC with:

```text
refcount(X) == 0
refcount(Y) == 0
Y back in avail_clusters
refcount_table[0] restored to the original refblock
refcount_table[1] == 0
```

Normal clean shutdown/reopen is safe; DIRTY recovery is no longer required for this failure class.

### 2. Successful cross-region recursion remains coherent

With Y and Z available:

```text
refcount_table[0] -> Y
refcount_table[1] -> Z
refcount(X) = 1
refcount(Y) = 1
refcount(Z) = 1
old region-0 refblock refcount = 0
old region-0 refblock propagated to runtime unref bookkeeping
```

## Next implementation boundary

The next candidate should retain the **transaction semantics** while replacing whole-state clone with a bounded undo journal.

A useful journal boundary is:

- record only refcount-table indices whose pointer is about to change;
- record the pre-transaction dirty state of the top-level refcount table;
- invalidate touched refblock-cache entries on rollback so old copy-on-write blocks can be reloaded from their unchanged on-disk addresses;
- record old scalar refcount values only for any already-dirty refblock mutated in place during the recursive chain;
- track transaction-allocated refblock clusters for allocator restoration;
- if an error class may already have produced unrecoverable/ambiguous host writes, do not pretend it is transactionally reversible: retain DIRTY and use the already-verified recovery containment instead.

That divides responsibilities cleanly:

1. **allocator ENOSPC before irreversible host-write ambiguity:** bounded transactional rollback;
2. **I/O/cache-write failures with uncertain durable side effects:** do not clear DIRTY; force recovery.

## Disposition

**SEMANTIC REPAIR VERIFIED; WHOLE-REFCOUNT CLONE NOT RECOMMENDED AS THE FINAL IMPLEMENTATION.**

For exact #634 recursive allocation ENOSPC, restoring the pre-relocation refcount state plus transaction allocator state fully removes the reachable-refcount-0 condition and permits a normal clean close/reopen. The successful path and recursive freed-block accounting also remain correct. The current proof implementation, however, can copy hundreds of MiB on a supported small-cluster image, so a bounded journal is the appropriate next implementation step.

No upstream patch/PR/contact was made or authorized by this carrier.
