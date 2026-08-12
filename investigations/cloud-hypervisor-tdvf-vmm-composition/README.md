# Cloud Hypervisor TDVF VMM candidate composition

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590V
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING COMPOSITION

## Purpose

Three independent #590 VMM-side owners are already proven in isolation against the same exact Cloud Hypervisor source:

- LF-R590D: BFV/CFV guest-memory copy error propagation through existing `FirmwareLoad`;
- LF-R590P: PayloadParam guest-memory write error propagation through typed `LoadPayloadParam`;
- LF-R590H: missing `TdHob` converted from `Option::unwrap()` panic to typed `TdxHobMissing`.

All three touch `Vm::populate_tdx_sections()` but own different terminal boundaries. This carrier tests their selected composition from exact source. It is not a fourth bug owner.

## Composition materialization

One deterministic script applies the three already-proven semantics to exact `vmm/src/vm.rs`:

1. preserve existing `FirmwareLoad(GuestMemoryError)` and route BFV/CFV `read_volatile_from` failure through it;
2. add `LoadPayloadParam(GuestMemoryError)` and route PayloadParam `write_slice` failure through it;
3. add `TdxHobMissing` and convert only the terminal missing-HOB `None` case while preserving the existing `Option<u64>` return contract.

The helpers remain distinct and the combined source retains the same valid-copy/write/offset behavior proven by the individual lanes.

## Focused composition matrix

A single focused regression exercises all six arms in one compiled source image:

- invalid BFV/CFV destination -> `FirmwareLoad(InvalidGuestAddress(...))`;
- valid BFV/CFV copy -> same count and bytes;
- invalid PayloadParam destination -> `LoadPayloadParam(InvalidGuestAddress(...))`;
- valid PayloadParam write -> same bytes;
- missing HOB -> `TdxHobMissing`;
- present HOB -> same `0x4000` offset.

## Broad gates

After focused composition:

- full `vmm` library tests with `tdx,kvm` and hosted `/dev/kvm` permission repaired when present;
- Clippy with `-D warnings`, allowing only the already identified exact-current unrelated x86 warning classes plus existing `unfulfilled-lint-expectations`;
- nightly rustfmt;
- `git diff --check`;
- complete combined candidate diff review + SHA-256 artifact receipt.

## Evidence boundary

A green composition validates coexistence only. The owning baseline/product evidence remains in LF-R590D, LF-R590P, and LF-R590H. This carrier must not broaden any candidate into source-file ranges, section-table/parser validity, payload-file exact-read rules, or TDVF section cardinality.
