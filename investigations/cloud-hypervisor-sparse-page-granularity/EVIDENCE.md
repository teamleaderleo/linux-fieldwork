# Cloud Hypervisor sparse page-granularity — continuation evidence

Updated: 2026-08-11

## Current source boundary

Canonical Cloud Hypervisor head inspected:
`a658c9f9fd0c4e0363004361d73ac8733fa24fd0`

Primary path:
`vmm/src/sparse.rs`

Current blob:
`10b9761484321c3ee0829584ad89cd126ba0dd6f`

Owned-fork source carrier:
`teamleaderleo/cloud-hypervisor:linux-fieldwork/sparse-page-granularity`

The branch was created directly from the current canonical head. No product or test bytes have been committed to it yet.

## Canonical failure

Canonical issue 8582 reports `written_pages_show_as_data_extents` on a 16 KiB-page kernel returning:

```text
[(0, 32768)]
```

instead of the fixture's requested:

```text
[(8192, 4096), (20480, 8192)]
```

It also reports `single_extent_at_zero_offset` overwriting bytes before the expected 4 KiB-based source-data window.

## Linux operation owner

The source fixtures use `memfd_create()`. Memfd files use shmem, so the relevant hole-punch owner is Linux shmem rather than Cloud Hypervisor's sparse-copy loop.

Linux's `fallocate(FALLOC_FL_PUNCH_HOLE)` contract says partial filesystem blocks are zeroed while whole filesystem blocks are removed. Current shmem hole-punch code derives the removable interior by rounding the requested byte range to `PAGE_SIZE` boundaries.

That gives the exact discriminator for the 16 KiB report:

- fixture writes and gaps are expressed in 4 KiB units;
- a 16 KiB shmem base page can contain several of those units;
- punching a sub-page gap zeroes bytes but leaves the containing page allocated;
- `SEEK_DATA` can therefore still report that page as data;
- the two touched 16 KiB pages collapse into the observed `[0, 32768)` data extent.

This is stronger than the earlier abstract quantization model because it identifies the kernel operation that performs the rounding.

Primary references retained in the investigation:

- Linux `fallocate(2)` deallocation semantics: partial blocks zeroed, whole blocks removed;
- Linux shmem `shmem_fallocate()` implementation: full-hole interior rounded to `PAGE_SIZE`;
- Linux tmpfs/shmem documentation: tmpfs lives in the page cache and current kernels can use large folios/multi-size THP.

## Relationship to the prior upstream hardening

Cloud Hypervisor commit `68ae56eb74b1a7e7c5fa6938b3e06712f941ee41` already fixed a different allocation assumption. Before that change, writing a few bytes into a shmem fixture could allocate a large folio and make untouched pages appear as data. The accepted repair introduced `sparse_layout()` and explicitly punched every gap.

That repair correctly moved the test toward an explicit deallocation operation, but it kept every synthetic coordinate at a fixed 4096-byte quantum. Its claim that the resulting `SEEK_DATA` / `SEEK_HOLE` layout matches the requested extents regardless of backing behavior therefore still depends on those punched gaps containing full deallocatable units.

The 16 KiB report is the adjacent counterexample.

## Current test audit

The fixed 4096-byte unit appears throughout the sparse unit suite:

- empty memfd length;
- written-page extent locations and expected extents;
- enumeration window;
- dense-file size;
- named-temp sparse extent fixture;
- source and sentinel windows in `single_extent_at_zero_offset`;
- both sources and destination offsets in the two-region test;
- non-zero source-offset test;
- both sources, snapshot regions, and final content assertions in the round-trip test.

Several of those tests use memfd sources. Some named temporary files may also live on tmpfs depending on `TMPDIR`/host configuration. Fixing only the two reported assertions would leave sibling 4 KiB assumptions in the same helper family.

## Candidate boundary

Keep production code unchanged.

Add one test helper that reads the host base page size through `sysconf(_SC_PAGESIZE)` and rejects an invalid result. Express synthetic fixture sizes, offsets, lengths, expected extents, destination offsets, and byte-range assertions as multiples of that value.

Conceptually:

```rust
fn test_page_size() -> u64 {
    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    assert!(page_size > 0);
    page_size as u64
}
```

Each test then preserves its current logical layout in pages:

```text
old: 4096 * 2, 4096 * 1, 4096 * 5, 4096 * 2
new: page * 2, page * 1, page * 5, page * 2
```

This keeps the same relative topology while ensuring the memfd/shmem gaps can contain complete base pages on 4 KiB and 16 KiB kernels.

## Compatibility / donut checks

### Sentinel over-copy check

Keep `single_extent_at_zero_offset` pre-filling the destination with `0xFE`. Scale its byte windows by the host page size. This continues to distinguish the correct sparse write from a dense/over-wide copy whose extra bytes happen to be zero.

### Window semantics

`enumeration_respects_window` should keep the same logical four-page window inside a fully populated file. Scaling the coordinates must preserve the `SEEK_DATA`/`SEEK_HOLE` window-clamping contract rather than merely making the sparse fixtures pass.

### Non-zero source offset

Scale both the source data location and the requested source window. The expected destination-relative location must remain four pages into the selected window.

### Multi-region destination offsets

Scale the destination offset between the two copied regions as well as source fixtures. This protects the translation `dst_offset + (data_off - src_offset)` rather than only source extent discovery.

### Round trip

Scale source fixtures, region table, destination length, and final byte-content assertions together. Preserve the dense-read oracle.

### Named temporary files

Using base-page multiples is safe for the current intended Linux filesystems and keeps tmpfs-backed `TMPDIR` cases aligned with the shmem rule that owns the reported failure. A future filesystem with a different hole-punch allocation unit would be a separate discriminator rather than justification to weaken extent assertions.

## Stop condition

The test-only candidate remains the leading answer while:

1. page-sized fixtures pass the ordinary 4 KiB environment;
2. a real 16 KiB kernel reproduces the old fixture failure and passes the page-sized candidate;
3. production sparse helpers remain unchanged;
4. sentinel, offset, and round-trip controls retain their distinguishing power.

If a real 16 KiB run still produces incorrect extents with base-page-aligned fixtures, split the resulting production/filesystem behavior into a successor instead of broadening this candidate blindly.

## Required execution

Before promotion:

1. apply the test-only change to the current-base source carrier;
2. run focused sparse unit tests on a normal 4 KiB host;
3. run them again immediately as a clean rerun;
4. run nightly rustfmt;
5. execute the old and candidate fixtures on a real 16 KiB-page kernel;
6. confirm the source diff changes only test code in `vmm/src/sparse.rs`;
7. retain exact current head, job/artifact identity, and evidence limits.

## External-contact state

`false; none occurred during this continuation.`
