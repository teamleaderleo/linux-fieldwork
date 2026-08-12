# Cloud Hypervisor TDVF GUID-table structural bounds

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590G
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — malformed GUID-table lengths can underflow parser cursors and panic; structural bounds candidate validated**

## Narrow question

When the TDVF/OVMF GUID-table footer is recognized, can malformed length fields make exact-current `tdvf_descriptor_offset()` underflow its table cursor and panic before any TDVF descriptor is parsed? Can minimal structural bounds checks turn those panics into typed parser errors while preserving the minimum footer-only table and normal deprecated-pointer fallback?

Yes. Exact-current source has two independently reproducible subtraction panics: a recognized table smaller than its 18-byte footer, and a nonzero entry length larger than the bytes remaining before the cursor. The minimum structural-bounds candidate turns both into typed errors and preserves the 18-byte footer-only fallback control.

## Format basis

EDK2 documents each GUID-table entry as arbitrary data + a 2-byte length + a 16-byte GUID, and the table footer as a 2-byte total length + 16-byte footer GUID. Therefore a recognized table must be at least 18 bytes; a nonzero entry must be at least 18 bytes and cannot exceed the remaining table bytes.

## Authoritative execution

- Fieldwork tested head: `04f5eb6fc9733c4bd4a7f1892316139efeece2cb`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31590967422`
- job: `94095564467`
- artifact: `9139432616`
- artifact digest: `sha256:dcb7f28e360b9bc856c0b2b39a0f053efc0692b5667425f6f3ecdafe98618fde`
- feature graph: `arch/tdx,arch/kvm,hypervisor/tdx,hypervisor/kvm`

## Baseline result

Minimum footer-only table (`table_size=18`) stayed green and fell back to the deprecated pointer:

```text
TDVF_GUID_CONTROL offset=Start(0) guid_found=false
```

Recognized `table_size=0` reaches exact-current `table_size - 18`:

```text
attempt to subtract with overflow
TDVF_GUID_SMALL_BASELINE panicked=true
TDVF_GUID_SMALL_INVARIANT_RC=101
```

A 40-byte table has 22 bytes before its footer. An entry advertising length 23 reaches exact-current `offset -= entry_size` with `offset=22`:

```text
attempt to subtract with overflow
TDVF_GUID_ENTRY_BASELINE panicked=true
TDVF_GUID_ENTRY_INVARIANT_RC=101
```

## Candidate

Typed structural errors:

```text
InvalidGuidTableSize(table_size)
InvalidGuidTableEntrySize { entry_size, remaining }
```

Checks:

- reject recognized table size `< 18` before cursor arithmetic;
- preserve current zero-entry break behavior;
- for nonzero entries reject `< 18` or `> remaining` before subtraction;
- otherwise preserve existing backward traversal and metadata-GUID handling.

Focused results:

```text
TDVF_GUID_CANDIDATE small_result=InvalidGuidTableSize(0)
TDVF_GUID_CANDIDATE entry_result=InvalidGuidTableEntrySize { entry_size: 23, remaining: 22 }
TDVF_GUID_CANDIDATE control_offset=Start(0) guid_found=false
```

## Candidate-only diff review

```text
arch/src/x86_64/tdx/mod.rs | 79 +++++++++++++++++++++++++++++++++++++++++++++-
1 file changed, 78 insertions(+), 1 deletion(-)
```

Reviewed scope is exactly:

- two typed GUID structural errors;
- the minimum table-size guard;
- the nonzero entry-size bounds guard;
- focused malformed regressions and the minimum-footer control.

No descriptor/section-table allocation, section-type decoding, BFV/CFV range, VMM destination, Payload, HOB, or cardinality semantics changed.

Candidate-only diff SHA-256:

```text
aa47e0e165834a37e41b0377a8b7c80fd9ec7f870686bfd3ab46ae745764b046
```

## Broad and quality gates

Authoritative run `31590967422` / job `94095564467`:

```text
arch lib:       37 passed, 0 failed, 1 existing ignored
hypervisor lib:  1 passed, 0 failed
candidate focused malformed/control matrix: success
clippy: success
nightly rustfmt: success
git diff --check: success
```

## Composition boundary

R590G touches GUID-table discovery before the TDVF descriptor. R590A owns later table-vs-file pre-allocation validation, and R590T owns wire section-type validity. Their semantic owners remain distinct, but the selected parser-hardening stack needs an explicit G+A+T composition run because all touch `arch/src/x86_64/tdx/mod.rs`.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor can panic on malformed recognized GUID-table lengths before TDVF descriptor parsing. The minimum format-backed structural bounds checks convert both subtraction panics into typed errors, preserve the minimum footer-only fallback control, and clear focused, broad, Clippy, rustfmt, and diff-hygiene gates.
