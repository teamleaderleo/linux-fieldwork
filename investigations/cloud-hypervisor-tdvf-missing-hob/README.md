# Cloud Hypervisor TDVF missing-TdHob panic

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590H
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING

## Narrow question

When TDVF metadata contains no `TdHob` section, does exact-current Cloud Hypervisor reach the consumer boundary with `hob_offset == None` and panic at `TdHob::start(hob_offset.unwrap())`? Can the minimum VMM-side repair preserve all present-HOB behavior while returning a typed error for the missing case?

## Source owner

`Vm::populate_tdx_sections()` initializes `hob_offset = None`, overwrites it when a `TdvfSectionType::TdHob` record is encountered, and after processing all sections unconditionally executes:

```rust
let mut hob = TdHob::start(hob_offset.unwrap());
```

This carrier deliberately does not change TDVF section cardinality or duplicate-section policy. The current loop's semantics are retained: if one or more TdHob records exist, the final observed address remains the HOB start. Only the `None` terminal case is changed.

EDK2's TDVF metadata source documents `TD_HOB` as the section designating the region where the host VMM writes physical-memory information for guest firmware. That supports treating Cloud Hypervisor's missing-HOB state as a malformed/unusable input for this consumer, without making a broader claim that every external TDVF dialect must have identical section cardinality.

## Baseline discriminator

The baseline probe is inserted only into the x86/KVM VMM unit-test module. It mirrors the current production scan exactly and then performs the same `unwrap()` boundary. It provides:

- ignored witness: missing TdHob must reproduce the current panic under `catch_unwind`;
- normal expected-red invariant: missing TdHob must not panic;
- present-HOB control: one TdHob at `0x4000` must preserve that offset.

After those baseline gates, the workflow restores `vmm/src/vm.rs` from exact source before applying the candidate. Candidate-only diff evidence is therefore self-contained and does not include the probe.

## Candidate

Minimum VMM-side candidate:

1. add typed `Error::TdxHobMissing`;
2. add a tiny associated helper converting `Option<u64>` to `Result<u64>`;
3. replace only `hob_offset.unwrap()` with the typed helper + `?`;
4. add a focused regression proving `None -> TdxHobMissing` and `Some(0x4000) -> 0x4000`.

This retains the existing section-processing order and duplicate-TdHob behavior and does not touch BFV/CFV file-range validation, guest destination ranges, Payload/ PayloadParam handling, HOB size/layout, or TDX memory initialization.

## Intended gates

- exact source pin and clean tree;
- baseline present-HOB control green;
- baseline missing-HOB panic witness green;
- baseline no-panic invariant expected red;
- exact source restoration before candidate;
- candidate typed missing/control regression green;
- source check that the production `hob_offset.unwrap()` boundary is gone;
- full `vmm` library tests with `tdx,kvm` and hosted `/dev/kvm` permission repaired if present;
- Clippy with candidate warnings denied, suppressing only known exact-current unrelated x86 warning classes if required;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.

## Stop/split conditions

Split rather than broaden if evidence points to:

- HOB region size/range validation;
- duplicate TdHob semantics;
- missing/duplicate Payload or PayloadParam policy;
- BFV/CFV raw source ranges (already independently proven by LF-R590E);
- guest-memory destination bounds;
- exact read/write error propagation.
