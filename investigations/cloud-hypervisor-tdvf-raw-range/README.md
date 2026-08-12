# Cloud Hypervisor TDVF raw firmware-range validation

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590E
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; Cloud Hypervisor upstream remains read-only

## Narrow question

Does exact-current `parse_tdvf_sections()` accept a byte-valid BFV/CFV section whose advertised `data_offset + data_size` lies past the TDVF firmware file, even though `Vm::populate_tdx_sections()` later seeks and copies those exact fields from the firmware file?

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

Baseline cells:

- ignored witness: current parser accepts the BFV range past EOF and returns the section;
- paired invariant: the same file must return an error; expected red on baseline;
- valid control: BFV range `[0x40, 0x60)` inside the same file remains accepted.

## Candidate

After section-table decoding, obtain the firmware file length once and validate only `Bfv | Cfv` raw source ranges:

```text
for BFV/CFV section:
    offset = data_offset
    size   = data_size
    require offset + size <= file_len
```

The candidate adds typed `ReadFileMetadata` and `InvalidSectionFileRange` errors plus one compact exact-boundary regression. Since `data_offset` and `data_size` are `u32`, their sum is representable in `u64`; no wrap-prone arithmetic remains in this specific check.

## Execution gates

```text
exact source pin
Rust 1.89.0 + nightly rustfmt
probe application and exact test discovery
valid BFV control on baseline
ignored BFV-past-EOF acceptance witness
paired invariant expected red on baseline
candidate application
paired invariant green
valid BFV control green
candidate typed-error regression green
cargo test --locked -p arch --features tdx
cargo clippy --locked -p arch --features tdx --all-targets --
  -D warnings with only exact-current regs.rs base lint classes suppressed
cargo +nightly fmt --all -- --check
git diff --check
complete candidate-only diff review
```

## Evidence boundary

A green result proves the parser accepts an invalid BFV/CFV firmware source range and that the local typed validation closes that parser/consumer contract. It does not by itself prove the missing-HOB panic, destination guest-range panics, or PayloadParam path; those remain separately executable #590 claims.
