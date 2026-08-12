# Cloud Hypervisor TDVF section-type validity

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590T
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING

## Narrow question

Does exact-current `parse_tdvf_sections()` deserialize an untrusted 32-bit section `Type` directly into a Rust enum before validating its discriminant? If so, can the parser keep wire bytes in an all-integer representation until the numeric type is validated, avoiding invalid Rust enum values while preserving all currently represented section types?

## Source owner

Exact source defines:

```rust
#[repr(C, packed)]
pub struct TdvfSection {
    ...
    pub r#type: TdvfSectionType,
    ...
}

#[repr(u32)]
pub enum TdvfSectionType {
    Bfv, Cfv, TdHob, TempMem, PermMem, Payload, PayloadParam,
    Reserved = 0xffffffff,
}
```

The parser allocates initialized `TdvfSection::default()` values, casts their storage to a mutable byte slice, and lets `File::read_exact()` overwrite all section bytes directly from the firmware image. There is no numeric type validation before the vector is returned.

Rust's Reference states that an enum must have a valid discriminant and that producing an invalid value is undefined behavior. Therefore an unknown on-disk value such as `7` cannot safely be represented by the current `TdvfSectionType` enum.

A current QEMU TDVF implementation provides an independent implementation check: its raw TDVF section entry stores `Type` as `uint32_t`, converts the wire fields explicitly, then switches on the numeric type and rejects unsupported values. That supports the representation boundary used by this candidate without making QEMU behavior normative for Cloud Hypervisor.

## Baseline discriminator: Miri only

A deterministic 256-byte TDVF fixture uses the deprecated metadata-pointer form and one structurally valid section whose raw type is `7`.

The injected baseline test calls exact-current `parse_tdvf_sections()` and then reads `sections[0].r#type`. It is `#[ignore]` and **must not be run as a normal Rust test**, because normal execution would itself exercise the suspected undefined behavior. The workflow runs this test only under Miri and expects Miri to reject the invalid enum discriminant.

A separate normal control uses raw type `0` (`Bfv`) and must remain green.

If Miri cannot execute the product test because of an unrelated unsupported dependency/platform operation, that is a harness failure and is not product evidence; the lane will be repaired or narrowed before disposition.

## Candidate

The candidate introduces a private wire-only representation:

```rust
#[repr(C, packed)]
struct RawTdvfSection {
    data_offset: u32,
    data_size: u32,
    address: u64,
    size: u64,
    r#type: u32,
    attributes: u32,
}
```

All bit patterns of those integer fields are valid Rust values, so the existing byte-oriented `read_exact()` pattern is safe for this representation. Conversion to public `TdvfSection` then validates the numeric type:

- `0..=6` map to the existing named variants;
- `0xffff_ffff` maps to the existing `Reserved` variant;
- any other value returns typed `TdvfError::InvalidSectionType(raw)`.

This lane does not change the semantics of known section types, add address/range validation, or decide broader metadata cardinality rules.

## Intended gates

- exact source pin and clean tree;
- normal known-type parser control green;
- Miri-only unknown-type baseline witness expected to fail specifically on invalid enum validity;
- restore exact source after the probe;
- candidate unknown type `7` returns typed `InvalidSectionType(7)` in normal execution;
- candidate validates all currently represented numeric types `0..=6` and `0xffffffff`;
- full `arch` + `hypervisor` TDX/KVM library tests;
- Clippy with warnings denied except exact-current unrelated x86 baseline warning classes if needed;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.

## Evidence boundary

A source-level validity concern alone is not enough for a PROVEN disposition. This lane requires either a product-path Miri witness or another validity-aware execution that identifies the invalid enum boundary. A generic standalone transmute example is not accepted as product evidence.
