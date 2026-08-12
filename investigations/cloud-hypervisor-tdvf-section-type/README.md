# Cloud Hypervisor TDVF section-type validity

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590T
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — unvalidated section type can construct an invalid Rust enum value**

## Narrow question

Does exact-current `parse_tdvf_sections()` deserialize an untrusted 32-bit section `Type` directly into a Rust enum before validating its discriminant? If so, can the parser keep wire bytes in an all-integer representation until the numeric type is validated, avoiding invalid Rust enum values while preserving all currently represented section types?

Yes. A product-path Miri run on exact source reaches the parser-produced `TdvfSection` with raw type `7` and reports undefined behavior when the enum field is read. A validity-safe integer-wire candidate rejects type `7` with a typed error, preserves all currently represented values, and passes focused/broad/quality gates.

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

Rust requires an enum value to carry a valid discriminant. The current parser therefore cannot safely materialize arbitrary on-disk `Type` values directly as `TdvfSectionType`.

A current QEMU TDVF implementation provides an independent implementation check: its raw TDVF section entry stores `Type` as `uint32_t`, converts the wire fields explicitly, then switches on the numeric type and rejects unsupported values. That supports the representation boundary used by this candidate without making QEMU behavior normative for Cloud Hypervisor.

## Authoritative execution

- Fieldwork tested head: `f19cadeb69333f941dda611f2ddc81d68560517a`
- workflow run: `31589016269`
- job: `94089405474`
- artifact: `9138397280`
- artifact digest: `sha256:9803b1092febea0289a507e7dcd21e6a64eb0122b3ea372a6233c48a79d10f33`
- exact source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- Rust: `1.89.0`
- Miri: `0.1.0 (3d6c19bb9a 2026-08-11)` on `1.99.0-nightly`
- feature graph: `arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

## Baseline discriminator: validity-aware execution

A deterministic 256-byte TDVF fixture uses the deprecated metadata-pointer form and one structurally valid section whose raw type is `7`. A normal control uses raw type `0` (`Bfv`) and remains green:

```text
TDVF_TYPE_CONTROL section_type=Bfv
```

The unknown-type witness is `#[ignore]` and was executed only under Miri. The test prints its input before calling exact-current `parse_tdvf_sections()` and reading the returned section type:

```text
TDVF_TYPE_MIRI_INPUT raw_type=7
```

Miri then rejects the parser-produced enum field:

```text
error: Undefined Behavior: constructing invalid value of type x86_64::tdx::TdvfSectionType:
at .<enum-tag>, encountered 0x00000007, but expected a valid enum tag
```

The diagnostic points at the read of `sections[0].r#type` in the product-path test. This is not a generic standalone transmute reproducer: the invalid value is created by exact-current `parse_tdvf_sections()` from the synthetic TDVF wire bytes.

Miri exit status was intentionally nonzero and treated as the baseline witness:

```text
TDVF_TYPE_MIRI_RC=1
```

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

All fields are integers, so every fully initialized bit pattern produced by the existing `read_exact()` byte copy is a valid Rust value. Only after the raw records have been read does conversion construct the public `TdvfSection` and validate the numeric type:

- `0..=6` map to the existing named variants;
- `0xffff_ffff` maps to the existing `Reserved` variant;
- any other value returns typed `TdvfError::InvalidSectionType(raw)`.

On the malformed type-7 fixture:

```text
TDVF_TYPE_CANDIDATE invalid_result=InvalidSectionType(7)
```

The preservation matrix stayed green for every currently represented value:

```text
0x0        -> Bfv
0x1        -> Cfv
0x2        -> TdHob
0x3        -> TempMem
0x4        -> PermMem
0x5        -> Payload
0x6        -> PayloadParam
0xffffffff -> Reserved
```

## Candidate-only diff review

The workflow restores `arch/src/x86_64/tdx/mod.rs` to exact source after the Miri probe before applying the candidate. The complete candidate-only diff was inspected from the artifact.

Scope is one Cloud Hypervisor source file, `arch/src/x86_64/tdx/mod.rs`, with:

- typed `InvalidSectionType(u32)`;
- private all-integer `RawTdvfSection`;
- numeric-to-enum validation and raw-to-typed conversion;
- parser read target changed from typed sections to raw sections;
- two focused candidate regressions covering unknown and all currently represented types.

No BFV/CFV file-range validation, VMM HOB policy, guest-memory destination handling, payload I/O, or section cardinality semantics are changed.

Candidate-only diff SHA-256:

```text
04c8af6c9253c9b742744f8500529111a3cc62dcf2ea30ca790ad8c3f771094a
```

Diff stat:

```text
arch/src/x86_64/tdx/mod.rs | 117 ++++++++++++++++++++++++++++++++++++++++++---
1 file changed, 111 insertions(+), 6 deletions(-)
```

## Broad gates

Authoritative run `31589016269` / job `94089405474`:

```text
arch lib:       37 passed, 0 failed, 1 existing ignored
hypervisor lib:  1 passed, 0 failed, 0 ignored
candidate focused unknown-type rejection: passed
candidate represented-type preservation: passed
clippy: success
nightly rustfmt: success
git diff --check: success
```

Clippy denied warnings while allowing only the exact-current unrelated `unreachable-code`, `unused-mut`, and `unused-variables` x86 baseline classes already encountered in adjacent exact-current lanes.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor can deserialize an unknown TDVF section `Type` directly into `TdvfSectionType` and thereby create an invalid Rust enum value. Miri catches the product-path undefined behavior for raw type `7`. The minimum validity-safe candidate keeps the wire type as `u32` until validation, rejects unknown values with `InvalidSectionType`, preserves every currently represented section type, and clears focused, broad, Clippy, rustfmt, and diff-hygiene gates.

This remains a distinct owner inside #590. It does not replace the separately proven BFV/CFV raw firmware-range lane (LF-R590E), missing-`TdHob` panic lane (LF-R590H), PayloadParam guest-write lane (LF-R590P), or future guest-destination/exact-read/cardinality work.
