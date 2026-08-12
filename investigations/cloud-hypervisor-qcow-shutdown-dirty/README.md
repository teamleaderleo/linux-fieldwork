# Cloud Hypervisor — QCOW clean-shutdown DIRTY honesty

Updated: 2026-08-12
State: EXECUTING / CARRIER PREPARED
Owning issue: #611
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

`QcowMetadata::shutdown()` currently treats `sync_caches()` as best effort, then clears the QCOW DIRTY bit even when that metadata synchronization failed.

The parser uses DIRTY as a recovery signal: writable dirty images trigger a refcount rebuild, while clean images may trust existing refcounts and build the allocator free list directly from them. Therefore clean shutdown must not claim success after a failed metadata flush.

The first fixture makes L1 dirty with an address outside the refcount horizon. `sync_caches()` then fails deterministically during its L1 refcount lookup. Current shutdown should nevertheless clear DIRTY; the candidate returns early and leaves DIRTY set.

## Explain like I'm five

QCOW has a flag that says “the bookkeeping might not have been saved cleanly.” On a clean close, Cloud Hypervisor saves the bookkeeping and turns that flag off.

Today it effectively does:

```text
try to save bookkeeping
ignore whether that worked
turn off the warning flag anyway
```

The test makes the save definitely fail and checks that the warning flag stays on.

## Why care

A later open decides whether to rebuild refcounts partly from this bit. Clearing it after failed metadata synchronization can remove the recovery path precisely when the image needs conservative treatment.

## Exact source boundary

Current `block/src/formats/qcow/metadata.rs`:

```rust
pub(super) fn shutdown(&self) {
    let mut inner = self.inner.write().unwrap();
    let _ = inner.sync_caches();
    ...
    if raw_file.file().is_writable() {
        let _ = header.set_dirty_bit(raw_file.file_mut(), false);
    }
}
```

`sync_caches()` can fail in L2/refcount/L1 writes and sync operations. The result is not used to gate clean-bit publication.

## First executable discriminator

Inside the existing metadata unit-test module:

1. create a writable QCOW image and parse it; writable open sets DIRTY;
2. set `l1_table[0]` to `max_valid_cluster_offset + cluster_size`, marking L1 dirty;
3. call `shutdown()`;
4. inspect the incompatible-features word directly at `V2_BARE_HEADER_SIZE`;
5. require DIRTY to remain set.

The invalid L1 address is only a deterministic private test seam for a metadata-write failure. No malformed image is exposed outside the test.

Negative control: an ordinary clean shutdown still clears DIRTY.

## Candidate boundary

Only publish clean shutdown after successful metadata synchronization:

```text
if sync_caches fails:
    leave DIRTY set
    return from shutdown
else:
    clear DIRTY best effort
```

`Drop` cannot return the synchronization error, so preserving the dirty recovery marker is the minimum correctness requirement. Logging the flush failure is useful but not necessary to prove the invariant.

Keep this independent of #609. #609 is a logical pointer/refcount transaction that can make `sync_caches()` succeed while persisting inconsistent ownership; #611 covers an actual `sync_caches()` error followed by a false clean marker.

## Evidence boundary

Source-proven:

- shutdown ignores `sync_caches()` result;
- DIRTY is cleared afterward;
- parser uses DIRTY to force refcount rebuild on writable reopen.

Pending:

- focused exact-current baseline/candidate execution;
- full block and io_uring block tests;
- rustfmt/Clippy.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed.
