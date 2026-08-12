# Cloud Hypervisor QCOW bounded refcount undo-journal audit

Updated: 2026-08-12
State: EXECUTED — BOUNDED JOURNAL VERIFIED FOR ALLOCATOR ENOSPC
Worker/variant: LF-R634J
Canonical issue: #634
Fieldwork base: `891b58d9ec6d0a6b93891ca6b9afea417ee46025`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; Cloud Hypervisor upstream remained read-only

## TL;DR

The earlier whole-`RefCount` transaction proved the right #634 semantics but can copy roughly 258.5 MiB on a parser-accepted small-cluster image. This variant retains the same allocator-ENOSPC rollback contract while journaling only refcount regions actually touched by the recursive transaction.

The bounded journal passed the original recursive ENOSPC witness, the successful cross-region ownership control, and a stronger adversarial case with a pre-existing dirty sibling refblock plus forced transaction-era cache eviction. After rollback, normal `sync_caches()`, clean shutdown, and clean reopen all retained the pre-transaction topology and ownership state. The full block library suite passed with 298 tests, plus Clippy, rustfmt, and diff hygiene.

This result is deliberately scoped to **allocator ENOSPC**. Arbitrary I/O or cache-write errors may have ambiguous durable side effects and should retain DIRTY / force recovery rather than being described as transactionally reversible.

## Explain like I'm five

The old proof fix took a photocopy of the whole bookkeeping binder before changing one or two pages. That was safe but can be huge. This version copies only the pages it is about to scribble on. If the operation runs out of space, it puts those pages back and returns any temporary pages it borrowed.

The hard test also made one copied page dirty and forced another page out of the cache while the failed edit was happening. Restoring those touched pages and flushing them again still repaired the book correctly.

## Why care

#634 is allocator corruption, not just a leaked cluster: a live refcount block can become allocator-free after clean reopen. The repair needs to prevent that state without adding an avoidable hundreds-of-megabytes copy to supported QCOW images.

## Invariant

> Recursive refcount allocation ENOSPC must restore every refcount-table pointer and touched cached refblock to its pre-transaction logical state, and every refblock cluster allocated only by the failed transaction must become allocator-free again.

A successful recursive ownership chain must remain unchanged.

## Candidate boundary

The candidate adds a `RefcountUndo` object inside `refcount.rs`.

At the first `NeedNewCluster`, the metadata layer starts one undo transaction and shares it through recursive refcount ownership/release calls. `RefCount` records a region only before its first transaction mutation:

- old top-level refcount-table pointer for that region;
- prior cached refblock, if one existed;
- whether the top-level refcount table was dirty before the transaction.

The transaction also records every refblock cluster allocated through `get_new_cluster()`.

On allocator ENOSPC:

1. remove current cache entries for journaled regions;
2. restore their old refcount-table pointers;
3. restore prior cached blocks, marking them dirty so any transaction-era eviction write is corrected by the next metadata flush;
4. restore the refcount-table dirty bit to its pre-transaction state;
5. return transaction-only allocations to `avail_clusters` in original LIFO order.

This is bounded by touched refcount regions rather than the complete refcount table. The candidate also preserves the earlier proof fix that propagates freed old refblocks returned by recursive ownership calls instead of discarding them.

The only compatibility shim left by the experiment is `#[cfg(test)]`: existing parser unit tests call the old lower-level `RefCount::set_cluster_refcount()` directly. Normal library code uses the journal-aware entry point, so production Clippy does not carry an obsolete wrapper.

## Authoritative execution

Workflow run: `31567656438`
Job: `94022729916`
Carrier head: `abf99a82f9e66f1cbbb20323f5d04822520429cf`
Artifact: `9130076035`
Artifact digest: `sha256:df74d01e689f655d221e0dc97a51d13c34c834258adbe42eca34751b6c23e838`
Source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4

All authoritative-run gates passed:

- exact source pin;
- candidate application and no-whole-`RefCount`-clone assertion;
- primary rollback / successful recursion / adversarial eviction test discovery;
- recursive ENOSPC rollback;
- successful recursive ownership control;
- dirty-sibling + forced-eviction rollback control;
- full block library suite: `298 passed; 0 failed`;
- `cargo clippy --locked -p block --lib -- -D warnings`;
- `cargo fmt --all -- --check`;
- `git diff --check`;
- receipt and artifact upload.

### 1. Recursive ENOSPC rollback

Exact output:

```text
REFBLOCK_JOURNAL_ROLLBACK post_error target=0x40000 target_refcount=0 replacement=0x80000000 replacement_refcount=0 replacement_free=true unref_count=0
REFBLOCK_JOURNAL_ROLLBACK post_sync table0=0x30000 table1=0x0 old=0x30000
REFBLOCK_JOURNAL_ROLLBACK reopened table0=0x30000 replacement_refcount=0 replacement_free=true free_tail=Some(0x80000000)
REFBLOCK_JOURNAL_ROLLBACK allocator_reuse reused=0x80000000 table0=0x30000
```

After recursive ownership ENOSPC, X and Y both return to refcount 0, Y is allocator-free, and `refcount_table[0]` is restored to its original block. A normal metadata sync and normal clean shutdown can then persist that restored topology. Clean reopen safely exposes Y to the allocator because nothing references it.

### 2. Successful recursion control

Exact output:

```text
REFBLOCK_JOURNAL_SUCCESS target=0x40000:1 y=0x80000000:1 z=0x80010000:1 old=0x30000:0 old_tracked=true
REFBLOCK_JOURNAL_SUCCESS reopened table0=0x80000000 table1=0x80010000 target=1 y=1 z=1 old=0 old_free=true
```

The successful chain remains coherent: table0 points to Y, table1 points to Z, X/Y/Z all reopen at refcount 1, and the replaced old region-0 refblock is rc0 and propagated to runtime free bookkeeping.

### 3. Dirty sibling + forced cache eviction

This test is intentionally more hostile than the original #634 witness.

First it creates a successful two-region state (`table0 -> Y`, `table1 -> Z`) with both refblock caches dirty. It then selectively writes only region 0 so region 0 is clean while region 1 remains a pre-existing dirty sibling. Cache capacity is reduced to two entries.

The second transaction then:

1. relocates clean region 0 from Y to A;
2. recursively releases Y by mutating the already-dirty region-1 block;
3. recursively owns A, creating region-2 metadata and forcing cache eviction at capacity two;
4. recursively owns that new refblock, crosses into region 3, and deterministically ENOSPCs.

Exact output:

```text
REFBLOCK_JOURNAL_EVICT post_error target1=1 target2=0 y=1 z=1 a=0 b=0 free=[
    0x180000000,
    0x100000000,
]
REFBLOCK_JOURNAL_EVICT post_sync table=[
    0x80000000,
    0x80010000,
    0x0,
    0x0,
]
REFBLOCK_JOURNAL_EVICT reopened table=[
    0x80000000,
    0x80010000,
    0x0,
    0x0,
] target1=1 target2=0 y=1 z=1 a=0 b=0 a_free=true b_free=true
```

This closes the obvious cache-state objection to the first journal design: a transaction-era eviction can write speculative dirty contents, but restoring the captured touched cache blocks as dirty causes the following normal `sync_caches()` to reassert the pre-transaction logical state before the top-level table is committed. Clean reopen then sees the original Y/Z topology, original ownership, and both failed transaction allocations free.

## Iteration evidence retained

The first journal run (`31567109716`) already passed the product semantics and the then-297-test block suite, but failed Clippy on two candidate-shape issues: an old lower-level wrapper was dead in normal library code, and two `Option<&mut _>` sites used a needless `as_deref_mut()`.

Removing the wrapper entirely then broke existing parser **unit tests**, which directly call that lower-level method. That was not a product semantic failure. The final candidate keeps it under `#[cfg(test)]` and uses `as_mut()`.

An initial adversarial-probe sketch was also discarded before any result was counted because it accidentally flushed both refblock caches, destroying the intended pre-existing-dirty-sibling condition. The authoritative run uses the corrected selective-flush probe.

These failed/scaffold iterations are retained to make the final green result auditable rather than silently erasing negative evidence.

## Scope and remaining boundary

**This validates a bounded transactional implementation family for allocator ENOSPC. It does not prove arbitrary I/O errors can be rolled back safely.**

The journal can repair speculative cache writes when a later allocator ENOSPC occurs and ordinary repair writes succeed. A write/eviction failure is different: the system may not know which host writes completed, and rollback writes may themselves fail. That failure class should be conservative about clean-shutdown certification.

The natural next boundary is therefore the existing shutdown/DIRTY issue #611:

```text
reversible allocator ENOSPC
    -> bounded journal rollback
    -> normal clean close is allowed

metadata/cache I/O failure with ambiguous durable effects
    -> retain DIRTY
    -> writable reopen rebuilds/reconciles before allocator publication
```

## Disposition

**BOUNDED JOURNAL VERIFIED FOR #634 ALLOCATOR-ENOSPC TRANSACTIONALITY.**

Compared with the whole-`RefCount` proof, this preserves the verified rollback semantics without copying the entire top-level refcount table. It also survives a pre-existing dirty sibling cache, forced transaction-era cache eviction, normal `sync_caches()`, clean shutdown/reopen, full block regressions, Clippy, formatting, and diff hygiene.

The next hardening unit is not “journal every error.” It is to verify #611 and make clean-shutdown certification depend on successful metadata synchronization so non-reversible I/O failures retain the recovery signal.

No upstream patch, PR, comment, or issue interaction occurred or is authorized by this carrier.
