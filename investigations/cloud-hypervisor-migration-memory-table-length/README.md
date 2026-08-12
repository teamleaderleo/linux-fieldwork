# Cloud Hypervisor migration memory-table length validation

Updated: 2026-08-12
State: PROVEN / CANDIDATE READY FOR INDEPENDENT REVIEW
Owning issue: #604
Worker/variant: LF-R604E
Fieldwork base: `891b58d9ec6d0a6b93891ca6b9afea417ee46025`
Validated review-carrier head: `23b84700185e58ef421af8bfebf129207c31c159`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; no third-party interaction is authorized or performed

## TL;DR

Exact-current `MemoryRangeTable::read_from()` panics when peer-provided table length is not divisible by the 16-byte `MemoryRange` record size. A deterministic `length = 1` parser fixture reproduces the panic while valid zero-length and one-record controls pass.

A narrow candidate converts malformed framing into `MigratableError::MigrateReceive`, preserves valid decoding, passes the full `vm-migration` crate tests and Clippy, and has been reduced to a one-file review payload with one regression test.

## Proven baseline behavior

The exact-current baseline witness calls `MemoryRangeTable::read_from()` with `length = 1` inside `catch_unwind` and records:

```text
assertion failed: (length as usize).is_multiple_of(size_of::<MemoryRange>())
MALFORMED_TABLE_BASELINE panicked=true
```

The paired ordinary-error invariant exits `101` on baseline because the peer-controlled malformed length unwinds through the assertion instead of returning a migration receive error.

The controls pass unchanged:

- `length = 0` decodes an empty table;
- one complete encoded `MemoryRange` decodes and round-trips its GPA/length.

This establishes the defect directly at the parser called by the receive path, without KVM or guest dependencies.

## First hosted execution and failure classification

Run `31567765911`, job `94023063834`, Fieldwork head `11936ead89317f69db54f242dd6bf3975c3704a6` reached the product discriminator successfully:

- source pin: pass;
- probe/test discovery: pass;
- valid controls: pass;
- baseline panic witness: pass;
- baseline ordinary-error invariant: expected red, correctly classified;
- candidate materialization: failed before candidate execution.

The failure owner was the Fieldwork materializer: it expected `Ok(MemoryRangeTable { data })` while exact current source uses `Ok(Self { data })`. No product conclusion was drawn from that carrier failure. Artifact `9130112157`, digest `sha256:14cd9e97e61653f0a2634b10d315500e51e2336fd3d1d0de35adacb4f31791df` retains the baseline evidence.

## Proof candidate execution

After repairing only the materializer, run `31567847397`, job `94023322769`, Fieldwork head `a57c140ddd3591f6669cfd41e64dc59a43c8b66d` completed successfully.

The candidate changes `MemoryRangeTable::read_from()` to:

```text
checked u64 -> usize conversion
-> reject non-record-aligned length with MigrateReceive
-> allocate whole MemoryRange records
-> read_exact as before
```

Results:

- baseline panic witness: pass;
- baseline invariant: expected red;
- candidate malformed-length invariant: pass;
- candidate zero-length control: pass;
- candidate one-record control: pass;
- `cargo test --locked -p vm-migration`: 24 passed, 0 failed, 1 intentionally ignored baseline witness;
- `cargo clippy --locked -p vm-migration --all-targets -- -D warnings`: pass;
- rustfmt and `git diff --check`: pass.

Artifact `9130147878`, digest `sha256:ec50fa696fb57fa9fec7f0047cd3abc14c37773d75f28ba820bd8eab446b209f` retains the complete proof matrix. Candidate-only diff digest: `sha256:e2a4cf56b59f814ed08e4d1d2e13119d3c8508559abbec4d893d0166a289851b`.

## Review-ready candidate

The final review payload starts from untouched exact upstream source and contains only the production change plus one regression in the existing `protocol::unit_tests` module.

Run `31567983769`, job `94023745563`, Fieldwork head `23b84700185e58ef421af8bfebf129207c31c159` validates that exact payload:

```text
vm-migration/src/protocol.rs | 21 +++++++++++++++++++--
1 file changed, 19 insertions(+), 2 deletions(-)
```

The regression is `protocol::unit_tests::test_memory_range_table_rejects_unaligned_length` and requires `MemoryRangeTable::read_from(..., 1)` to return `MigrateReceive`.

Review-payload gates:

- focused regression: pass;
- `cargo test --locked -p vm-migration`: 22 passed, 0 failed;
- `cargo clippy --locked -p vm-migration --all-targets -- -D warnings`: pass;
- rustfmt: pass;
- `git diff --check`: pass;
- final changed source: only `vm-migration/src/protocol.rs`.

Review patch SHA-256: `ec4e378fdbc928a3ec9e3f44627567eb58c6cab9fe122a745cc57f8169740dfa`.

Artifact `9130196219`, digest `sha256:c71beae676aef59eaf1d8de9dc0f00d0303fea3723a57b17b6e26cb0e47afe7c` retains the exact patch and logs.

## Exact commands

```text
cargo test --locked -p vm-migration --lib \
  protocol::malformed_memory_range_table_length_tests::malformed_memory_range_table_length_panics_baseline \
  -- --ignored --exact --nocapture

cargo test --locked -p vm-migration --lib \
  protocol::malformed_memory_range_table_length_tests::malformed_memory_range_table_length_returns_error \
  -- --exact --nocapture

cargo test --locked -p vm-migration
cargo clippy --locked -p vm-migration --all-targets -- -D warnings
cargo fmt --all -- --check
git diff --check
```

The review-only carrier separately runs:

```text
cargo test --locked -p vm-migration --lib \
  protocol::unit_tests::test_memory_range_table_rejects_unaligned_length \
  -- --exact --nocapture
cargo test --locked -p vm-migration
cargo clippy --locked -p vm-migration --all-targets -- -D warnings
```

## Evidence boundary

Established:

- malformed peer framing with `length = 1` panics exact-current parser code;
- valid empty and one-record tables remain valid;
- the local validation candidate converts that malformed framing into `MigrateReceive`;
- the review-ready one-file candidate passes focused, crate, Clippy, rustfmt, and diff gates.

Outside this proof:

- full VMM/socket migration integration;
- resource limits for very large but record-aligned table lengths;
- a hosted 32-bit target exercising the checked `u64 -> usize` overflow arm.

Those change the input/resource premise and should be separate discriminators. The current repair is deliberately limited to malformed record framing and checked host-size conversion.

## Cross-context receipt

- caller/consumer: receive path passes peer request length into this parser; no divisibility guard was found before the parser;
- representation: malformed framing loses on baseline while zero-length and one-record wire representations pass;
- history: recent protocol changes concern serialization and migration error logging; no current upstream repair or duplicate for this malformed-length panic was found in the bounded search;
- adjacent lane: Fieldwork #580 is truncated memory content after syntactically valid framing and remains separate.

Reopen if upstream main changes this parser, a caller-level framing validator appears, or a broader resource-limit claim is proposed.

## Tooling note

An accidental empty internal Fieldwork issue #636 was created by connector routing while preparing the carrier. It was immediately renamed, documented as an interaction artifact, and closed. It carries no technical result and #604 remains canonical.

## Disposition

**PROVEN / CANDIDATE READY FOR INDEPENDENT REVIEW**
