# Cloud Hypervisor TDVF parser candidate composition

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590C
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **GREEN COMPOSITION — LF-R590G + LF-R590A + LF-R590T coexist cleanly**

## Purpose

Three independent parser-side #590 owners were already proven in isolation against the same exact Cloud Hypervisor source:

- LF-R590G: GUID-table structural subtraction bounds;
- LF-R590A: descriptor section-table-vs-file validation before metadata-driven allocation;
- LF-R590T: validity-safe raw section type decoding before constructing the Rust enum.

All three live in `arch/src/x86_64/tdx/mod.rs`. This carrier validates their selected composition and is not a fourth product owner.

## Authoritative execution

- tested Fieldwork head: `ce652ef863e82f784e15582e6ccc3cb8d94e969f`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31592359081`
- job: `94099973618`
- artifact: `9139666727`
- artifact digest: `sha256:15f89acb246559d2484174cd7dbf29217ca69fbc2d4bf7fd8d257059c71cac1c`
- combined diff SHA-256: `34311bdbe80b056db34b3c37bfdd9003a005e6912242e1a5556d59cf1dac88f9`
- features: `arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

## Deterministic materialization

The workflow starts from exact Cloud Hypervisor source and retrieves the already-tested candidate materializers from immutable Fieldwork tested commits:

- G script from `04f5eb6fc9733c4bd4a7f1892316139efeece2cb`;
- A script from `be334d724140b11d04e587e2392dffeb468bc2cd`;
- T script from `f19cadeb69333f941dda611f2ddc81d68560517a`.

They apply successfully in order `G -> A -> T`. G modifies earlier GUID discovery; A inserts the table-vs-file check immediately before allocation/read; T then replaces the typed section allocation/read with all-integer `RawTdvfSection` decoding while leaving A's preceding range check intact.

## Focused composition matrix

Every owning candidate regression/control passed in the combined source:

```text
TDVF_GUID_CANDIDATE small_result=InvalidGuidTableSize(0)
TDVF_GUID_CANDIDATE entry_result=InvalidGuidTableEntrySize { entry_size: 23, remaining: 22 }
TDVF_GUID_CANDIDATE control_offset=Start(0) guid_found=false
TDVF_ALLOC_CANDIDATE invalid_result=InvalidDescriptorRange { table_end: 1073741840, file_len: 256 }
TDVF_ALLOC_CANDIDATE control_sections=1
TDVF_TYPE_CANDIDATE invalid_result=InvalidSectionType(7)
TDVF_TYPE_CANDIDATE control raw_type=0x0 type=Bfv
TDVF_TYPE_CANDIDATE control raw_type=0x1 type=Cfv
TDVF_TYPE_CANDIDATE control raw_type=0x2 type=TdHob
TDVF_TYPE_CANDIDATE control raw_type=0x3 type=TempMem
TDVF_TYPE_CANDIDATE control raw_type=0x4 type=PermMem
TDVF_TYPE_CANDIDATE control raw_type=0x5 type=Payload
TDVF_TYPE_CANDIDATE control raw_type=0x6 type=PayloadParam
TDVF_TYPE_CANDIDATE control raw_type=0xffffffff type=Reserved
```

## Complete diff review

```text
arch/src/x86_64/tdx/mod.rs | 262 +++++++++++++++++++++++++++++++++++++++++++--
1 file changed, 255 insertions(+), 7 deletions(-)
```

The complete combined diff was inspected from the artifact. Production changes are exactly the three already-proven owners:

- G: two typed GUID structural errors plus the table/entry subtraction guards;
- A: typed `InvalidDescriptorRange` plus the pre-allocation table-vs-file check;
- T: typed `InvalidSectionType`, private all-integer wire section, and validated conversion before constructing `TdvfSection`.

Remaining additions are the owning focused regressions/controls. No BFV/CFV source range, VMM destination, HOB, Payload, exact-read, or section-cardinality behavior is mixed in.

## Broad and quality gates

```text
arch lib:       41 passed, 0 failed, 1 existing ignored
hypervisor lib:  1 passed, 0 failed
focused G+A+T composition matrix: success
clippy: success
nightly rustfmt: success
git diff --check: success
```

## Disposition

**GREEN COMPOSITION.** LF-R590G, LF-R590A, and LF-R590T coexist cleanly on exact source. Product ownership remains with the three individual lanes; this receipt validates integration only.
