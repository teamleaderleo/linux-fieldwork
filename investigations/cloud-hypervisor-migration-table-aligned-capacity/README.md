# Cloud Hypervisor migration table aligned-capacity review

Updated: 2026-08-12
State: EXECUTION PENDING
Variant: LF-R637
Canonical issue: #637
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Internal #604 candidate head: `a9ff8e0ca603f72e6fb718fc023b679201ce04c5`
External-contact state: false; upstream remains read-only

## Question

Can a syntactically aligned peer-provided `MemoryRangeTable` length still panic the receiver during vector capacity construction, including after the narrow #604 unaligned-length candidate?

## Discriminator

Use `length = u64::MAX - 15`, which is divisible by the 16-byte `MemoryRange` record size on the 64-bit hosted runner.

Run `MemoryRangeTable::read_from()` with an empty `Cursor` under `catch_unwind(AssertUnwindSafe(...))` and require a panic. This value is chosen to trip Rust vector capacity checks before any real giant allocation, avoiding an intentional OOM workload.

Run the same integration test against:

1. exact current upstream source;
2. internal clean #604 candidate `a9ff8e0c...`.

If both panic, the aligned-capacity problem is distinct from #604's malformed unaligned framing.

## Stop condition

If either parser returns a normal `MigratableError` instead of panicking, inspect that exact error path and narrow or close #637 rather than assuming the theory.
