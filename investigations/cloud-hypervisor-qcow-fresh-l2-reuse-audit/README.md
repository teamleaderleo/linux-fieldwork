# Cloud Hypervisor QCOW fresh-L2 reuse audit

Updated: 2026-08-12
State: EXECUTING
Canonical issue: #609
Worker: LF-R609C
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

This is an independent adversarial check of the fresh-L2 theory in #609. The source ordering allows a fresh L2 to be zero-filled and wired into L1 while its refcount increment remains deferred in `map_write()`. The primary discriminator here goes beyond free-list membership: after an ENOSPC unwind, clean close, and real parser reopen, call the normal data-cluster allocator and test whether it returns and overwrites the exact cluster still referenced by L1.

A paired negative control persists the same mismatched L1 while leaving the QCOW DIRTY bit set. Exact-current `parse_qcow()` should then rebuild refcounts from L1/L2 reachability and keep the live L2 out of the allocator. That distinguishes the claimed clean-close boundary from dirty-image recovery.

## Bounded question

Can exact-current Cloud Hypervisor reach all of these states in sequence?

1. fresh L2 allocated and zero-filled;
2. L1 updated to point at it;
3. later `map_write()` allocation fails before the local deferred fresh-L2 refcount is applied;
4. fresh L2 refcount remains zero;
5. clean shutdown flushes the L1/L2 caches and clears DIRTY;
6. clean reopen classifies the live L2 as free;
7. `append_data_cluster()` subsequently returns that exact L2 address and writes guest-data bytes over the table.

## Competing explanation / negative control

A dirty reopen has an explicit recovery path. If the mismatched L1 reaches disk while DIRTY remains set, `parse_qcow()` rebuilds refcounts by walking the L1 and L2 tables. The control expects the reachable L2 to recover refcount 1 and stay out of `avail_clusters`.

If that control fails, the theory needs a wider refcount-recovery audit. If the clean case fails because another owner restores ownership or excludes the cluster, #609 needs correction.

## Probe design

The injected exact-current block tests use two appended physical clusters and cap the refcount horizon at that file size. `avail_clusters` is ordered so the higher appended cluster becomes the fresh L2. The lower cluster is consumed by subsequent data/refcount work, causing ENOSPC before `map_write()` reaches its deferred refcount loop.

Clean arm:

- record L1 -> fresh L2 and refcount 0 immediately after ENOSPC;
- drop through `QcowMetadata`, invoking production `shutdown()`;
- verify DIRTY is clear;
- reopen with `parse_qcow()`;
- verify L1 still points at the same L2, refcount is 0, and free list contains it;
- call `append_data_cluster()` with a marker-filled data cluster and assert it returns the same live-L2 address;
- verify marker bytes physically overwrote the cluster while L1 still names it.

Dirty control:

- reach the same ENOSPC mismatch;
- call `sync_caches()` so the L1 pointer is durable while DIRTY stays set;
- drop the raw `QcowState` without `QcowMetadata::shutdown()`;
- reopen through `parse_qcow()`;
- verify rebuild gives the live L2 refcount 1 and excludes it from the free list.

## Evidence boundary

Pending exact execution. No product candidate is applied by this branch. The branch exists only to run a distinguishing baseline and a dirty-recovery control on exact-current upstream source.
