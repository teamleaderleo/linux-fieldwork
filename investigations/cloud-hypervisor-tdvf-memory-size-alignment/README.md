# Cloud Hypervisor TDVF MemoryDataSize alignment

Updated: 2026-08-13
Owning issue: #590
Fieldwork base: `f9a45e6a311b59aed58dd6ed525a5d38df1e30b6`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Narrow question

Can exact-current Cloud Hypervisor accept a TDVF section whose `MemoryDataSize` is not 4 KiB aligned, then silently truncate that size when the KVM TDX backend converts it to a page count?

## Independent consumer basis

QEMU at `d49f87606ac1a6e15701b26c1b16c5d7e948ffcb`, `hw/i386/tdvf.c`, defines `TDVF_ALIGNMENT = 4096` and rejects a section when `MemoryDataSize` is not aligned to that boundary.

This lane owns only `MemoryDataSize` alignment. `MemoryAddress` alignment is a separate question even though QEMU validates both.

## Exact Cloud Hypervisor path

`arch/src/x86_64/tdx/mod.rs::parse_tdvf_sections()` currently returns section metadata without checking `size` alignment.

Later, exact-current `hypervisor/src/kvm/mod.rs::tdx_init_memory_region()` builds its KVM TDX command with:

```rust
pages: (size / 4096).try_into().unwrap(),
```

That is integer division. If parser-accepted `MemoryDataSize = 0x1800`, the backend represents it as one page (`0x1000` bytes), dropping the final `0x800` bytes from TDX initialization/measurement.

## Baseline discriminator

Use a byte-valid one-section BFV fixture whose other relevant fields are clean:

```text
data_offset = 0x1000
data_size   = 0x1000
address     = 0x100000   # 4 KiB aligned
size        = 0x1800     # deliberately not 4 KiB aligned
```

The raw source range is inside the firmware file and `RawDataSize <= MemoryDataSize`, so the fixture does not rely on the already-proven source-range or raw-vs-memory-size bugs.

Expected baseline:

- parser accepts `size=0x1800`;
- applying the exact backend conversion gives `pages=1`, represented bytes `0x1000`, dropped tail `0x800`;
- normal parser-alignment invariant is expected red.

Control uses `size=0x2000`.

## Minimum candidate

After reading the TDVF section table, reject any section where:

```text
MemoryDataSize % 4096 != 0
```

with a typed `InvalidSectionMemorySizeAlignment { memory_size }` error.

Do not add address alignment, raw-size containment, type rules, or cardinality policy in this candidate.

## Gates

- exact source pin and clean tree;
- source assertion that KVM TDX still uses `pages = size / 4096`;
- baseline acceptance/truncation witness;
- aligned control;
- expected-red baseline invariant;
- restore exact source before candidate;
- typed malformed rejection + aligned control;
- full `arch` + `hypervisor` TDX/KVM library tests;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only diff and SHA-256 receipt.
