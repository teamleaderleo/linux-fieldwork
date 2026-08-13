# Cloud Hypervisor — embedded TDVF Payload is skipped without external kernel

Updated: 2026-08-13
Owning issue: #590
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
TD-Shim spec/source: `confidential-containers/td-shim@e3a692b1e58c59b40647d919f6de8ae69b2c8846`
Tested Fieldwork head: `823e2343518d0db667e68c9b2417b0299e3de8dd`
External-contact state: false; upstream remains read-only
State: **PROVEN SPEC/CONSUMER GAP — CANDIDATE PENDING SOURCE-RANGE/PRECEDENCE COMPOSITION**

## Result

Exact-current Cloud Hypervisor accepts a TDVF `Payload` section whose `RawDataSize` is nonzero because the payload is embedded in the TD-Shim firmware image, and the corresponding raw bytes are present/readable in the firmware. But the production `Payload` arm has no firmware raw-data copy path: all work is gated on a separate `self.kernel` file.

Therefore firmware-only TDX with a spec-valid embedded Payload skips the payload bytes entirely.

This case is supported by the current TD-Shim specification and validator. It does not depend on the separate #654 TDX direct-kernel validation repair because firmware-only TDX is already a valid exact-current configuration.

## TD-Shim contract

TD-Shim exact source `e3a692b1e58c59b40647d919f6de8ae69b2c8846` establishes:

- the VMM shall follow each TDVF section's `MemoryAddress` and load the corresponding component;
- for `Payload`, `RawDataSize` must be nonzero when the whole image includes the payload, otherwise it must be zero;
- there may be zero or one Payload section;
- `MemoryDataSize >= RawDataSize` when raw data is present;
- `doc/tdshim_spec.md` explicitly describes a “TD-Shim with container OS” use case where the OS kernel is included as `Payload` so TD-Shim does not need to load it from other storage;
- `td-shim-interface/src/metadata.rs::validate_sections()` implements the same Payload rule.

The handoff question is also resolved by the current spec: when the final binary includes the payload and TD-Shim knows the payload type, **the VMM does not need to create a PayloadInfo HOB**. The VMM still has the responsibility to load the payload into TD private memory. PayloadInfo is the VMM handoff for the external/dynamic payload case where the host knows the external payload type.

## Exact-current Cloud Hypervisor owner

`parse_tdvf_sections()` accepts valid `TdvfSectionType::Payload` records and returns their `data_offset`, `data_size`, `address`, and `size`.

`Vm::populate_tdx_sections()` currently handles Payload as:

```rust
TdvfSectionType::Payload => {
    info!("Copying payload to guest memory");
    if let Some(payload_file) = self.kernel.as_mut() {
        // external-kernel path
        ...
    }
}
```

The exact production arm contains:

```text
external_kernel_gate = true
firmware_raw_copy = false
```

It does not seek `firmware_file` to `section.data_offset`, does not consume `section.data_size`, and has no embedded-Payload branch.

## Baseline fixture

Byte-valid one-section TDVF firmware:

```text
type        = Payload (5)
data_offset = 0x1000
data_size   = 0x10
address     = 0x200000
size        = 0x1000
attributes  = 0
```

The 16 raw payload bytes at file offset `0x1000` are all `0x7c`. `MemoryDataSize` is 4 KiB aligned and larger than `RawDataSize`; the source range is fully inside the file.

## Execution history

First run:

- run `31667413341`
- job `94344826916`
- artifact `9168439187`

Source/spec checks passed, but the fixture test failed to compile because the probe formatted `section.r#type` directly from a packed TDVF struct, triggering Rust E0793. This was harness-only; no parser/product conclusion was taken from that run.

The probe was repaired by copying packed fields to locals before formatting/comparison.

Authoritative baseline rerun:

- run `31667565640`
- job `94345291529`
- tested Fieldwork head `823e2343518d0db667e68c9b2417b0299e3de8dd`
- artifact `9168493865`
- artifact digest `sha256:99df68661a347912b5236279c30dcd6ddc63839698a698831bf289299d7d2e04`
- bundle `embedded-payload-baseline-final.zip`

Exact TD-Shim contract and exact Cloud Hypervisor owner gates passed.

Parser/raw-byte fixture:

```text
TDVF_EMBEDDED_PAYLOAD_PARSE offset=0x1000 raw=0x10 address=0x200000 memory=0x1000 type=Payload
TDVF_EMBEDDED_PAYLOAD_BYTES len=16 first=0x7c last=0x7c
```

Production-owner receipt:

```text
TDVF_EMBEDDED_PAYLOAD_OWNER external_kernel_gate=true firmware_raw_copy=false
```

Expected production invariant:

```text
TDVF_EMBEDDED_PAYLOAD_INVARIANT_RC=1
AssertionError: spec-valid embedded Payload has no firmware raw-data copy path
```

This is a source + executable-fixture proof, not a claim that a full TDX guest was booted in the hosted runner.

## Candidate boundary now clarified

A minimal embedded-Payload repair does **not** need to synthesize PayloadInfo for the embedded/known-type case.

However, do not collapse the following owners into one unreviewed patch:

1. **Embedded raw source range.** Earlier BFV/CFV source-range validation was intentionally scoped to those types because Payload was believed to come only from a separate kernel file. Embedded Payload shows that `Payload` with `data_size > 0` also needs firmware raw-source range validation.
2. **Embedded raw copy.** When `data_size > 0` and no external kernel is supplied, the VMM must load the raw bytes from `firmware_file[data_offset..data_offset+data_size]` into the Payload memory address.
3. **Guest-memory/runtime I/O errors.** The copy must propagate destination/read failures rather than add another unwrap or ignored short-copy path.
4. **Ambiguous dual source.** If metadata embeds a Payload (`RawDataSize > 0`) and the user also supplies an external `--kernel`, do not silently choose precedence without a sourced rule. This ambiguity does not block fixing the clearly valid firmware-only embedded case.

## Disposition

**PROVEN SPEC/CONSUMER GAP.** Exact-current Cloud Hypervisor parses a supported embedded TDVF Payload and its raw bytes, but the VMM lacks the required firmware-to-Payload-memory load path when no external kernel file exists.

Candidate work should proceed as controlled composition of the raw-source validation and copy/error owners, not as a speculative PayloadInfo change.
