# Cloud Hypervisor TDVF MemoryDataSize alignment

Updated: 2026-08-13
Owning issue: #590
Fieldwork base: `f9a45e6a311b59aed58dd6ed525a5d38df1e30b6`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Tested Fieldwork head: `876745ad27acb34bd26d87f70c182203e6de00a1`
External-contact state: false; upstream remains read-only
State: **PROVEN**

## Result

Exact-current Cloud Hypervisor accepts TDVF `MemoryDataSize` values that are not 4 KiB aligned. Its KVM TDX backend later converts the byte size to a page count with integer division:

```rust
pages: (size / 4096).try_into().unwrap(),
```

Therefore a parser-accepted `MemoryDataSize=0x1800` becomes one page (`0x1000` bytes), silently omitting the final `0x800` bytes from the initial TDX memory operation and any measurement requested for that operation.

The minimum parser candidate rejects non-4K-aligned `MemoryDataSize` with a typed error. Focused, broad, Clippy, formatting, and diff-hygiene gates passed.

## Independent consumer basis

QEMU at `d49f87606ac1a6e15701b26c1b16c5d7e948ffcb`, `hw/i386/tdvf.c`, defines `TDVF_ALIGNMENT = 4096` and rejects a TDVF section whose `MemoryDataSize` is not page aligned before its TDX setup proceeds.

QEMU's later TDX path (`target/i386/kvm/tdx.c`) likewise derives `nr_pages` from `entry->size >> 12`; its parser alignment check is what makes that page conversion lossless.

This lane owns only `MemoryDataSize` alignment. `MemoryAddress` alignment remains a separate question even though QEMU validates both.

## Exact Cloud Hypervisor owner

`arch/src/x86_64/tdx/mod.rs::parse_tdvf_sections()` reads section metadata and returns it without checking `size` alignment.

`hypervisor/src/kvm/mod.rs::tdx_init_memory_region()` then constructs:

```rust
pages: (size / 4096).try_into().unwrap(),
```

No rounding or remainder check occurs before the page count is submitted.

## Authoritative execution

Hosted run:

- run `31663822509`
- job `94334072753`
- tested head `876745ad27acb34bd26d87f70c182203e6de00a1`
- artifact `9167184685`
- artifact digest `sha256:12e0682c51aba83ba77026423ccd71c9d90e4288c46154d83b4a50abd3987d80`
- candidate-only diff SHA-256 `4edc38e08c25956ecb06a162e73de465317fb87588857248feb68ad077ef06e8`

Feature matrix:

`arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

### Baseline

Byte-valid BFV fixture:

```text
data_offset = 0x1000
data_size   = 0x1000
address     = 0x100000
size        = 0x1800
```

The raw source is in-file, `RawDataSize <= MemoryDataSize`, and `MemoryAddress` is 4 KiB aligned. This isolates memory-size alignment from the already-proven raw-source-range and raw-vs-memory-size owners.

Exact-current parser accepted the section. Applying the exact backend page conversion gives:

```text
TDVF_MEMORY_ALIGN_BASELINE memory_size=0x1800 backend_pages=1 backend_bytes=0x1000 dropped=0x800
```

The normal alignment invariant lost on baseline:

```text
TDVF_MEMORY_ALIGN_BASELINE_INVARIANT_RC=101
```

Aligned control `MemoryDataSize=0x2000` remained valid.

## Candidate

After reading the section table:

```rust
for section in &sections {
    let memory_size = section.size;
    if memory_size % 4096 != 0 {
        return Err(TdvfError::InvalidSectionMemorySizeAlignment { memory_size });
    }
}
```

Malformed result:

```text
Err(InvalidSectionMemorySizeAlignment { memory_size: 6144 })
```

Aligned control remains accepted:

```text
TDVF_MEMORY_ALIGN_CANDIDATE control memory_size=0x2000
```

## Broad gates

```text
arch:       37 passed, 0 failed, 1 intentionally ignored
hypervisor: 1 passed,  0 failed
Clippy:     success
rustfmt:    success
git diff --check: success
```

Complete candidate-only diff was reviewed. Product change is one typed error plus one post-read alignment loop; remaining diff is focused regression coverage.

## Disposition

**PROVEN.** Exact-current parser accepts fractional-page `MemoryDataSize`, while the exact KVM TDX backend floors byte size to whole pages. The minimum 4 KiB alignment guard is validated.

Keep separate:

- `RawDataSize <= MemoryDataSize` containment (proven separately);
- `MemoryAddress` alignment;
- raw source range versus EOF;
- section type/raw-data rules;
- overlap/cardinality;
- VMM guest-memory error propagation.
