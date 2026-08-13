# Cloud Hypervisor TDVF raw-data versus memory-size validation

Updated: 2026-08-13
Owning issue: #590
Fieldwork base: `f9a45e6a311b59aed58dd6ed525a5d38df1e30b6`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Tested Fieldwork head: `11ce94f1b63d6cda02b29307d11d198727b279cf`
External-contact state: false; upstream remains read-only
State: **PROVEN**

## Result

Exact-current Cloud Hypervisor accepts a TDVF section whose `RawDataSize` (`data_size`) is larger than its declared `MemoryDataSize` (`size`). A production-shaped BFV copy then uses the larger `data_size`, so firmware bytes can be written beyond the section's own declared memory extent.

The minimum parser candidate rejects `MemoryDataSize < RawDataSize` with a typed error while preserving the valid `RawDataSize < MemoryDataSize` case. Focused, broad, Clippy, formatting, and diff-hygiene gates all passed.

## Independent format/consumer basis

This invariant is not inferred from field names alone.

EDK2 at `2970e5699ba6267f3384ffab20f96647578aebc8` documents TDVF `RawDataSize` as the bytes in the binary image and `MemoryAddress/MemoryDataSize` as the guest physical address/size where BFV is loaded (`OvmfPkg/ResetVector/X64/IntelTdxMetadata.nasm.inc`). Its current producer defines BFV and CFV `MEMORY_SIZE` from the corresponding `RawDataSize` PCD (`OvmfPkg/ResetVector/ResetVector.nasmb`), so emitted BFV/CFV use equality.

QEMU at `d49f87606ac1a6e15701b26c1b16c5d7e948ffcb` performs the general TDVF sanity check in `hw/i386/tdvf.c`:

```c
if (entry->size < entry->data_len) {
    error_report("Broken metadata RawDataSize ... MemoryDataSize ...");
    return -1;
}
```

QEMU also has additional alignment/type checks. Those remain separate owners; this lane changes only raw-data containment.

## Exact Cloud Hypervisor owner

`arch/src/x86_64/tdx/mod.rs::parse_tdvf_sections()` validates descriptor signature/length/version and reads all advertised section records, then returns them without comparing `data_size` and `size`.

Downstream BFV/CFV population copies `section.data_size` bytes to `section.address`. Later TDX initialization uses `section.size` as the memory-region extent. The accepted metadata can therefore make the copy extent larger than the declared TDVF section extent.

## Authoritative execution

Hosted run:

- run `31663540495`
- job `94333229193`
- tested head `11ce94f1b63d6cda02b29307d11d198727b279cf`
- artifact `9167088088`
- artifact digest `sha256:5df1668a8ce5b025b01691363d1e9f389bce2338c6842e2ad1efb443c6570dd4`
- candidate-only diff SHA-256 `ad8689046a2171cdaaf1bc039a3b998f25befafe5081f28ffce71a10b383ecac`

Feature matrix:

`arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

### Baseline

Malformed byte-valid BFV metadata:

```text
data_offset = 0x1000
data_size   = 0x2000
address     = 0x100000
size        = 0x1000
```

The raw source range itself is fully inside the 16 KiB fixture file, so this is not the previously proven EOF bug.

Exact-current parser accepted it:

```text
TDVF_DATA_MEMORY_BASELINE data_size=0x2000 memory_size=0x1000
```

A production-shaped guest-memory copy using the returned metadata copied the full raw length and modified the first byte outside the declared memory extent:

```text
TDVF_DATA_MEMORY_BASELINE copied=0x2000 byte_at_declared_end=0x5a
```

The normal containment invariant lost on baseline:

```text
TDVF_DATA_MEMORY_BASELINE_INVARIANT_RC=101
```

Valid negative control `data_size=0x2000`, `memory_size=0x3000` parsed successfully.

## Candidate

After reading the section table, reject any entry where:

```rust
let data_size = section.data_size;
let memory_size = section.size;
if memory_size < u64::from(data_size) {
    return Err(TdvfError::InvalidSectionMemorySize {
        data_size,
        memory_size,
    });
}
```

The check is deliberately type-independent, matching QEMU's general containment sanity check and avoiding another dependency on section-type decoding.

Malformed result:

```text
Err(InvalidSectionMemorySize { data_size: 8192, memory_size: 4096 })
```

Valid larger-memory control remains accepted:

```text
TDVF_DATA_MEMORY_CANDIDATE control data_size=0x2000 memory_size=0x3000
```

## Broad gates

```text
arch:       37 passed, 0 failed, 1 intentionally ignored
hypervisor: 1 passed,  0 failed
Clippy:     success
rustfmt:    success
git diff --check: success
```

Complete candidate-only diff was reviewed. Product change is one typed error plus one post-read containment loop; the rest of the diff is focused regression coverage.

## Disposition

**PROVEN.** `RawDataSize > MemoryDataSize` is accepted on exact-current Cloud Hypervisor and can make the BFV-style copy write outside the section's declared memory extent. The minimum containment guard is validated.

Keep separate:

- BFV/CFV source range versus firmware EOF (already proven separately);
- raw section type decoding (already proven separately);
- `MemoryAddress` / `MemoryDataSize` page alignment;
- BFV/CFV zero `RawDataSize`;
- memory-only section `RawDataSize` rules;
- section overlap/cardinality;
- VMM guest-memory error propagation.
