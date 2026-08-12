# Cloud Hypervisor TDVF raw firmware-range validation

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590E
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remains read-only
State: **PROVEN — BFV/CFV raw firmware-source range only**

## Narrow question

Does exact-current `parse_tdvf_sections()` accept a byte-valid BFV/CFV section whose advertised `data_offset + data_size` lies past the TDVF firmware file, even though `Vm::populate_tdx_sections()` later seeks and copies those exact fields from the firmware file?

Yes. The deterministic synthetic fixture proves current source accepts the out-of-file BFV raw range, while the minimum parser-side candidate rejects it with a typed error and preserves the valid control.

This carrier intentionally owns only BFV/CFV **firmware-file source ranges**. `Payload` reads a separate kernel/payload file. `TdHob`, `TempMem`, `PermMem`, and `PayloadParam` have different destination/semantic contracts and remain separate #590 follow-ups.

## Fixture

A 256-byte synthetic TDVF file uses the deprecated metadata pointer form and contains one structurally valid descriptor/section record:

```text
signature      = TDVF
version        = 1
num_sections   = 1
descriptor_len = 48 bytes
section.type   = BFV
section.data_offset = 0x180
section.data_size   = 0x20
file_len            = 0x100
```

The descriptor and section-table bytes themselves fit completely inside the file. Only the BFV raw-data source range is invalid.

Paired valid control:

```text
section.data_offset = 0x40
section.data_size   = 0x20
file_len            = 0x100
```

## Baseline result

Authoritative final run:

- Fieldwork tested head: `2aec09d81b07b0aa80371c854ecda744af5d4db7`
- workflow run: `31587489499`
- job: `94084601379`
- artifact: `9137750344`
- artifact digest: `sha256:ad63e3860dab463c1bae552eec4c2424bf2ca307572f4c1af130adde14b1dd7e`
- Rust: `1.89.0`; nightly rustfmt from 2026-08-12 (`1.99.0-nightly`)
- selected feature graph: `arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

Valid control stayed green:

```text
TDVF_RAW_CONTROL file_len=0x100 data_offset=0x40 data_size=0x20
```

Current parser accepted the malformed raw range unchanged:

```text
TDVF_RAW_BASELINE file_len=0x100 data_offset=0x180 data_size=0x20 guid_found=false
```

The paired safety invariant lost on baseline exactly as intended:

```text
TDVF_BASELINE_INVARIANT_RC=101
TDVF_RAW_INVARIANT result=Ok(([TdvfSection { data_offset: 384, data_size: 32, address: 4096, size: 32, type: Bfv, attributes: 0 }], false))
BFV raw range past EOF must be rejected
```

Thus the parser-consumer contract gap is executable, not source-only: a BFV section with raw range `[0x180, 0x1a0)` is accepted from a file whose length is only `0x100`.

## Candidate

After section-table decoding, obtain the firmware file length once and validate only `Bfv | Cfv` raw source ranges:

```text
for BFV/CFV section:
    offset = u64(data_offset)
    size   = u64(data_size)
    require offset + size <= file_len
```

The candidate adds typed `ReadFileMetadata` and `InvalidSectionFileRange` errors plus one compact regression. Because `data_offset` and `data_size` are `u32` values widened to `u64`, their sum cannot overflow `u64` in this specific check.

Candidate result on the same malformed fixture:

```text
TDVF_RAW_INVARIANT result=Err(InvalidSectionFileRange { offset: 384, size: 32, file_len: 256 })
```

The valid BFV control remains accepted, and the dedicated typed-error regression passes.

Complete candidate-only diff review found exactly one Cloud Hypervisor source file changed, containing only:

- `ReadFileMetadata` and `InvalidSectionFileRange` error variants;
- BFV/CFV raw firmware-length validation after section-table decode;
- one focused typed-error regression.

No Payload, HOB, guest-destination, or memory-layout semantics are changed.

Candidate-only diff SHA-256:

```text
9d2fac6d010340b58738ee3185fa40906ccd5691ca0e9ef5f05f80f09faf1547
```

## Broad gates

Authoritative run `31587489499` / job `94084601379`:

```text
arch lib:       38 passed, 0 failed, 2 intentionally ignored
hypervisor lib:  1 passed, 0 failed, 0 ignored
clippy:          success
nightly rustfmt: success
git diff --check: success
```

Clippy denied warnings while suppressing only the exact-current unrelated `unreachable-code`, `unused-mut`, and `unused-variables` baseline classes already seen in adjacent exact-current x86 work.

## Harness history

Two earlier failures are retained as harness evidence, not product evidence:

1. The first workflow selected `arch --features tdx` alone. In current Cargo feature ownership, `arch/tdx` is empty and does not enable Hypervisor TDX/KVM support, so compilation failed at the existing `tdx_capabilities` call. The repaired run selects both `arch` and `hypervisor` with package-qualified TDX/KVM features.
2. Early synthetic fixtures referenced fields of packed `TdvfSection` directly inside formatting/assertion macros and then used absolute `std::...` paths rejected by workspace Clippy policy. The fixtures were repaired by copying packed fields to locals and importing the standard-library functions. Candidate product semantics did not change.

Run `31587302628` already proved the baseline/candidate/broad behavior before its fixture-only Clippy failure. Final run `31587489499` repeats the same product result with all quality gates green.

## Evidence boundary / disposition

**PROVEN for BFV/CFV raw TDVF firmware-source ranges.** Exact-current Cloud Hypervisor accepts a structurally valid BFV record whose raw source range lies beyond firmware EOF. The minimum parser-side candidate rejects that record with a typed error, preserves an in-file BFV control, and passes the selected TDX/KVM arch+hypervisor test and quality matrix.

This does **not** close the whole #590 umbrella. Still unsaturated and separately owned:

- missing required `TdHob` leading to `hob_offset.unwrap()`;
- guest destination range validity for section address/size;
- `PayloadParam` guest write error propagation;
- runtime exact-read/error propagation even after metadata validation;
- semantics/cardinality for other section types and pointer discovery variants.

Do not apply the BFV/CFV firmware-file source-range rule to `Payload`: that path reads a separate kernel/payload file.
