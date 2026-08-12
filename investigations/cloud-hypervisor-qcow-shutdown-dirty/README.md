# Cloud Hypervisor — QCOW failed shutdown must retain DIRTY

Updated: 2026-08-12
State: EXECUTION QUEUED
Owning issue: #611
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
Carrier branch: `research/ch-migration-rollback-probes`
External-contact state: false; none occurred

## TL;DR

`QcowMetadata::shutdown()` currently ignores a failed `sync_caches()` and clears the QCOW DIRTY bit anyway.

That can advertise a clean close after metadata persistence failed. On reopen, Cloud Hypervisor uses DIRTY as a reason to distrust/refcount-rebuild an image; falsely clearing it can remove the recovery signal.

A deterministic block-unit fixture is queued that forces `sync_caches()` to fail through an invalid dirty L1 refcount address, then reads the raw incompatible-features field after shutdown. Current behavior should clear DIRTY and fail the regression assertion. The leading candidate clears DIRTY only after successful metadata synchronization.

## Explain like I'm five

Cloud Hypervisor puts a “work in progress” flag on a QCOW image while it is modifying metadata.

When closing cleanly, it flushes the metadata and removes the flag.

Today, even if the flush says “I failed,” shutdown still removes the flag.

The next process can then believe the image was clean when it was not.

## Why care

The DIRTY bit changes reopen behavior. Current parser logic treats a dirty writable image as having potentially-invalid refcounts and rebuilds them.

A clean marker is therefore a consistency claim, not presentation metadata.

## Current source boundary

`block/src/formats/qcow/metadata.rs`:

```text
shutdown():
    lock metadata
    ignore sync_caches() result
    if writable:
        ignore set_dirty_bit(false) result
```

`sync_caches()` can fail while flushing:

- dirty L2 pointer tables;
- dirty refcount blocks;
- file synchronization;
- L1 pointer table / copied-bit derivation;
- refcount table.

`QcowHeader::set_dirty_bit()` itself writes the incompatible-features field and fsyncs it, so a successful false clear is intentionally durable.

## Historical intent

Relevant current-history commit:

- https://github.com/cloud-hypervisor/cloud-hypervisor/commit/53ee9ebb7769626207ca7b85d7fd3f375771236f

That change correctly moved shutdown/DIRTY clearing to `Drop for QcowMetadata`, so the bit is cleared only when the last shared metadata owner disappears.

It does not condition the clean marker on successful metadata synchronization.

## Exact probe

Workflow:

```text
.github/workflows/ch-qcow-shutdown-dirty.yml
```

Run:

```text
31552073027
```

Exact test:

```text
formats::qcow::metadata::unit_tests::failed_metadata_flush_must_keep_dirty_bit_set
```

The fixture:

1. creates/parses a writable QCOW image, establishing DIRTY;
2. makes L1 dirty with a cluster pointer outside the refcount horizon;
3. proves direct `sync_caches()` returns `Err` through the private metadata seam;
4. recreates the same dirty L1 state;
5. invokes `QcowMetadata::shutdown()`;
6. reads the raw incompatible-features word at the QCOW v3 offset;
7. requires DIRTY to remain set.

Expected current baseline:

```text
metadata flush fails
shutdown ignores error
DIRTY clear succeeds
regression assertion fails
```

Positive control for any candidate: an ordinary clean shutdown must still clear DIRTY.

## Candidate

Tracked applicator:

```text
apply_candidate.py
```

Leading product behavior:

```text
if sync_caches() failed:
    warn
    return, leaving DIRTY set
otherwise:
    clear DIRTY for writable image
```

`Drop` cannot return the metadata error to the original caller, so preserving the recovery marker is the minimum correctness guarantee.

Do not turn this into a general shutdown-error propagation redesign unless another consumer provides a real caller-visible contract.

## Relation to #609

#609 is a logical metadata transaction bug: a reachable fresh L2 can retain refcount 0 even when the metadata flush itself succeeds.

This lane is different: it owns **actual flush failure followed by a false clean marker**.

Fixing #611 does not close #609. If `sync_caches()` successfully persists a logically inconsistent pointer/refcount state, DIRTY may still be cleared under #611's candidate. #609 must repair the transaction itself.

## Evidence boundary

Source-established:

- failed cache synchronization is ignored by shutdown;
- DIRTY is cleared afterward and fsynced when that operation succeeds;
- DIRTY affects refcount-rebuild policy on reopen;
- latest shutdown ownership history does not repair the error ordering.

Execution pending:

- exact-current baseline header-bit observation;
- candidate regression pass;
- block Clippy.

No production image, guest, host fault injection, or upstream interaction is involved.

## Authority

No upstream issue, pull request, comment, review, reaction, email, or other external interaction was created by Fieldwork for this lane.
