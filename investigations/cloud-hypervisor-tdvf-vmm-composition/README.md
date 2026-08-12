# Cloud Hypervisor TDVF VMM candidate composition

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590V
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **GREEN COMPOSITION — LF-R590D + LF-R590P + LF-R590H coexist cleanly**

## Purpose

Three independent #590 VMM-side owners were already proven in isolation against the same exact Cloud Hypervisor source:

- LF-R590D: BFV/CFV guest-memory copy error propagation through existing `FirmwareLoad`;
- LF-R590P: PayloadParam guest-memory write error propagation through typed `LoadPayloadParam`;
- LF-R590H: missing `TdHob` converted from `Option::unwrap()` panic to typed `TdxHobMissing`.

All three touch `Vm::populate_tdx_sections()` but own different terminal boundaries. This carrier validates their selected composition from exact source; it is not a fourth bug owner.

## Authoritative execution

- tested Fieldwork head: `7f04aa356312f9bb9fa9ba9dcf8cd8ef33cfcee2`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31591279246`
- job: `94096582052`
- artifact: `9139454701`
- artifact digest: `sha256:d515083026d746b5ee508644dec79813769d4db47100fb17c336198f2186da94`
- combined diff SHA-256: `3bcd988d4311df52c94f3f173302e9210f93b456bd86d7dcc9885352b9284bf4`
- features: `tdx,kvm`

## Composition materialization

One deterministic script applies the three already-proven semantics to exact `vmm/src/vm.rs`:

1. R590D preserves existing `FirmwareLoad(GuestMemoryError)` and routes BFV/CFV `read_volatile_from` failure through it;
2. R590P adds `LoadPayloadParam(GuestMemoryError)` and routes PayloadParam `write_slice` failure through it;
3. R590H adds `TdxHobMissing` and converts only the terminal missing-HOB `None` case while preserving the existing `Option<u64>` return contract.

The helpers remain distinct and the combined source retains the same valid-copy/write/offset behavior proven by the individual lanes.

## Focused composition matrix

All six arms pass in one compiled source image:

```text
TDVF_VMM_COMPOSITION firmware_invalid=FirmwareLoad(InvalidGuestAddress(GuestAddress(8192)))
TDVF_VMM_COMPOSITION firmware_control copied=16 bytes=[90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
TDVF_VMM_COMPOSITION payload_param_invalid=LoadPayloadParam(InvalidGuestAddress(GuestAddress(8192)))
TDVF_VMM_COMPOSITION payload_param_control bytes=[99, 111, 110, 115, 111, 108, 101, 61, 116, 116, 121, 83, 48, 0]
TDVF_VMM_COMPOSITION hob_missing=TdxHobMissing
TDVF_VMM_COMPOSITION hob_control=0x4000
```

## Complete diff review

```text
vmm/src/vm.rs | 98 +++++++++++++++++++++++++++++++++++++++++++++++++++++------
1 file changed, 89 insertions(+), 9 deletions(-)
```

The complete combined diff was inspected from the artifact. Production changes are limited to the two already-proven typed errors, three small helpers, and replacement of the three already-proven terminal unwrap boundaries. The remaining additions are the composition regression. No parser, source-range, exact-read, or section-cardinality behavior is included.

## Broad and quality gates

```text
focused composition matrix: success
full VMM tdx,kvm library: 105 passed, 0 failed, 0 ignored
clippy: success
nightly rustfmt: success
git diff --check: success
```

## Disposition

**GREEN COMPOSITION.** LF-R590D, LF-R590P, and LF-R590H coexist cleanly on exact source and preserve each lane's invalid-input error plus valid control. Product ownership remains with the three individual lanes; this receipt validates integration only.
