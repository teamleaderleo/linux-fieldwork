# SMBIOS Type 11 OEM-count independent candidate review

Updated: 2026-08-12
State: EXECUTED — INDEPENDENT CANDIDATE REVIEW VERIFIED
Variant: LF-R593R
Canonical issue: #593
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Rust: `rustc 1.89.0 (29483883e 2025-08-04)`
Runner: Ubuntu 24.04.4
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Purpose

Close the remaining quality-gate ambiguity around the already-proven SMBIOS Type 11 255/256 count boundary without duplicating its baseline reproduction.

The old controlled-fork candidate run passed all SMBIOS candidate tests but failed `arch` Clippy because the crate was linted with its default feature set. In that configuration, x86_64 `regs.rs` sees `hypervisor::StandardRegisters` as uninhabited and emits unrelated unreachable/unused warnings. The candidate does not touch that file.

This review used a matched baseline/candidate quality gate with the existing `arch/kvm` feature enabled. That is not a lint suppression: it selects the product x86_64 register implementation and keeps `-D warnings` unchanged.

## Candidate scope

The retained Fieldwork patch had a malformed textual hunk representation (`git apply` reported a corrupt patch), so the review did not pretend that packaging error was product drift. The same narrow candidate was materialized against exact current source with anchor-checked `apply_review_candidate.py`. The resulting upstream diff is confined to `arch/src/x86_64/smbios.rs` and matches the recorded count semantics:

- add `Error::TooManyOemStrings`;
- perform checked `u8::try_from(oem_strings.len())` before Type 11 emission;
- keep 255 accepted and encoded as 255;
- reject 256 before emitting a contradictory wrapped count;
- add focused 255/256 regressions.

No embedded-NUL change is part of this review; that was mixed into an older experimental controlled-fork workflow and is outside #593's count invariant.

## Authoritative execution

Workflow run: `31569676042`
Job: `94028776208`
Tested Fieldwork head: `9cbe748869d1174121756b90f1569b1e4b51d8cc`
Artifact: `9130820011`
Artifact digest: `sha256:346aa6248470be14a36209e2213b5d262e411d3ac123fa5066ec8dd05f8a1c60`
Exact source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`

Receipt:

```text
source_gate=success
baseline_clippy_gate=success
candidate_gate=success
discover_gate=success
valid_255_gate=success
reject_256_gate=success
arch_suite_gate=success
candidate_clippy_gate=success
hygiene_gate=success
```

The matched exact-current baseline quality gate passed:

```text
cargo clippy --locked -p arch --features kvm --all-targets -- -D warnings
```

The same command passed after applying the one-file candidate. This demonstrates that the older red Clippy result was not caused by the SMBIOS change; it came from linting the `arch` crate without the KVM feature that inhabits the x86_64 standard-register implementation.

Focused results:

```text
smbios_oem_string_count_255_is_accepted ... ok
smbios_oem_string_count_256_is_rejected ... ok
```

Full KVM-feature arch library suite:

```text
37 passed; 0 failed
```

Final hygiene proved the only changed upstream path was:

```text
arch/src/x86_64/smbios.rs
```

Rustfmt and `git diff --check` passed.

## Materialization iteration

The first independent review run proved the matched baseline KVM Clippy was green, but `git apply` rejected the retained `candidate.patch` as a corrupt patch before any candidate test ran. This was a Fieldwork artifact-format problem, not source drift: exact-current anchors remained unchanged.

The authoritative run replaced only that materialization mechanism with an anchor-checked script. It did not expand candidate semantics or add the old experimental embedded-NUL change.

## Disposition

**INDEPENDENT CANDIDATE REVIEW VERIFIED.**

The Type 11 cardinality fix is a narrow one-file change: preserve 255, reject 256 with a typed error before serialization, and avoid the baseline `count=0` wrap. Exact-current matched baseline/candidate KVM-feature Clippy, focused boundaries, full arch tests, formatting, and diff hygiene all pass.

The old candidate run's `regs.rs` Clippy failure should not be treated as candidate-owned. The retained textual patch itself should be regenerated before any human review because its stored hunk representation is malformed; the semantic product diff executed here is the evidence source of truth.

No Cloud Hypervisor upstream issue, PR, comment, review, email, reaction, or other interaction occurred or is authorized by this carrier.
