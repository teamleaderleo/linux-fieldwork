# Cloud Hypervisor TDVF GUID-table structural bounds

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590G
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING

## Narrow question

When the TDVF/OVMF GUID-table footer is recognized, can malformed length fields make exact-current `tdvf_descriptor_offset()` underflow its table cursor and panic before any TDVF descriptor is parsed? Can minimal structural bounds checks turn those panics into typed parser errors while preserving the minimum footer-only table and normal deprecated-pointer fallback?

## Source owners

Exact-current code reads the 16-bit table length and then immediately computes:

```rust
let mut offset = table_size - 18;
```

without requiring `table_size >= 18`.

Inside the backward entry walk it reads an entry length and, after handling only zero, performs:

```rust
offset -= entry_size;
```

without requiring the nonzero entry to fit within the remaining table bytes.

Both are malformed-input subtraction boundaries before the descriptor parser.

## Format basis

EDK2's own reset-vector source documents the GUID table as:

```text
Data (arbitrary bytes identified by guid)
length from start of data to end of guid (2 bytes)
guid (16 bytes)
```

and the table footer as:

```text
length of whole table (16 bit word)
GUID (table footer, 16 bytes)
```

Therefore:

- the recognized footer requires at least 18 table bytes;
- any nonzero entry must be at least 18 bytes;
- an entry length cannot exceed the bytes remaining before the current cursor.

The candidate uses only those structural constraints.

## Baseline discriminators

Synthetic 256-byte firmware images place the exact footer GUID bytes at EOF-0x30 and the 16-bit table size at EOF-0x32.

Controls and witnesses:

1. `table_size = 18` is the minimum footer-only table. Exact-current should avoid the loop and fall back to the deprecated metadata pointer at EOF-0x20, preserving `SeekFrom::Start(0)` and `guid_found=false`.
2. `table_size = 0` recognizes the footer but underflows `table_size - 18`; ignored witness catches the panic, paired no-panic invariant is expected-red.
3. `table_size = 40` gives 22 bytes before the footer; the first synthetic entry advertises length 23. Exact-current reaches `offset -= entry_size` with `offset=22`, underflows, and panics; a second paired invariant is expected-red.

## Candidate

Add typed structural errors:

```text
InvalidGuidTableSize(table_size)
InvalidGuidTableEntrySize { entry_size, remaining }
```

Checks:

- reject recognized table size `< 18` before allocation/read/cursor arithmetic;
- preserve current zero-entry break behavior;
- for nonzero entries reject `< 18` or `> remaining` before subtraction;
- otherwise preserve the existing backward traversal and metadata-GUID handling.

Focused candidate tests cover both malformed cases and the 18-byte minimum footer control.

## Intended gates

- exact source pin and clean tree;
- minimum footer-only control green;
- undersized-table panic witness green + no-panic invariant expected-red;
- oversized-entry panic witness green + no-panic invariant expected-red;
- restore exact source before candidate;
- candidate typed structural errors + boundary control green;
- full arch + hypervisor TDX/KVM library tests;
- Clippy with warnings denied except already identified exact-current unrelated x86 baseline classes;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.

## Composition boundary

R590G touches GUID-table discovery before the TDVF descriptor. R590A and R590T touch later descriptor/section parsing. Their semantic owners are independent, but a selected parser-hardening stack should still receive an explicit composition run because all are in `arch/src/x86_64/tdx/mod.rs`.
