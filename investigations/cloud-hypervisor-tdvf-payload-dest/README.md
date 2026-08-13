# Cloud Hypervisor TDVF Payload guest-memory destination panic

Updated: 2026-08-13
Owning issue: #590
Worker/variant: LF-R590Q
Fieldwork base: `f9a45e6a311b59aed58dd6ed525a5d38df1e30b6`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Narrow question

When a TDVF `Payload` section names a guest address that is not backed by guest memory, does exact-current `Vm::populate_tdx_sections()` panic at the payload `mem.read_volatile_from(...).unwrap()` boundary? Can the minimum repair propagate that guest-memory failure as a payload-specific typed VMM error while preserving a valid payload copy?

This is separate from:

- `PayloadParam`, whose generated command line is written with `write_slice()`;
- BFV/CFV firmware-copy destination handling;
- payload-file header I/O and exact-read semantics;
- later `init_tdx_memory()` host-range validation.

## Exact source owner

The `Payload` arm already maps file seek/rewind failures through `Error::LoadPayload(io::Error)`, but the actual payload-to-guest copy is:

```rust
mem.read_volatile_from(
    GuestAddress(section.address),
    payload_file,
    payload_size as usize,
)
.unwrap();
```

A `GuestMemoryError` at this boundary is therefore converted into a VMM panic.

## Baseline discriminator

Use an ordinary 64-byte file and a 4 KiB `GuestMemoryMmap`:

- valid control: destination `0x800`, copy 16 bytes -> returns 16 and exact bytes are present;
- ignored malformed witness: destination `0x2000` -> current `.unwrap()` panics on `InvalidGuestAddress`;
- normal expected-red invariant: the same invalid destination must not panic.

No TDX hardware is needed because the test exercises the exact guest-memory copy primitive and the same unwrap contract as the production Payload arm.

## Minimum candidate

1. add typed `Error::LoadPayloadMemory(GuestMemoryError)`;
2. add a tiny `copy_tdx_payload()` helper around the existing non-exact `read_volatile_from()` call;
3. replace only the Payload arm unwrap with `...?`;
4. focused regression proves invalid destination returns the typed payload-memory error and valid copy count/content are unchanged.

This lane deliberately leaves successful-short-copy semantics unchanged so payload exact-read behavior can be owned separately.

## Gates

- exact upstream source pin and clean tree;
- baseline valid control;
- baseline invalid-destination panic witness;
- baseline no-panic invariant expected red;
- restore exact source before candidate;
- focused typed propagation + valid-content control;
- full `vmm` library tests with `tdx,kvm`;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only diff and SHA-256 receipt.
