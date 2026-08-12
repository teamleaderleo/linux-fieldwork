# Cloud Hypervisor TDVF section-table pre-allocation validation

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590A
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — truncated advertised section table can force large allocation before EOF is checked**

## Narrow question

Can a tiny TDVF firmware file provide a descriptor whose `length` and `num_sections` are internally self-consistent but advertise a section table far larger than the bytes remaining in the file, causing exact-current `parse_tdvf_sections()` to allocate the full advertised `Vec<TdvfSection>` before `read_exact()` discovers EOF?

Yes. Exact-current source first allocates from `num_sections`, then discovers truncation in `read_exact()`. A bounded product-path witness requested a 1 GiB section vector from a 256-byte firmware image and hit Rust's allocation failure under a 512 MiB subprocess address-space cap. The minimum candidate rejects the same descriptor against firmware length before allocation and passes focused, broad, and quality gates.

## Source owner

Exact-current parser validates signature, descriptor-length consistency, and version, then performs:

```rust
let mut sections = Vec::new();
sections.resize_with(descriptor.num_sections as usize, TdvfSection::default);
file.read_exact(/* all advertised section bytes */)?;
```

There is no check that the advertised contiguous section table fits between the current stream position and firmware EOF before `Vec::resize_with()`.

Because `length` and `num_sections` are `u32`, a self-consistent descriptor can advertise roughly 134 million 32-byte entries, approaching 4 GiB of section-vector allocation even when the file itself is tiny.

## Authoritative execution

- Fieldwork tested head: `be334d724140b11d04e587e2392dffeb468bc2cd`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31590569627`
- job: `94094319001`
- artifact: `9139279372`
- artifact digest: `sha256:365fecce00ee7717602fe770a54a2bb9b4149fd1cbf9cfa49abb449ea72d5cbc`
- feature graph: `arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

## Baseline result

The valid one-section control stayed green.

A normal 256-byte fixture advertised 262,144 sections (8 MiB of table data). Exact-current allocated the vector and only then failed while reading the absent table bytes:

```text
TDVF_ALLOC_INVARIANT result=Err(ReadDescriptor(Error { kind: UnexpectedEof, message: "failed to fill whole buffer" }))
TDVF_ALLOC_BASELINE_INVARIANT_RC=101
```

The stronger witness advertised 33,554,432 sections = exactly 1 GiB of `TdvfSection` storage. The already-built product test binary ran in a subprocess capped to 512 MiB virtual memory, preventing a runner-wide OOM:

```text
TDVF_ALLOC_BASELINE_REQUEST num_sections=33554432 section_bytes=1073741824
memory allocation of 1073741824 bytes failed
TDVF_ALLOC_BASELINE_SUBPROCESS_RC=134
```

The witness was accepted only because the exact requested allocation and Rust allocation-failure diagnostic were both present. No timeout, generic SIGKILL, or runner OOM was used as evidence.

## Candidate

Before `Vec` allocation, after the existing descriptor structural checks:

```rust
let section_table_start = file.stream_position()?;
let file_len = file.metadata()?.len();
let section_table_size = u64::from(descriptor.length) - size_of::<TdvfDescriptor>() as u64;
let table_end = section_table_start.checked_add(section_table_size)?;
if table_end > file_len {
    return Err(TdvfError::InvalidDescriptorRange { table_end, file_len });
}
```

Only after that check does the existing allocation/read proceed. This is not an arbitrary metadata-size cap; it requires only that the descriptor's advertised contiguous table physically fit in the firmware file.

The same 1 GiB-advertising 256-byte fixture runs without any memory cap under the candidate and returns immediately:

```text
TDVF_ALLOC_CANDIDATE invalid_result=InvalidDescriptorRange { table_end: 1073741840, file_len: 256 }
```

A one-section in-file control remains valid:

```text
TDVF_ALLOC_CANDIDATE control_sections=1
```

## Candidate-only diff review

The workflow restores `arch/src/x86_64/tdx/mod.rs` to exact source after baseline execution. Complete candidate-only diff scope:

```text
arch/src/x86_64/tdx/mod.rs | 66 ++++++++++++++++++++++++++++++++++++++++++++++
1 file changed, 66 insertions(+)
```

Reviewed contents are exactly:

- typed `InvalidDescriptorRange { table_end, file_len }`;
- pre-allocation section-table start/file-length validation;
- one malformed 1 GiB-advertising regression;
- one valid one-section control.

No section-type decoding, BFV/CFV raw range, GUID-table traversal, VMM destination, Payload, HOB, or section-cardinality semantics are changed.

Candidate-only diff SHA-256:

```text
56d94f7fb8d0aabb365b4c5547ae9235626d07db326a9671335798b90e5e5d37
```

## Broad and quality gates

Authoritative run `31590569627` / job `94094319001`:

```text
arch lib:       37 passed, 0 failed, 1 existing ignored
hypervisor lib:  1 passed, 0 failed
candidate focused malformed/control matrix: success
clippy: success
nightly rustfmt: success
git diff --check: success
```

Clippy denied warnings while allowing only the already identified exact-current unrelated x86 baseline warning classes.

## Composition boundary

LF-R590T independently changes TDVF section wire representation to validate enum discriminants. R590A executes before the section allocation/read and owns only table-vs-file range validation. Both touch the same parser region, so a selected parser-hardening stack still needs an explicit A+T composition gate. LF-R590G is a separate earlier GUID-table discovery owner.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor can attempt a large metadata-driven `Vec<TdvfSection>` allocation from a tiny truncated firmware image before it checks whether the advertised section table exists. The minimum pre-allocation table-vs-file range candidate rejects the malformed descriptor before allocation, preserves a valid table, and clears focused, broad, Clippy, rustfmt, and diff-hygiene gates.
