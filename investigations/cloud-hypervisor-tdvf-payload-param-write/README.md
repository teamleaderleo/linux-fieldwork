# Cloud Hypervisor TDVF PayloadParam guest-memory write

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590P
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: EXECUTING

## Narrow question

When a TDVF `PayloadParam` section points outside mapped guest memory, does exact-current `Vm::populate_tdx_sections()` panic at the existing `mem.write_slice(...).unwrap()` boundary? Can the minimum repair propagate the underlying `vm_memory::GuestMemoryError` through the function's existing `Result` without adding broader metadata policy?

## Source owner

The current `PayloadParam` arm generates the kernel command line and then performs:

```rust
mem.write_slice(
    cmdline.as_cstring().unwrap().as_bytes_with_nul(),
    GuestAddress(section.address),
)
.unwrap();
```

The same VMM already uses `vm_memory::GuestMemoryError` as the source for other typed guest-memory copy failures (`InitramfsRead`, `FirmwareLoad`). This lane therefore keeps the repair at the write boundary rather than pre-validating section addresses or translating the failure to `io::Error`.

## Baseline discriminator

A 4 KiB `GuestMemoryMmap` is used directly at the same guest-memory API boundary:

- valid control writes `b"console=ttyS0\0"` at `0x800` and reads it back;
- ignored baseline witness writes at `0x2000` and catches the current `unwrap()` panic;
- normal invariant asserts the same invalid address must not panic and is expected-red on baseline.

After baseline execution, the workflow restores `vmm/src/vm.rs` to exact source before applying the candidate so the candidate-only diff contains no probe instrumentation.

## Candidate

Minimum VMM-side candidate:

1. add typed `Error::LoadPayloadParam(#[source] vm_memory::GuestMemoryError)`;
2. add a tiny production helper wrapping `GuestMemoryMmap::write_slice()` and mapping only that error;
3. call the helper with `?` from the existing `PayloadParam` arm;
4. focused regression proves an invalid address returns the typed error and the valid control writes identical bytes.

The candidate deliberately leaves these separate:

- `cmdline.as_cstring().unwrap()` semantics;
- missing/duplicate PayloadParam cardinality;
- guest destination prevalidation for other TDVF section types;
- BFV/CFV raw firmware source ranges (already proven independently by LF-R590E);
- missing TdHob (owned independently by LF-R590H);
- payload-file read semantics and exact-read handling.

## Intended gates

- exact source pin and clean tree;
- baseline valid write/readback control green;
- baseline invalid-address panic witness green;
- baseline no-panic invariant expected red;
- restore exact source before candidate;
- candidate typed propagation + valid control green;
- source check that the PayloadParam `write_slice(...).unwrap()` boundary is gone;
- full `vmm` library tests with `tdx,kvm` and hosted `/dev/kvm` permission repaired if present;
- Clippy with candidate warnings denied, suppressing only known exact-current unrelated x86 warning classes if required;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.
