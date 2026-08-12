# Cloud Hypervisor truncated migration payload — execution receipt

Updated: 2026-08-12
Owning issue: #580
Exact upstream source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Carrier branch: `research/ch-migration-rollback-probes`
External-contact state: false; none occurred

## TL;DR

The truncated-memory-payload failure is reproduced on exact current Cloud Hypervisor source with a focused in-tree unit probe.

A `Command::Memory` payload whose table is valid but whose memory bytes end early leaves current `receive_memory_ranges()` making zero progress. The focused baseline remained running until the five-second harness deadline terminated it with exit status `124`.

A minimal candidate that treats `bytes_read == 0` as an incomplete-payload receive error makes the same test return normally with an ordinary error. The candidate test, rustfmt, and an authoritative Clippy gate are green.

## Exact execution

Authoritative run / job:

```text
31550880817 / 93973144031
```

Exact source / toolchain:

```text
cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052
rustc 1.89.0 (29483883e 2025-08-04)
```

Exact test:

```text
migration::transport::truncated_payload_tests::receive_memory_ranges_rejects_truncated_payload
```

Artifact:

```text
ID: 9124468956
SHA-256: 0a3a742d2039e666c28568a003bcbe406ae8c806ab7954cded75d6956c776f1d
```

## Baseline

The fixture writes a syntactically valid `MemoryRangeTable`, writes only 32 bytes of a declared 256-byte memory payload, then closes the peer socket.

Observed:

```text
BASELINE_RC=124
running 1 test
```

The test did not return before the harness killed it.

The exact dependency/source mechanism is:

```text
vm-memory ReadVolatile may return Ok(0) on EOF
receive_memory_ranges() adds bytes_read to offset
bytes_read == 0 leaves offset unchanged
loop condition remains true forever
```

## Candidate

Candidate behavior is deliberately local to the existing partial-read loop:

```text
bytes_read = read_volatile_from(...)?
if bytes_read == 0:
    return ordinary MigrateReceive incomplete-payload error
offset += bytes_read
```

Observed:

```text
running 1 test
test migration::transport::truncated_payload_tests::receive_memory_ranges_rejects_truncated_payload ... ok
1 passed; 0 failed
```

## Quality gates

`cargo fmt --all -- --check` passed.

The authoritative Clippy command used shell `pipefail` and denied all warnings while suppressing only one known unrelated exact-current lint-owner mismatch in `vmm/src/lib.rs`:

```text
cargo clippy -p vmm --features kvm --lib --tests -- \
  -D warnings -A unfulfilled-lint-expectations
```

Result: passed.

The suppression is limited to `unfulfilled-lint-expectations`; all other warnings remained denied. The earlier artifact `9124049135` is superseded because its `cargo clippy | tee` pipeline masked the unrelated nonzero Clippy exit.

## Interpretation

This closes one bounded subquestion under #580:

> A truncated/closed migration memory payload must not leave the receiver in a zero-progress loop.

The candidate is smaller than a general cancellation redesign and should remain separable from other receive-liveness work.

## Remaining #580 boundaries

Still open and distinct:

- connected-but-idle peer during an in-progress payload: explicit cancellation cannot currently interrupt the blocking read;
- TCP/TLS accept/handshake failures can bypass the normal receive failure event/finalizer;
- direct request-read / response-write I/O errors can bypass receiver state cleanup;
- a live-idle TLS handshake has no bounded handshake deadline after TCP accept;
- explicit `Abandon` is available in the protocol but is not a substitute for transport-failure finalization.

## Evidence boundary

Established:

- exact-current truncated-payload baseline hangs under the focused fixture;
- minimal zero-progress detection returns an ordinary error;
- candidate focused test passes;
- rustfmt passes;
- focused VMM Clippy passes with only the known unrelated unfulfilled-expectation lint category suppressed.

Not established here:

- connected-but-stalled cancellation;
- TLS failure/event behavior;
- full live-migration/KVM behavior;
- upstream acceptance of the candidate.

No guest, KVM VM, external target, or upstream interaction was used.
