# Cloud Hypervisor QCOW refblock failure DIRTY containment audit

Updated: 2026-08-12
State: EXECUTION PENDING
Worker/variant: LF-R634C
Canonical issue: #634
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream is read-only

## Question

Can a small recovery-containment change block #634's clean-reopen allocator corruption chain without claiming to solve recursive refcount ownership transactionality?

Candidate:

1. add a per-open `refcount_update_failed` flag to `QcowState`;
2. initialize it false in `parse_qcow()`;
3. if an externally requested `set_cluster_refcount_track_freed()` returns an error, set the flag before propagating the error;
4. final-owner shutdown may still flush metadata, but must not clear DIRTY while that flag is set.

The flag is deliberately conservative: it marks any tracked refcount-update failure, even if a particular error occurred before a mutation. The safety goal is recovery containment, not leak minimization.

## Required witness

Reuse #634's real 64 KiB / 16-bit region-crossing recursive ENOSPC state:

```text
refcount_table[0] -> Y
refcount(Y) = 0
outer tracked refcount update returns ENOSPC
```

Then require:

```text
refcount_update_failed == true
final-owner shutdown leaves QCOW DIRTY set
writable reopen takes refcount rebuild path
no post-rebuild state has Y both reachable from refcount_table and allocator-free
```

A negative control must show ordinary successful open/close still clears DIRTY.

## Boundary

Passing this test does **not** prove the full #634 ownership invariant. The inconsistent refcount-table pointer can still exist and even become durable, but the image remains marked for recovery and the next writable parser rebuild must reconcile it before allocator publication.

The complete repair still needs either bottom-up ownership of the recursive refblock dependency chain before publication or transactional rollback.

This containment also intentionally does not absorb #611: unrelated `sync_caches()` failures remain a separate DIRTY-clear problem unless explicitly handled by their own repair.
