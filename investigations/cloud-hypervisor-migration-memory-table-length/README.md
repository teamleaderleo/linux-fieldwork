# Cloud Hypervisor migration memory-table length validation

Updated: 2026-08-12
State: EXECUTING
Owning issue: #604
Worker/variant: LF-R604E
Fieldwork base: `891b58d9ec6d0a6b93891ca6b9afea417ee46025`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; no third-party interaction is authorized or performed

## TL;DR

Exact-current `MemoryRangeTable::read_from()` asserts that peer-provided payload length is divisible by the 16-byte `MemoryRange` record size. This carrier executes a panic witness, a paired ordinary-error invariant, valid zero-length and one-record controls, then tests a local validation candidate.

## Question

Does malformed migration framing such as `length = 1` panic the parser on exact current source, and does replacing that assertion with ordinary `MigrateReceive` validation preserve valid table decoding?

## Exact source boundary

`Request.length` is wire data. `MemoryRangeTable::read_from(fd, length)` currently begins with:

```text
assert!((length as usize).is_multiple_of(size_of::<MemoryRange>()))
```

It then allocates `length / size_of::<MemoryRange>()` records and reads their encoded bytes.

No current upstream issue or pull request found during the bounded search describes this malformed-length panic. Related Fieldwork #580 concerns truncated memory payload progress after syntactically valid framing and is a separate failure phase.

## Probe matrix

The exact-source probe adds four unit tests in `vm-migration/src/protocol.rs`:

- ignored baseline witness: `length=1` must currently be caught as a panic;
- paired invariant: malformed length must return `MigrateReceive` without unwinding;
- zero-length control: empty table remains valid;
- full-record control: one encoded `MemoryRange` round-trips unchanged.

The ignored witness gives the mechanism a losing mode while keeping the ordinary suite suitable for the candidate.

## Candidate

The local candidate performs a checked `u64 -> usize` conversion, validates record divisibility, and returns `MigratableError::MigrateReceive(anyhow!(...))` for invalid framing. The rest of the table read remains unchanged.

Large but aligned allocation limits are outside this candidate. They require a separate resource-bound discriminator.

## Execution gates

The hosted workflow runs the exact source with Rust 1.89.0, formats the injected tests, discovers every named test, proves the baseline panic witness, proves the paired invariant is red on baseline, applies the candidate, then runs:

```text
cargo test --locked -p vm-migration
cargo clippy --locked -p vm-migration --all-targets -- -D warnings
cargo fmt --all -- --check
git diff --check
```

Logs and complete probe/candidate diffs are retained as an artifact.

## Evidence boundary

Source/history: current and refreshed.
Product execution: pending hosted fixture.
Candidate execution: pending hosted fixture.
Full VMM receive-migration socket integration: outside the first proof; the unit seam is the parser directly called by the receive path.

## Disposition rule

- PROVEN if exact-current baseline catches the malformed length as a panic and the paired invariant loses there.
- FALSIFIED if the exact-current parser returns an ordinary error without unwinding.
- CANDIDATE READY FOR INDEPENDENT REVIEW if the validation candidate passes the focused matrix, full `vm-migration` tests, Clippy, rustfmt, and diff hygiene.
- REPAIR if the carrier fails before the parser discriminator executes.
