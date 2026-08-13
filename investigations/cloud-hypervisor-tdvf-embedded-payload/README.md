# Cloud Hypervisor — embedded TDVF Payload is skipped without external kernel

Updated: 2026-08-13
Owning issue: #590
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
TD-Shim spec/source: `confidential-containers/td-shim@e3a692b1e58c59b40647d919f6de8ae69b2c8846`
External-contact state: false; upstream remains read-only
State: STAGED — BASELINE ONLY

## Narrow question

Can exact-current Cloud Hypervisor parse a spec-valid TDVF `Payload` section whose `RawDataSize` is nonzero because the payload is embedded in the TD-Shim firmware image, yet skip loading those raw bytes solely because no separate `--kernel` file was supplied?

## TD-Shim contract

Current TD-Shim specification and implementation make this a real supported metadata form, not a field-name inference:

- the VMM shall follow each TDVF section's `MemoryAddress` and load the corresponding component;
- for `Payload`, `RawDataSize` must be nonzero when the whole TD-Shim image includes the payload, otherwise it must be zero;
- there may be zero or one Payload section;
- `MemoryDataSize >= RawDataSize` when raw data is present;
- `doc/tdshim_spec.md` explicitly describes a “TD-Shim with container OS” use case where the OS kernel is included as `Payload` so TD-Shim does not need to load it from other storage;
- `td-shim-interface/src/metadata.rs::validate_sections()` implements the same Payload rule.

## Exact-current Cloud Hypervisor boundary

`parse_tdvf_sections()` accepts valid `TdvfSectionType::Payload` records and returns their `data_offset`, `data_size`, `address`, and `size`.

But `Vm::populate_tdx_sections()` handles `Payload` as:

```rust
TdvfSectionType::Payload => {
    info!("Copying payload to guest memory");
    if let Some(payload_file) = self.kernel.as_mut() {
        // external-kernel path
        ...
    }
}
```

The production arm contains no path that seeks `firmware_file` to `section.data_offset` and copies `section.data_size` when `self.kernel` is `None`.

Firmware-only TDX configuration is already valid on exact-current source, so this embedded-Payload case does not depend on the separate #654 direct-kernel validation repair.

## Baseline fixture

Construct a byte-valid one-section TDVF firmware:

```text
type        = Payload (5)
data_offset = 0x1000
data_size   = 0x10
address     = 0x200000
size        = 0x1000
attributes  = 0
```

The 16 raw payload bytes at file offset `0x1000` are all `0x7c`. `MemoryDataSize` is 4 KiB aligned and larger than `RawDataSize`, and the source bytes are fully inside the file.

Baseline must prove:

1. exact-current parser accepts and returns the Payload record;
2. the raw bytes are present and readable from the returned `data_offset/data_size`;
3. exact production `Payload` arm still gates all work on `self.kernel.as_mut()` and contains no `firmware_file` raw-copy path;
4. a normal invariant requiring an embedded-payload copy path is expected red.

This is deliberately a source + executable-fixture proof. It does not claim a full TDX boot was executed.

## Candidate stop condition

Do **not** implement the first obvious copy-only patch yet.

TD-Shim's dynamic Linux path boots from the Payload memory slice when a `PayloadInfo` GUID HOB is present; without one it falls back to its built-in firmware-volume payload. Therefore a complete embedded-Payload repair may need both raw-byte loading and a correct PayloadInfo handoff, depending on the embedded payload image contract.

Also resolve source precedence before candidate work:

- embedded payload (`RawDataSize > 0`) with no external kernel is clearly valid and must be supported;
- metadata with `RawDataSize == 0` plus external `--kernel` is the existing dynamic-kernel form;
- if both an embedded payload and an external kernel are supplied, do not silently choose one until the intended override/conflict rule is sourced.

## Initial disposition target

If baseline confirms the four points above: **PROVEN SPEC/CONSUMER GAP; CANDIDATE PENDING HANDOFF SEMANTICS.**
