# Cloud Hypervisor — QCOW clean-shutdown DIRTY honesty

Updated: 2026-08-12
State: EXECUTED — THEORY AND MINIMUM CANDIDATE VERIFIED
Owning issue: #611
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; none occurred

## TL;DR

Exact current `QcowMetadata::shutdown()` can encounter a real `sync_caches()` error and still clear the QCOW DIRTY bit through the final-owner `Drop` path. The executed baseline observed exactly that false-clean transition.

The minimum candidate is also verified: if metadata synchronization fails, log the failure and return without clearing DIRTY. With that change, the same failure leaves DIRTY set, writable reopen takes the normal recovery path, and a later successful close clears DIRTY. Ordinary clean shutdown still clears DIRTY. Default and io_uring block suites, Clippy, rustfmt, and diff hygiene all pass.

## Explain like I'm five

QCOW has a warning flag that says “my bookkeeping might not have been saved cleanly.”

Exact current behavior was proven to do this:

```text
save bookkeeping -> FAILS
turn warning flag off anyway
```

The candidate changes it to:

```text
save bookkeeping -> FAILS
leave warning flag ON
next writable open repairs/rechecks bookkeeping
successful later close turns warning flag off
```

## Why care

A later writable open uses DIRTY as a recovery signal. Clearing it after failed metadata synchronization can remove the recovery path precisely when the image needs conservative treatment.

This is the non-reversible-I/O complement to #634's bounded allocator-ENOSPC rollback:

```text
allocator ENOSPC with reversible in-memory metadata transaction
    -> bounded journal rollback
    -> clean close can remain truthful

metadata synchronization failure / uncertain durable side effects
    -> retain DIRTY
    -> force writable recovery
```

## Exact source boundary

Exact-current `block/src/formats/qcow/metadata.rs`:

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

`Drop for QcowMetadata` calls `shutdown()`, so this is the final-owner clean-close certification path.

`sync_caches()` contains normal fallible metadata operations: L2/refcount writes, syncs, L1 publication with refcount lookup, and refcount-table flush. Exact current does not use that result to gate DIRTY clearing.

## Deterministic failure fixture

The probe uses only a private metadata-unit seam:

1. create and parse a writable QCOW image, which sets DIRTY;
2. set cached `l1_table[0]` to one cluster beyond `max_valid_cluster_offset`, marking L1 dirty;
3. explicitly call `sync_caches()` and require an error during the L1 refcount lookup;
4. confirm raw header DIRTY is still set immediately after that error;
5. drop the final `QcowMetadata` owner, exercising production `Drop -> shutdown()`;
6. observe the raw incompatible-features word.

The malformed cached pointer is never exposed as a user image fixture. It is a deterministic way to force the product metadata synchronization path to fail while the file remains writable, so the subsequent DIRTY-header write can still succeed and expose the ordering bug.

## Authoritative execution

Workflow run: `31568421826`
Job: `94025021918`
Tested Fieldwork carrier head: `db58511c1fb2cd544eae3a0fdb4d8d54e714cd7d`
Artifact: `9130362465`
Artifact digest: `sha256:8aac975ecc3fc0318cade9660e7440265abe6e086a42e888c1aeb6131f31cfdb`
Exact source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4

The workflow runs the baseline and candidate in the same job. After the unmodified baseline, it hard-resets to the exact source SHA before applying the candidate.

All authoritative gates passed:

- exact source pin;
- unmodified-source baseline probe discovery and execution;
- candidate application after hard reset;
- candidate failure/recovery probe;
- ordinary clean-close control;
- full default block library suite: `297 passed; 0 failed`;
- full io_uring block library suite: `325 passed; 0 failed`;
- `cargo clippy --locked -p block --lib --features io_uring -- -D warnings`;
- `cargo fmt --all -- --check`;
- `git diff --check`;
- receipt/artifact upload.

## Exact baseline result

```text
QCOW_SHUTDOWN_BASELINE sync_error kind=Other raw=None dirty_before_drop=true
QCOW_SHUTDOWN_BASELINE post_drop dirty=false
```

The baseline first proves `sync_caches()` really failed while DIRTY was still set. Final-owner Drop then ran exact-current shutdown, swallowed the repeated failure, and successfully wrote `DIRTY=false`.

This removes the source-only uncertainty from #611: the false-clean state is reachable in an executed product path.

## Minimum candidate

The tested product change is intentionally small:

```rust
if let Err(e) = inner.sync_caches() {
    log::warn!("Failed to synchronize QCOW metadata during shutdown: {e}");
    return;
}
```

Only after successful synchronization does existing writable-image logic attempt `set_dirty_bit(..., false)`.

`Drop` cannot propagate the synchronization error to its caller, so retaining DIRTY is the minimum correctness action. Logging is useful observability; the safety property is the early return before clean certification.

## Exact candidate result

```text
QCOW_SHUTDOWN_CANDIDATE sync_error kind=Other raw=None dirty_before_drop=true
QCOW_SHUTDOWN_CANDIDATE post_failed_drop dirty=true
QCOW_SHUTDOWN_CANDIDATE recovery_close dirty=false
```

The same deterministic synchronization failure now survives final-owner Drop with DIRTY still set. A real writable `parse_qcow()` reopen succeeds and takes the dirty-image recovery path. Dropping that recovered metadata after successful synchronization then clears DIRTY normally.

## Clean-close negative control

```text
QCOW_SHUTDOWN_CONTROL post_drop dirty=false
```

So the candidate does not make DIRTY sticky: normal successful shutdown still publishes a clean image.

## Invariant

> A writable QCOW image may clear DIRTY on final-owner shutdown only after metadata synchronization has completed successfully. If `sync_caches()` fails, shutdown must preserve DIRTY so a later writable open takes recovery/rebuild rather than trusting potentially partial metadata as clean.

## Relation to #609 and #634

This does not replace logical ownership fixes.

#609 can have `sync_caches()` succeed while persisting a logically inconsistent fresh-L2/refcount pair, so conditioning DIRTY clearing on sync success does not fix #609.

#634's recursive allocator-ENOSPC class now has a separately verified bounded transaction that can restore the pre-transaction logical state and then cleanly close. #611 is the complementary class where the metadata synchronization operation itself failed and durable state may be ambiguous; that case should not be certified clean.

## Carrier-history correction

The reused `research/ch-qcow-shutdown-dirty` branch existed before this execution and had **zero workflow runs**. I initially described its candidate as stale because I thought exact current had moved away from the `RwLock::write()` shutdown form. That was incorrect: exact current still uses `self.inner.write().unwrap()` and the old candidate patch shape already matched it.

What was stale was the **evidence state**, not that lock API. This pass tightened the old probe to explicitly prove the `sync_caches()` error and use final-owner Drop, then executed baseline/candidate/regressions on exact current.

## Scope / remaining hardening boundary

This proves the minimum conditional-clear candidate for an actual metadata synchronization error. It does not guarantee that the process can always repair an arbitrary storage failure during the same shutdown; the point is precisely not to erase the recovery signal when synchronization could not be certified.

A broader metadata-safety design could eventually combine:

- transient per-session poison from propagated metadata mutation failures;
- actual `sync_caches()` success/failure;
- DIRTY clearing only when all clean-certification conditions hold.

But #611 does not need that larger refactor to establish its minimum invariant.

## Disposition

**VERIFIED THEORY / MINIMUM CANDIDATE VERIFIED.**

Exact current can clear DIRTY after a demonstrated `sync_caches()` failure. Gating clean certification on successful synchronization prevents that state, preserves real writable-reopen recovery, leaves ordinary clean close unchanged, and passes default/io_uring block suites plus Clippy/format/diff hygiene.

No upstream issue, pull request, comment, review, email, reaction, or other interaction occurred or is authorized by this carrier.
