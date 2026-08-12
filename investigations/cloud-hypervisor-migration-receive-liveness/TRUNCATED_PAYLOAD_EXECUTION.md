# Cloud Hypervisor truncated migration payload — execution receipt

Updated: 2026-08-12
Owning issue: #580
Exact upstream source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Carrier branch: `research/ch-migration-rollback-probes`
External-contact state: false; none occurred

## TL;DR

The truncated-memory-payload failure is now reproduced on exact current Cloud Hypervisor source with a focused in-tree unit probe.

A `Command::Memory` payload whose table is valid but whose memory bytes end early leaves the current `receive_memory_ranges()` loop making zero progress. The focused baseline was terminated by the harness deadline with exit status `124` while the single test was still running.

A one-branch candidate that treats `bytes_read == 0` as an incomplete-payload receive error makes the same exact test return normally with an error, and the focused candidate test passes.

The first candidate run's Clippy command was not authoritative because shell piping through `tee` masked a nonzero Clippy exit. The underlying Clippy failure was an unrelated pre-existing `unfulfilled-lint-expectations` error in `vmm/src/lib.rs`, not the changed migration transport path. A corrected workflow is queued with `pipefail` and only that known baseline warning suppressed while all other warnings remain denied.

## Exact execution

Workflow:

```text
Cloud Hypervisor truncated migration payload
```

Run / job:

```text
31550372469 / 93971577711
```

Runner:

```text
Ubuntu 24.04
rustc 1.89.0 (29483883e 2025-08-04)
```

Exact test:

```text
migration::transport::truncated_payload_tests::receive_memory_ranges_rejects_truncated_payload
```

### Baseline

The test was built and discovered by exact full name, then run under a five-second outer deadline.

Observed:

```text
BASELINE_RC=124
running 1 test
```

The test did not return before the harness killed it.

### Candidate

Candidate behavior is deliberately local to the existing partial-read loop:

```text
read_volatile_from(...)
if bytes_read == 0:
    return ordinary migration receive error
offset += bytes_read
```

Observed focused result:

```text
running 1 test
test migration::transport::truncated_payload_tests::receive_memory_ranges_rejects_truncated_payload ... ok
1 passed; 0 failed
```

Rustfmt check passed on the candidate carrier.

## Clippy correction

The run uploaded artifact `9124049135`, but its generated text receipt incorrectly said `candidate_clippy=pass` because the workflow used:

```text
cargo clippy ... | tee ...
```

without `pipefail`.

The actual Clippy process exited nonzero on an unrelated current-source lint expectation in `vmm/src/lib.rs`:

```text
this lint expectation is unfulfilled
#[expect(clippy::collapsible_match)]
```

This is a carrier/quality-gate accounting error, not a product result. Do not use the first artifact's Clippy line as evidence.

Corrected workflow run `31550880817` is queued with:

- `set -o pipefail`;
- all warnings denied;
- only `unfulfilled-lint-expectations` allowed to fence the known unrelated baseline owner.

Update this receipt when that run completes.

## Evidence boundary

Established by exact-current execution:

- the focused truncated-payload baseline hangs until the harness deadline;
- the local zero-progress candidate makes the focused test return an ordinary error;
- candidate rustfmt passes.

Pending at this checkpoint:

- corrected authoritative Clippy result;
- connected-but-idle mid-payload cancellation behavior;
- TLS event/finalization matrix;
- KVM or end-to-end live migration.

No guest, KVM VM, external service, or upstream interaction was used for this proof.
