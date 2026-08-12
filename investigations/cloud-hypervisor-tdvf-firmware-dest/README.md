# Cloud Hypervisor TDVF BFV/CFV guest destination

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590D
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — invalid BFV/CFV guest destination reaches a guest-memory unwrap panic; existing FirmwareLoad propagation validated**

## Narrow question

When a BFV/CFV TDVF section names a guest destination outside mapped guest memory, does exact-current `Vm::populate_tdx_sections()` panic at `mem.read_volatile_from(...).unwrap()`? Can the minimum repair propagate the existing `vm_memory::GuestMemoryError` through the already-defined `Error::FirmwareLoad` channel while preserving a valid copy?

Yes. Exact-current source reproducibly panics on an unmapped BFV/CFV destination. The minimum candidate maps the same guest-memory failure to the existing `FirmwareLoad` error and propagates it with `?`, while preserving the successful copy count and bytes.

This remains separate from LF-R590E: R590E owns whether the raw source range lies inside the firmware file; R590D owns the destination-side guest-memory failure once source bytes are available.

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

so the candidate does not invent a second destination-copy error type.

## Authoritative execution

- Fieldwork tested head: `133b608558690e65eeb1a66b33b2d8cfe8c7ef37`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31590009668`
- job: `94092550442`
- artifact: `9138903752`
- artifact digest: `sha256:b1b9db109ba59d171dade030de9f7a0f4268ed0f3055d9873fea10c191b2efb9`
- features: `tdx,kvm`

## Baseline result

A 4 KiB `GuestMemoryMmap` and ordinary 64-byte file containing `0x5a` exercise the exact guest-memory API boundary. Valid control:

```text
TDVF_FIRMWARE_DEST_CONTROL copied=16 bytes=[90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
```

Invalid guest address `0x2000` reproduces the production failure:

```text
called `Result::unwrap()` on an `Err` value: InvalidGuestAddress(GuestAddress(8192))
TDVF_FIRMWARE_DEST_BASELINE panicked=true
```

The paired no-panic invariant loses on exact-current source as intended:

```text
TDVF_FIRMWARE_DEST_BASELINE_INVARIANT_RC=101
TDVF_FIRMWARE_DEST_INVARIANT panicked=true
invalid BFV/CFV guest destination must not panic the VMM
```

The workflow restores `vmm/src/vm.rs` to exact source before applying the candidate, so candidate-only evidence excludes the baseline probe.

## Candidate

Minimum candidate:

1. extract the existing BFV/CFV `read_volatile_from` operation into `copy_tdx_firmware_section(...) -> Result<usize>`;
2. map only its `GuestMemoryError` to existing `Error::FirmwareLoad`;
3. call the helper with `?` from the BFV/CFV arm;
4. add one focused regression proving invalid destination returns `FirmwareLoad(_)` and valid destination preserves count/content.

Focused result:

```text
TDVF_FIRMWARE_DEST_CANDIDATE invalid_result=FirmwareLoad(InvalidGuestAddress(GuestAddress(8192)))
TDVF_FIRMWARE_DEST_CANDIDATE copied=16 bytes=[90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
```

The returned byte count remains intentionally unchanged/ignored by the caller. Exact-read/source-EOF semantics remain a separate owner; this lane changes only panic-to-error propagation for guest destination failure.

## Candidate-only diff review

Complete candidate-only diff scope:

```text
vmm/src/vm.rs | 48 ++++++++++++++++++++++++++++++++++++++++++++----
1 file changed, 44 insertions(+), 4 deletions(-)
```

Reviewed contents are exactly:

- one tiny production firmware-copy helper using existing `Error::FirmwareLoad`;
- replacement of the one BFV/CFV `read_volatile_from(...).unwrap()` boundary;
- one focused regression with invalid and valid destination arms.

No new error type, parser validation, source-range rule, exact-read policy, Payload/PayloadParam logic, HOB behavior, or section-cardinality semantics are changed.

Candidate-only diff SHA-256:

```text
dee0bbf66069621261b7c0218737032b3ffe7b2763b14dd504493e3bf671132e
```

## Broad and quality gates

Authoritative run `31590009668` / job `94092550442`:

```text
candidate focused propagation: success
full VMM tdx,kvm library: 105 passed, 0 failed, 0 ignored
clippy: success
nightly rustfmt: success
git diff --check: success
```

The workflow uses `-D warnings` while allowing only the already identified exact-current unrelated x86 warning classes and the existing `unfulfilled-lint-expectations` class in `vmm/src/lib.rs`, outside this candidate.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor panics when a BFV/CFV firmware copy targets unmapped guest memory because `read_volatile_from()` is unconditionally unwrapped. The minimum candidate propagates the actual `InvalidGuestAddress` through the VMM's existing `FirmwareLoad` error, preserves valid copy count/content, and passes focused, full VMM, Clippy, rustfmt, and diff-hygiene gates.

This remains a distinct #590 owner. Separate lanes own BFV/CFV source-file ranges (LF-R590E), section type validity (LF-R590T), missing TdHob (LF-R590H), PayloadParam guest writes (LF-R590P), section-table pre-allocation validation (LF-R590A), and future exact-read/cardinality work.
