# Execution receipt — truncated migration memory payload

Date: 2026-08-12
Owning issue: #580
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `1.89.0`
External-contact state: false; none occurred

## Result

The truncated `Command::Memory` payload zero-progress loop is executable on exact current source.

Focused test:

```text
migration::transport::truncated_payload_tests::receive_memory_ranges_rejects_truncated_payload
```

Baseline was run under a five-second harness deadline and timed out:

```text
BASELINE_RC=124
running 1 test
```

This confirms `receive_memory_ranges()` can stay in its manual retry loop after the peer closes before the declared payload is complete.

## Candidate

The candidate adds one local progress check after `read_volatile_from()`:

```text
bytes_read == 0 -> ordinary MigrateReceive error
```

The focused test then passes immediately.

## Gates

- run: `31550880817`
- job: `93973144031`
- artifact: `9124468956`
- artifact digest: `sha256:0a3a742d2039e666c28568a003bcbe406ae8c806ab7954cded75d6956c776f1d`
- focused candidate test: pass
- rustfmt: pass
- Clippy: pass with only the unrelated current-base `unfulfilled-lint-expectations` warning explicitly suppressed; every other warning remains denied

## Boundary

This closes only the closed/truncated-payload subcase. A connected peer that stalls mid-payload still requires an abort-aware cancellation discriminator, and terminal receive/event finalization is a separate control-flow issue in #580.
