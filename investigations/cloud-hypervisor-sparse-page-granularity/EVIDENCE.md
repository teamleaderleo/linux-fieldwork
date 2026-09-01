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

The branch was created directly from the current canonical head. No source bytes have been applied to it yet.

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

## Refined candidate boundary

Tracked patch:
`candidate.patch`

Fieldwork patch commit:
`fb9dbb1574d5099c5bfa7fb36af91eaac602b2ce`

Patch blob:
`0f7217609d9a66df3af5a1fa94c9fbaee626c219`

The candidate is test-only and changes only tests that manufacture holes through `sparse_layout()`.

It adds:

```rust
fn test_page_size() -> u64 {
    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    assert!(page_size > 0, "sysconf(_SC_PAGESIZE) failed");
    page_size as u64
}
```

The synthetic sparse layouts then keep their existing topology in host-page units.

### Deliberately unchanged 4 KiB controls

Three tests retain fixed 4096-byte coordinates:

- `empty_memfd_has_no_data_extents`;
- `enumeration_respects_window`;
- `dense_file_yields_single_extent`.

This is intentional.

Those tests do not depend on `PUNCH_HOLE` deallocating a synthetic gap. In particular, `enumeration_respects_window` keeps a 4 KiB start and end inside a fully populated file. On a 16 KiB host that remains a sub-page byte window, so the test continues to prove that production `next_data_extent()` clamps to arbitrary byte ranges instead of inheriting the fixture page quantum.

This is a stronger candidate than blindly replacing every 4096 constant.

### Scaled sparse-layout tests

The candidate scales:

- `written_pages_show_as_data_extents`;
- `sparse_file_yields_extents_at_written_positions`;
- `single_extent_at_zero_offset`;
- `two_regions_in_same_destination_file_at_dst_offset`;
- `extent_at_non_zero_src_offset`;
- `round_trip_sparse_write_then_read`.

For each one, source data islands, punched gaps, destination offsets, expected extents, and byte-content assertions move together.

## Compatibility / donut checks

### Sentinel over-copy check

`single_extent_at_zero_offset` still pre-fills the destination with `0xFE`. Only the intended page-scaled source data window may change. This continues to catch an over-wide sparse copy even when the extra bytes would otherwise read as zero.

### Arbitrary-byte window

`enumeration_respects_window` remains fixed at 4 KiB units and is outside the candidate diff. This guards the byte-oriented production API while the sparse fixture generator becomes page-aware.

### Non-zero source offset

The source data location, selected source window, and expected destination-relative content all scale together. The data remains four logical pages into the selected region.

### Multi-region destination offsets

Both source fixtures and the second destination offset scale together, preserving the translation `dst_offset + (data_off - src_offset)`.

### Round trip

Source layouts, region table, snapshot length, and final byte assertions scale together. The dense-read oracle remains unchanged.

## Patch carrier validation

The tracked unified diff was generated from exact current test bytes and checked against a synthetic file retaining the exact affected source contexts and line positions.

Local analysis result:

```text
git apply --check candidate.patch -> 0
```

The applied synthetic result confirms:

- production-prefix bytes are unchanged;
- `test_page_size()` is present;
- sparse-layout coordinates use the page quantum;
- the fixed 4 KiB arbitrary-window control remains present.

This is patch-carrier validation only. No Rust compiler or rustfmt executable is available in the current local execution environment, so no Cargo/rustfmt result is claimed.

## Required execution

Before promotion:

1. apply the patch to the current-base source carrier;
2. run focused sparse unit tests on a normal 4 KiB host;
3. run them again immediately as a clean rerun;
4. run nightly rustfmt and the appropriate VMM quality gate;
5. execute the old and candidate fixtures on a real 16 KiB-page kernel;
6. confirm the old fixture reproduces the reported collapse while the page-sized candidate passes;
7. retain exact source, run, job, and artifact identities.

## Stop / split condition

If a real 16 KiB run still produces incorrect extents with base-page-aligned `sparse_layout()` fixtures, split the resulting filesystem/production behavior into a successor.

If a named filesystem-backed test fails because its deallocation unit exceeds the host page size, treat that as its own filesystem discriminator instead of weakening expected extents globally.

## External-contact state

`false; none occurred during this continuation.`
