# Cloud Hypervisor TDVF raw-data versus memory-size validation

Updated: 2026-08-13
Owning issue: #590
Fieldwork base: `f9a45e6a311b59aed58dd6ed525a5d38df1e30b6`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Narrow question

Can exact-current Cloud Hypervisor accept a TDVF section whose `RawDataSize` (`data_size`) is larger than its declared `MemoryDataSize` (`size`), then allow the normal BFV/CFV copy semantics to write firmware bytes beyond the section's declared memory extent?

## Format/consumer basis

This is not inferred from field names alone.

EDK2 at `2970e5699ba6267f3384ffab20f96647578aebc8` documents TDVF `RawDataSize` as the bytes in the binary image and `MemoryAddress/MemoryDataSize` as the guest physical address/size where BFV is loaded (`OvmfPkg/ResetVector/X64/IntelTdxMetadata.nasm.inc`). Its current producer defines both BFV and CFV `MEMORY_SIZE` from the matching `RawDataSize` PCD (`OvmfPkg/ResetVector/ResetVector.nasmb`), so emitted BFV/CFV use equality.

QEMU at `d49f87606ac1a6e15701b26c1b16c5d7e948ffcb` performs a general TDVF sanity check in `hw/i386/tdvf.c`:

```c
if (entry->size < entry->data_len) {
    error_report("Broken metadata RawDataSize ... MemoryDataSize ...");
    return -1;
}
```

QEMU then applies additional alignment/type rules. This lane intentionally owns only the containment invariant `RawDataSize <= MemoryDataSize`; those other rules remain separate research questions.

## Exact Cloud Hypervisor gap

`arch/src/x86_64/tdx/mod.rs::parse_tdvf_sections()` validates descriptor signature/length/version and reads all advertised section records, then returns them directly. It does not compare `data_size` with `size`.

Downstream BFV/CFV population copies `section.data_size` bytes to `section.address`, while later TDX initialization uses `section.size` as the region size. Therefore accepting `data_size > size` makes the copy extent larger than the declared TDVF memory extent.

## Baseline discriminator

Construct a byte-valid one-section TDVF file with an in-file BFV source range and page-aligned memory values:

- malformed: `data_offset=0x1000`, `data_size=0x2000`, `address=0x100000`, `size=0x1000`;
- valid control: same except `size=0x3000`.

The malformed baseline should parse successfully. A production-shaped guest-memory copy using the returned `data_size` should copy `0x2000` bytes and visibly modify the byte at `address + size`, proving bytes are written beyond the section's declared `0x1000` memory extent.

A normal invariant test requires parser rejection; it should fail on exact-current source.

## Minimum candidate

After the section table is read, reject any section where:

```text
MemoryDataSize < RawDataSize
```

with a typed `InvalidSectionMemorySize { data_size, memory_size }` error.

The check does not inspect section type, so it does not introduce another dependency on the separately proven wire-enum repair. It also preserves `data_size < size`, which QEMU accepts and which can represent zero-filled/reserved tail memory.

## Gates

- exact source pin and clean tree;
- baseline valid control green;
- malformed acceptance/copy witness green;
- containment invariant expected red on baseline;
- restore exact source before candidate;
- typed malformed rejection + `data_size < size` control;
- full `arch` + `hypervisor` library tests with exact TDX/KVM feature matrix;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only diff and SHA-256 receipt.

## Split boundaries

Do not mix into this candidate:

- BFV/CFV source range versus firmware EOF (already proven separately);
- raw section type decoding (already proven separately);
- MemoryAddress/MemoryDataSize page alignment;
- BFV/CFV zero RawDataSize;
- memory-only section RawDataSize rules;
- section overlap/cardinality;
- VMM guest-memory error propagation.
