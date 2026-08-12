# Cloud Hypervisor QCOW recursive refcount transaction audit

Updated: 2026-08-12
State: EXECUTION PENDING
Worker/variant: LF-R634R
Canonical issue: #634
Fieldwork base: `891b58d9ec6d0a6b93891ca6b9afea417ee46025`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remains read-only

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

The refactor also propagates freed-block lists returned by recursive ownership calls. Current exact source ignores the `Vec<u64>` returned by `self.set_cluster_refcount(addr, 1)?` in the `added_clusters` ownership loop, potentially stranding old refblocks freed by those recursive relocations until reopen.

## Required discriminators

### 1. Exact #634 failure must roll back cleanly

Use real 64 KiB / 16-bit geometry with:

- target X in region 0;
- Y at the first cluster in region 1;
- only Y available to the recursive metadata transaction;
- deterministic two-region allocation horizon.

After recursive ownership ENOSPC require:

```text
refcount(X) == 0
refcount(Y) == 0
Y back in avail_clusters
refcount_table[0] restored to the original refblock
refcount_table[1] == 0
```

Then allow **normal clean shutdown** (DIRTY should clear), reopen, and prove ordinary allocator reuse of Y is safe because the refcount table no longer points to it.

### 2. Successful cross-region recursion must remain coherent

Provide both Y and Z:

- Y replaces the clean region-0 refblock;
- Z becomes the new region-1 refblock;
- Z owns Y and itself.

Require after success/reopen:

```text
refcount_table[0] -> Y
refcount_table[1] -> Z
refcount(X) = 1
refcount(Y) = 1
refcount(Z) = 1
old region-0 refblock refcount = 0 and allocator-discoverable
```

The old refblock must also be propagated into runtime `unref_clusters` before close, exercising the recursive freed-list bookkeeping fix.

## Acceptance boundary

A green semantic candidate is not automatically product-ready. `RefCount::clone()` duplicates the top-level refcount table and cache on each first post-flush relocation. If the functional gates pass, the next review must quantify whether that copy cost is acceptable or whether the same transaction needs a smaller per-region undo journal.

No upstream patch/PR/contact is authorized by this carrier.
