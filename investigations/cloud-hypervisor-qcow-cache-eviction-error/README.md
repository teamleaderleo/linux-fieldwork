# Cloud Hypervisor QCOW cache eviction error atomicity

Updated: 2026-08-12
State: EXECUTION PENDING
Variant: LF-R640
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only

## Question

Does a failed dirty-cache eviction discard the only in-memory dirty copy while a caller-visible metadata pointer has already changed?

Exact-current `CacheMap::insert()` removes the victim before invoking its fallible write callback. `RefCount::set_cluster_refcount()` can update `ref_table[table_index]` before calling that insertion path.

## Executable discriminator

Construct a `RefCount` directly inside its unit-test module with:

- two refcount-table regions;
- refblock-cache capacity 1;
- region 1 cached and dirty with a known refcount value not present on disk;
- region 0 empty.

Use a read-only metadata fd so the eviction callback deterministically fails when inserting a new region-0 refblock.

Current expected state after the error:

```text
ref_table[0] = new region-0 block address   # pointer already changed
dirty cached region-1 victim = absent       # only dirty copy dropped
new region-0 cache entry = absent            # insertion did not complete
```

Then reopen the same temporary file writable and run the ordinary refcount flush sequence. If `flush_blocks()` succeeds because the dirty victim is gone and `flush_table()` persists the already-changed pointer, the failure cannot be repaired merely by retrying a later normal flush.

This probe uses an intentionally read-only fd for deterministic write failure; it does not require host I/O fault injection or a real disk failure.

## Stop condition

If callback failure leaves the dirty victim resident and restores the old pointer, close the theory. If the low-level state is lossy as predicted, search/establish a canonical Fieldwork issue before proposing any repair.
