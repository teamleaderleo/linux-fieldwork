# SMBIOS Type 11 OEM-count independent candidate review

Updated: 2026-08-12
State: EXECUTION PENDING
Variant: LF-R593R
Canonical issue: #593
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remains read-only

## Purpose

Close the remaining quality-gate ambiguity around the already-proven SMBIOS Type 11 255/256 count boundary without duplicating its baseline reproduction.

The old controlled-fork candidate run passed all SMBIOS candidate tests but failed `arch` Clippy because the crate was linted with its default feature set. In that configuration, x86_64 `regs.rs` sees `hypervisor::StandardRegisters` as uninhabited and emits unrelated unreachable/unused warnings. The candidate does not touch that file.

This review therefore uses a matched baseline/candidate quality gate with the existing `arch/kvm` feature enabled. That is not a lint suppression: it selects the product x86_64 register implementation and keeps `-D warnings` unchanged.

## Candidate scope

Apply the retained Fieldwork `candidate.patch` only. It:

- adds `Error::TooManyOemStrings`;
- performs checked `u8::try_from(oem_strings.len())` before Type 11 emission;
- keeps 255 accepted and encoded as 255;
- rejects 256 before emitting a contradictory wrapped count;
- adds focused 255/256 regressions.

No embedded-NUL change is part of this review; that was mixed into an older experimental controlled-fork workflow and is outside #593's count invariant.

## Required gates

1. exact-current baseline `cargo clippy --locked -p arch --features kvm --all-targets -- -D warnings` passes;
2. apply only retained `candidate.patch`;
3. focused 255/256 tests pass;
4. full `cargo test --locked -p arch --features kvm --lib` passes;
5. matched candidate Clippy passes;
6. rustfmt and `git diff --check` pass;
7. final changed upstream source is only `arch/src/x86_64/smbios.rs`.

If baseline KVM-feature Clippy is red for unrelated current debt, this carrier records that rather than weakening the gate.
