# Cloud Hypervisor sparse fixtures on 16 KiB-page hosts

## TL;DR

The 16 KiB failure now has a direct syscall-contract explanation in addition to the retained model. Current Cloud Hypervisor `sparse_layout()` writes 4 KiB-sized data islands, then uses `fallocate(FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE)` to punch the gaps and claims the resulting `SEEK_DATA`/`SEEK_HOLE` map will match those byte ranges regardless of backing behavior. Linux documents a narrower contract: hole punching deallocates whole filesystem blocks while partial blocks are zeroed.

On a 16 KiB-granularity memfd/tmpfs backing, the current 4 KiB gap punches can therefore zero parts of the two touched 16 KiB blocks without deallocating either block. `SEEK_DATA` can then report one allocated region from 0 through 32768, exactly matching the canonical failure.

The candidate boundary remains test-only: make the memfd sparse fixtures use host-page-sized units, keep production sparse-copy code unchanged, preserve sentinel assertions that catch over-copy, and require a real 16 KiB run before promotion.

Tracking issue: [linux-fieldwork #496](https://github.com/teamleaderleo/linux-fieldwork/issues/496)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8582

## Explain like I'm five

The test draws tiny 4 KiB islands inside a file and then asks Linux to erase the gaps around them. On a 16 KiB-backed file, erasing only one 4 KiB corner can turn those bytes into zeroes while the whole 16 KiB block still counts as allocated.

```text
requested fixture:
0----8K  data 12K------20K  data------28K

16K allocation view:
[           allocated           ][           allocated           ]
0                              16K                              32K

reported data extent:
(0, 32768)
```

Scaling the synthetic islands and gaps to the host page size gives the hole punch whole page-sized regions to remove.

## Why care

Two legitimate concerns sit here:

1. Cloud Hypervisor's unit suite can fail on 16 KiB-page Linux even when production sparse copying is behaving according to the filesystem's reported extents.
2. Weakening the assertions to accept any coalesced extent would hide real over-copy regressions. The tests should keep distinguishing sparse-copy behavior while using a representable synthetic layout.

## Current state

- State: `MECHANISM PROVEN BY SOURCE + LINUX CONTRACT; TARGET EXECUTION PENDING`
- Current upstream head inspected: `a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`
- Current `vmm/src/sparse.rs` blob: `10b9761484321c3ee0829584ad89cd126ba0dd6f`
- Candidate source commit: none yet
- Latest distinguishing result: Linux hole-punch semantics explain the exact `(0, 32768)` canonical extent from the current 4 KiB fixture on a 16 KiB allocation unit
- Cleanup state: no runtime state
- Next safe action: build a test-only page-sized fixture candidate and run focused tests on 4 KiB plus a real 16 KiB kernel
- External-contact state: `false; none occurred`

## Intent and precedent

Current source already contains a portability repair for a related sparse-fixture assumption:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/68ae56eb74b1a7e7c5fa6938b3e06712f941ee41

That change stopped relying on “never written” bytes to remain holes under shmem large-folio behavior and introduced explicit `FALLOC_FL_PUNCH_HOLE` calls.

The remaining assumption is the granularity of those writes and punches.

## Question

Can Cloud Hypervisor preserve the intended sparse-copy assertions on 4 KiB and 16 KiB-page Linux hosts by scaling only the memfd-backed test fixtures to the host page size?

## Source boundary

Project: `cloud-hypervisor/cloud-hypervisor`

Current upstream head inspected:
`a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`

Primary file:
`vmm/src/sparse.rs`

Current blob:
`10b9761484321c3ee0829584ad89cd126ba0dd6f`

Canonical issue remains open:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8582

## Current fixture mechanism

Current `sparse_layout()` does this:

1. set the file length;
2. write each requested data extent;
3. sort the data extents;
4. call `fallocate(PUNCH_HOLE | KEEP_SIZE)` for every gap;
5. later enumerate with `SEEK_DATA` / `SEEK_HOLE`.

Its source comment says the resulting extents match `data` exactly regardless of folio/THP allocation policy.

The canonical failing fixture requests:

```text
[(8192, 4096), (20480, 8192)]
```

and expects exactly those two extents.

The 16 KiB report observed:

```text
[(0, 32768)]
```

## Linux contract

Linux `fallocate(2)` documents hole punching this way:

- the requested byte range is deallocated where whole filesystem blocks can be removed;
- partial filesystem blocks in the requested range are zeroed;
- subsequent reads from the punched range return zeroes.

Reference:
https://man7.org/linux/man-pages/man2/fallocate.2.html

Linux filesystem documentation also makes clear that `SEEK_DATA` and `SEEK_HOLE` report filesystem/page-cache mappings rather than a promise to reconstruct the application's original write calls byte-for-byte:
https://www.kernel.org/doc/html/latest/filesystems/iomap/operations.html

This is the missing bridge between the current source and the canonical 16 KiB result.

## Exact 16 KiB mechanism

For the first data island `(8192, 4096)` and second `(20480, 8192)`, current `sparse_layout()` punches gaps that include 4 KiB- and 8 KiB-sized partial regions around written data.

With a 16 KiB allocation unit:

- writing bytes 8192..12288 touches the first 16 KiB unit;
- writing bytes 20480..28672 touches the second 16 KiB unit;
- punching 0..8192 is partial to the first unit;
- punching 12288..20480 crosses partial ends of the first and second units;
- punching after 28672 is partial to the second unit before later untouched space.

Those partial punches may zero bytes without deallocating the two touched units. Both units remain reportable as data, producing:

```text
[(0, 32768)]
```

The retained Fieldwork `model16k` probe independently reaches the same extent map from coarse allocation/deallocation.

## Production-code discriminator

Current production enumeration uses filesystem-reported `SEEK_DATA` / `SEEK_HOLE` boundaries. The fixed 4096 constants under this investigation live in the test fixtures and assertions.

That keeps the leading repair boundary in the tests.

A production defect should be split only if page-aligned fixtures still make `next_data_extent()` or `write_region_sparse()` return or copy the wrong ranges on a real 16 KiB host.

## Candidate boundary

Use one host-page-sized test quantum for memfd-backed sparse fixtures.

Conceptually:

```text
q = host page size

total = q * N
extents = [(q * A, q * B, byte), ...]
expectations = expressed in q units
```

The candidate should:

1. obtain the host page size through a normal Linux/Rust mechanism;
2. replace hard-coded 4096 units in the sparse memfd fixtures with that quantum;
3. keep the existing production sparse helpers byte-oriented;
4. keep sentinel-filled destination checks so copying outside the source data ranges remains observable;
5. avoid converting expected results into “whatever extents Linux returned.”

## Adjacent contexts

### `written_pages_show_as_data_extents`

Primary canonical failure. Page-sized source islands and holes should restore a deterministic representable map.

### `single_extent_at_zero_offset`

Second canonical failure. The destination sentinel already distinguishes a correct sparse copy from an over-wide copy. Scale the source fixture and byte ranges while preserving the sentinel logic.

### Named temporary files

Some sibling tests use `NamedTempFile` rather than memfd. Their filesystem allocation granularity can differ from the process page size. Avoid silently broadening the first candidate across every sparse fixture if a memfd-only change fixes the canonical failures. Treat a filesystem-backed counterexample as a separate discriminator.

### Empty and dense controls

Keep at least one empty sparse control and one dense-file control unchanged in meaning so the extent collector cannot pass simply because all layouts are classified the same way.

### Production restore path

Retain the round-trip sparse write/read tests. They protect the consumer path while the fixture generator changes.

## Reproduction retained in Fieldwork

```sh
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-sparse-page-granularity.py fixed4k
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-sparse-page-granularity.py host
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-sparse-page-granularity.py model16k
```

The model is a mechanism discriminator, not target execution.

## Required candidate gates

1. exact current upstream source identity;
2. test-only diff review;
3. focused sparse tests on a 4 KiB-page host;
4. immediate clean rerun;
5. real 16 KiB-page execution reproducing the old failure before the repair and passing after it;
6. sentinel assertions proving no over-copy around the intended source-data ranges;
7. `cargo fmt --all -- --check`;
8. ordinary project quality gate appropriate to the touched VMM unit tests.

## Evidence boundary

- The canonical issue supplies real 16 KiB target failure output.
- Linux Fieldwork has a source/history map, a 4 KiB control, and an exact 16 KiB allocation model.
- This pass adds the Linux syscall-contract explanation tying current `PUNCH_HOLE` use to the canonical extent collapse.
- Linux Fieldwork still lacks a real 16 KiB execution environment in this investigation.
- No candidate product bytes were produced in this pass.
- No claim is made that host page size is the correct quantum for every filesystem-backed sparse test; the immediate canonical failures are memfd-backed.

## Reopen / split rules

Split into production code only if a page-aligned real 16 KiB fixture demonstrates incorrect enumeration or copying.

Widen beyond memfd fixtures only if a named filesystem-backed sibling test fails with its own distinguishing allocation-granularity case.

Stop the fixture redesign if real 16 KiB execution disproves the partial-block explanation.

## Authority

No upstream issue, pull request, comment, review, or other interaction was created or modified by this Fieldwork pass.