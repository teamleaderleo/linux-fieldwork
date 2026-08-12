# Cloud Hypervisor QCOW metadata failure-policy integration

Updated: 2026-08-12
State: EXECUTION PENDING
Variant: LF-R611634I
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Related canonical issues: #611, #634
External-contact state: false; Cloud Hypervisor upstream remains read-only

## Goal

Integrate the two independently verified QCOW metadata failure policies on one exact-current build:

1. **#634 allocator ENOSPC while recursively owning refcount metadata** — bounded per-region undo journal restores the pre-transaction logical state, so clean close remains truthful.
2. **#611 metadata synchronization failure** — shutdown must not certify the image clean; retain DIRTY so writable reopen takes recovery.

Both changes touch `block/src/formats/qcow/metadata.rs`, so independent green runs are not enough by themselves. This carrier tests that the policies compose rather than masking or weakening each other.

## Required split

```text
reversible allocator ENOSPC
    -> journal touched refcount regions + transaction allocations
    -> restore before shutdown
    -> sync_caches succeeds
    -> DIRTY may clear

metadata synchronization failure / uncertain durable effects
    -> sync_caches fails
    -> shutdown returns before DIRTY clear
    -> writable reopen uses recovery
```

The integration is rejected if the #611 gate makes rolled-back #634 sessions unnecessarily dirty, or if #634 rollback causes #611's actual sync failure to be mistaken for a reversible transaction.

## Gates

Apply the already-executed #634 bounded-journal candidate and its three discriminators, then apply the already-executed #611 conditional-clear candidate and its two candidate controls. Run all five focused tests on the same product tree, then the default and io_uring block suites, Clippy, rustfmt, and diff hygiene.

No new upstream-facing patch or interaction is authorized by this carrier.
