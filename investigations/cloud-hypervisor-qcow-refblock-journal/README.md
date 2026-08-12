# Cloud Hypervisor QCOW bounded refcount undo-journal audit

Updated: 2026-08-12
State: EXECUTION PENDING
Worker/variant: LF-R634J
Canonical issue: #634
Fieldwork base: `891b58d9ec6d0a6b93891ca6b9afea417ee46025`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remains read-only

## TL;DR

The whole-`RefCount` transaction proved the right #634 semantics but can copy roughly 258.5 MiB on a parser-accepted small-cluster image. This variant keeps the same rollback contract while journaling only refcount regions actually touched by the recursive transaction.

The first candidate deliberately uses **per-region cache-block snapshots**, not a whole refcount-table snapshot. If that survives the primary ENOSPC and success controls, the next adversarial gate is cache eviction / pre-existing dirty cache state. A green two-region test alone is not enough.

## Explain like I'm five

The old proof fix took a photocopy of the whole bookkeeping binder before changing one or two pages. That was safe but can be huge. This version copies only the pages it is about to scribble on. If the operation runs out of space, it puts those pages back and returns any temporary pages it borrowed.

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

## Initial discriminators

### Recursive ENOSPC rollback

Reuse the exact 64 KiB / 16-bit cross-region #634 fixture:

```text
X: externally allocated target in region 0
Y: only refblock allocation available, located in region 1
recursive refcount(Y)=1 -> needs another refblock -> ENOSPC
```

Require immediately after error and after normal clean close/reopen:

```text
refcount(X) = 0
refcount(Y) = 0
refcount_table[0] = original region-0 block
refcount_table[1] = 0
Y allocator-free
normal allocator reuse of Y does not alias refcount metadata
```

### Successful recursion control

With Y and Z available require:

```text
refcount_table[0] -> Y
refcount_table[1] -> Z
refcount(X) = 1
refcount(Y) = 1
refcount(Z) = 1
old region-0 block refcount = 0 and runtime-tracked as freed
```

## Adversarial follow-up required before recommendation

The per-region journal must then be attacked with a cache that already contains dirty refblocks and with cache pressure that can evict entries during the transaction. If rollback cannot recover from a transaction-era cache write without ambiguous durable state, that error class must retain DIRTY and use recovery rather than being described as transactionally reversible.

The stop condition for this first unit is either:

- the bounded journal passes semantic + cache-state discriminators and full regressions; or
- a precise cache/eviction counterexample shows the journal boundary is still too weak.

No upstream patch, PR, comment, or issue interaction is authorized by this carrier.
