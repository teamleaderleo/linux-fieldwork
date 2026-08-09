# Cloud Hypervisor sparse fixtures on 16 KiB-page hosts

## TL;DR

The canonical 16 KiB failure is strongly explained by a **test-fixture granularity mismatch**: the tests request 4 KiB memfd data/hole extents, while a 16 KiB-granularity backing can only keep the two touched 16 KiB regions allocated. A retained model produces the exact upstream extent `(0, 32768)`. The next step is a fixture-only candidate followed by real 4 KiB and 16 KiB target execution.

Tracking issue: [linux-fieldwork #496](https://github.com/teamleaderleo/linux-fieldwork/issues/496)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8582

## Explain like I'm five

The test draws little 4 KiB islands of data in a file and expects holes around them. A machine that handles the memory-backed file in 16 KiB pages cannot always remove just one 4 KiB corner of a page. Both 16 KiB pages touched by the test stay allocated, so Linux reports one 32 KiB island instead.

```text
wanted:   hole | 4K data | hole | 8K data | hole
16K host: [        allocated       ][     allocated     ]
result:   data from 0 through 32768
```

## Why care

This can make legitimate 16 KiB Linux hosts fail Cloud Hypervisor's unit suite even when production sparse copying is correct. Some sibling tests may also become weaker if an over-wide copy adds only zero bytes that their assertions already expect.

## Current state

- State: `SCOPING`
- Exact working head: documentation branch only; no owned-fork source candidate yet
- Latest authoritative gate or artifact: Fieldwork `model16k` mechanism probe; current 4 KiB control matches the existing fixture
- First incomplete step: build fixture-only source candidate
- Cleanup state: no mutable runtime state
- Next safe action: change only memfd-backed test fixture quantum, then run focused tests on 4 KiB
- External-contact state: `false; none occurred`

## Intent and precedent

Current source already contains a portability repair for a related sparse-fixture assumption:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/68ae56eb74b1a7e7c5fa6938b3e06712f941ee41

That change explicitly punched gaps with `FALLOC_FL_PUNCH_HOLE` because shmem large-folio allocation made "never written" an unreliable proxy for a hole. The retained 4 KiB coordinates are the remaining portability assumption under investigation.

## Question

Can Cloud Hypervisor's sparse-file tests preserve their intended sparse-copy assertions on both 4 KiB and 16 KiB-page Linux hosts by scaling **test fixtures only** to the host page size?

## Source

- Project: `cloud-hypervisor/cloud-hypervisor`
- Requested revision: current `main` at scout time
- Resolved commit: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- Candidate source commit: none yet
- Primary path: `vmm/src/sparse.rs`
- Fieldwork scout: https://github.com/teamleaderleo/fieldwork/pull/772

## Environment

### Local/model evidence

- Architecture: ordinary x86_64 runner
- Host page size: 4 KiB for live control
- Privileges: unprivileged memfd + `fallocate(PUNCH_HOLE)`
- Network: not required

### Required platform evidence

A real 16 KiB-page Linux kernel is still required for target execution.

## Baseline behavior

The upstream report's `written_pages_show_as_data_extents` requests:

```text
[(8192, 4096), (20480, 8192)]
```

and observes:

```text
[(0, 32768)]
```

Current production code enumerates whatever extents the filesystem reports through `SEEK_DATA` / `SEEK_HOLE`; fixed 4096-byte coordinates are in the unit fixtures and their assertions rather than an obvious production chunking invariant.

## Hypothesis or candidate

Leading candidate:

```text
host page size
      ↓
test fixture quantum
      ↓
page-aligned memfd data + punched-hole coordinates
      ↓
existing sparse-copy implementation unchanged
```

Keep sentinel assertions that can detect over-copy. Do not "fix" the test by accepting arbitrary coalesced extents, because that can hide a dense or over-wide copy path.

## Reproduction

Retained no-network probe in Fieldwork:

```sh
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-sparse-page-granularity.py fixed4k
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-sparse-page-granularity.py host
python3 programmes/open-source-ecosystems/scouts/foundational-systems/artifacts/cloud-hypervisor-sparse-page-granularity.py model16k
```

The 16 KiB model deliberately models only coarse allocation/deallocation of the current fixture; it is not claimed as filesystem execution.

## Results

The 16 KiB model maps the current requested extents to:

```text
[(0, 32768)]
```

which exactly equals the upstream-reported extent list.

On the ordinary 4 KiB control, the current fixture's requested and observed extents match.

## Interpretation

**Demonstrated model behavior:** 16 KiB allocation granularity is sufficient to explain the exact reported failure shape.

**Source-supported interpretation:** the leading repair boundary is the test fixture, not production sparse-copy code.

**Open question:** a real 16 KiB kernel must show that page-sized fixtures restore the intended sparse tests without exposing a separate production defect.

## Evidence boundary

- No real 16 KiB target run has been executed by Linux Fieldwork.
- The canonical issue supplies the real observed 16 KiB failure.
- No candidate source patch exists yet.
- No claim is made about every filesystem's `SEEK_HOLE` granularity.

## Next step

Prepare one boring owned-fork candidate from current canonical `main` that changes only the sparse unit fixture coordinates/expectations needed to use the host page size. Then run focused tests on 4 KiB and obtain a real 16 KiB run before any upstream packet is considered.

## Authority

No upstream issue, pull request, comment, review, or other interaction has been authorized or created by this investigation.