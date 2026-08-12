# Cloud Hypervisor TDVF BFV/CFV guest destination

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590D
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING

## Narrow question

When a BFV/CFV TDVF section names a guest destination outside mapped guest memory, does exact-current `Vm::populate_tdx_sections()` panic at `mem.read_volatile_from(...).unwrap()`? Can the minimum repair propagate the existing `vm_memory::GuestMemoryError` through the already-defined `Error::FirmwareLoad` channel while preserving a valid copy?

This is separate from LF-R590E. R590E owns whether the raw source range lies inside the firmware file. R590D owns the destination-side guest-memory failure after the file source is available.

## Source owner

The exact-current BFV/CFV arm seeks the firmware file and then performs:

```rust
mem.read_volatile_from(
    GuestAddress(section.address),
    &mut firmware_file,
    section.data_size as usize,
)
.unwrap();
```

The same VMM already defines:

```rust
#[error("Failed to copy firmware to memory")]
FirmwareLoad(#[source] vm_memory::GuestMemoryError),
```

so this lane does not invent a second destination-copy error type.

## Baseline discriminator

Use a 4 KiB `GuestMemoryMmap` and a 64-byte ordinary file containing `0x5a` bytes:

- valid control copies 16 bytes to guest address `0x800`, verifies return count 16 and reads back sixteen `0x5a` bytes;
- ignored witness attempts the same copy to unmapped guest address `0x2000` and catches the current unwrap panic;
- normal no-panic invariant repeats the invalid destination and is expected-red on baseline.

The probe mirrors the exact production guest-memory API call and unwrap boundary. After baseline execution the workflow restores `vmm/src/vm.rs` to exact source before applying the candidate.

## Candidate

Minimum candidate:

1. extract the existing BFV/CFV `read_volatile_from` operation into a tiny production helper returning `Result<usize>`;
2. map only its `GuestMemoryError` to existing `Error::FirmwareLoad`;
3. call that helper with `?` from the BFV/CFV arm;
4. focused regression proves invalid destination returns `FirmwareLoad(_)` and valid destination preserves count/content.

The returned byte count remains intentionally unchanged/ignored by the caller. Exact-read/source-EOF semantics are owned separately; this lane changes only panic-to-error propagation for guest destination failure.

## Intended gates

- exact source pin and clean tree;
- baseline valid copy control green;
- baseline invalid-address panic witness green;
- baseline no-panic invariant expected red;
- restore exact source before candidate;
- focused typed propagation + valid content/count control green;
- full `vmm` library tests with `tdx,kvm`;
- Clippy with `-D warnings`, suppressing only the known exact-current unrelated x86/unfulfilled-expectation baseline classes;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.

## Stop/split conditions

Do not broaden this candidate into:

- BFV/CFV file-length/range validation (LF-R590E);
- exact byte-count enforcement or firmware truncation TOCTOU;
- Payload copy error propagation;
- PayloadParam writes (LF-R590P);
- missing TdHob (LF-R590H);
- section type validity (LF-R590T);
- guest region allocation policy or address/size prevalidation.
