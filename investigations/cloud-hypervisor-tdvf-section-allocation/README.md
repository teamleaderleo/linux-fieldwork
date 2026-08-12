# Cloud Hypervisor TDVF section-table pre-allocation validation

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590A
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING

## Narrow question

Can a tiny TDVF firmware file provide a descriptor whose `length` and `num_sections` are internally self-consistent but advertise a section table far larger than the bytes remaining in the file, causing exact-current `parse_tdvf_sections()` to allocate the full advertised `Vec<TdvfSection>` before `read_exact()` discovers EOF?

## Source owner

Exact-current parser validates:

```text
signature == TDVF
length == sizeof(descriptor) + num_sections * sizeof(section)
version == 1
```

but then immediately does:

```rust
let mut sections = Vec::new();
sections.resize_with(descriptor.num_sections as usize, TdvfSection::default);
file.read_exact(/* all advertised section bytes */)?;
```

There is no check that the advertised table fits between the current file position and firmware EOF before the allocation.

`length` and `num_sections` are `u32`. A self-consistent descriptor can therefore advertise up to roughly 134 million 32-byte entries, approaching 4 GiB of section-vector allocation, even when the actual file is tiny.

## Safe baseline discriminator

This lane deliberately avoids an uncontrolled runner OOM.

1. A normal 256-byte valid control advertises one 32-byte section and must parse successfully.
2. A normal expected-red invariant advertises 262,144 sections (8 MiB) in the same 256-byte file. Exact-current is expected to allocate the table and only then return `ReadDescriptor(UnexpectedEof)`; the invariant requires rejection before the advertised table read.
3. A separate ignored product-path witness advertises 33,554,432 sections = exactly 1 GiB of table data. The workflow runs the already-built arch test binary in a subprocess with a **512 MiB virtual-memory cap**. Baseline is expected to terminate at Rust's allocation failure for the 1 GiB `Vec<TdvfSection>` request. The cap bounds the witness and prevents system-wide memory exhaustion.

The giant witness is accepted only if its log contains both the exact advertised request marker and Rust's allocation-failure diagnostic. A generic timeout, SIGKILL, or runner OOM is not accepted as product evidence.

## Candidate

Before `Vec` allocation, after the descriptor's existing structural checks:

1. get the current stream position (start of section table);
2. get firmware file length;
3. derive advertised section-table bytes from the already-validated descriptor length;
4. checked-add table start + table bytes;
5. return typed `InvalidDescriptorRange { table_end, file_len }` if the table exceeds EOF;
6. only then allocate and read sections.

Candidate regression uses the same 1 GiB-advertising 256-byte fixture **without any memory cap**. It must return the typed range error immediately, demonstrating that the large allocation is no longer attempted.

The candidate does not cap valid TDVF metadata by an arbitrary policy size; it only requires the advertised contiguous section table to physically fit in the firmware file.

## Intended gates

- exact source pin and clean tree;
- valid one-section baseline control green;
- 8 MiB truncated-table pre-read invariant expected-red on baseline;
- 1 GiB advertised allocation witness under a 512 MiB subprocess address-space cap;
- restore exact source before candidate;
- candidate typed rejection of the same 1 GiB-advertising tiny fixture without memory cap;
- full arch + hypervisor TDX/KVM library tests;
- Clippy with warnings denied except already identified exact-current unrelated x86 baseline classes;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.

## Composition boundary

LF-R590T independently changes the TDVF section wire representation to validate enum discriminants. R590A is intentionally placed **before** the section allocation/read block and owns only table-vs-file range validation. If both are selected, they must be composition-tested because they touch the same parser region even though the semantic owners are distinct.
