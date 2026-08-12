# Cloud Hypervisor — migration memory-table framing validation

Updated: 2026-08-12
State: EXECUTION QUEUED
Owning issue: #604
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
Carrier branch: `research/ch-migration-rollback-probes`
External-contact state: false; none occurred

## TL;DR

`MemoryRangeTable::read_from()` currently uses an `assert!` to require that a peer-provided migration payload length is a whole number of `MemoryRange` records. A malformed `Command::Memory` frame can therefore panic the receiver instead of producing a protocol error.

A three-cell exact-current unit probe is queued:

1. misaligned length `1` must return `Err` without panic;
2. length `0` remains a valid empty table;
3. one complete 16-byte `MemoryRange` remains decodable.

The minimal candidate replaces the assertion with checked `u64 -> usize` conversion and explicit record-divisibility validation, returning `MigratableError::MigrateReceive` for malformed framing.

## Explain like I'm five

A migration message says how many bytes of table data follow. Every table row has one fixed size.

Today Cloud Hypervisor says:

```text
this length had better be exactly made of whole rows — assert!
```

For bytes arriving from another process, it should instead say:

```text
this length is malformed — return an error
```

A bad message should end the migration request, not crash the VMM thread.

## Why care

Migration protocol input is fallible input. Internal assertions are appropriate for invariants already proven inside the process; a wire length has not earned that trust.

The defect is independent of #580's truncated-payload loop. #580 starts with a valid table and then ends the memory bytes early. This lane fails before table decode because the table framing itself is malformed.

## Current state

- State: `EXECUTION QUEUED`
- Exact working head: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- Source blob: `vm-migration/src/protocol.rs` at current head
- Workflow: `.github/workflows/ch-migration-memory-table-length.yml`
- Run: `31550954550`
- First incomplete step: exact-current baseline/candidate execution
- Cleanup state: no runtime resources created
- External-contact state: false; none occurred

## Source boundary

`Request.length` is decoded from the migration request header as `u64`.

`MemoryRangeTable::read_from(fd, length)` currently begins:

```rust
assert!((length as usize).is_multiple_of(size_of::<MemoryRange>()));
```

It then allocates `length / size_of::<MemoryRange>()` records and reads the table bytes.

`receive_memory_ranges()` passes the `Command::Memory` request length directly to this parser.

No caller-side check establishes record divisibility first.

## Probe

Tracked applicator:

```text
apply_probe.py
```

Exact test name:

```text
protocol::unit_tests::malformed_memory_range_table_length_returns_error_without_panic
```

The malformed cell uses `catch_unwind` around:

```text
MemoryRangeTable::read_from(Cursor::new([]), 1)
```

The assertion in the test requires the call itself not to panic and then requires an ordinary `Err`.

Baseline discriminator:

```text
current source assertion panics
catch_unwind catches panic
test fails because malformed input did not return normally
```

Controls execute in the same test:

```text
length=0 -> empty table
length=size_of::<MemoryRange>() -> exact record round trip
```

## Candidate

Tracked applicator:

```text
apply_candidate.py
```

Candidate behavior:

```text
checked usize conversion
if length % sizeof(MemoryRange) != 0:
    return MigrateReceive(error)
allocate/read table otherwise
```

The checked conversion is local to the same parser and avoids silent truncation on a hypothetical narrower target without introducing a new protocol policy.

## Deliberate non-scope

Do not bundle:

- arbitrary maximum migration message sizes;
- memory allocation quotas;
- generic protocol fuzzing;
- unrelated asserts in internal-only paths;
- truncated memory content after a valid table (#580).

Large-but-aligned payload length resource limits may deserve a separate lane, but they are not required to fix this panic.

## Evidence boundary

Source-established:

- wire length is externally supplied;
- parser asserts record divisibility;
- receive path forwards the wire length directly;
- normal `MigrateReceive` error plumbing already exists.

Execution pending:

- current exact panic observation;
- candidate test;
- rustfmt;
- vm-migration Clippy.

No claim is made about untrusted Internet exposure or production exploitability. This is a migration-protocol robustness boundary exercised only with synthetic local input.

## Next step

Consume run `31550954550`, record exact baseline/candidate output and artifact identity, and keep the product scope inside `vm-migration/src/protocol.rs` if the discriminator wins.

## Authority

No upstream issue, pull request, comment, review, reaction, email, or other external interaction is authorized or performed.
