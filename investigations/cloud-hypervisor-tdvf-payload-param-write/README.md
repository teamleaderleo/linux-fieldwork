# Cloud Hypervisor TDVF PayloadParam guest-memory write

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590P
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — invalid PayloadParam destination reaches a guest-memory unwrap panic; typed propagation validated**

## Narrow question

When a TDVF `PayloadParam` section points outside mapped guest memory, does exact-current `Vm::populate_tdx_sections()` panic at the existing `mem.write_slice(...).unwrap()` boundary? Can the minimum repair propagate the underlying `vm_memory::GuestMemoryError` through the function's existing `Result` without adding broader metadata policy?

Yes. Exact-current source reproducibly panics on an unmapped PayloadParam address with `InvalidGuestAddress`. The minimum candidate maps that same guest-memory failure to typed `Error::LoadPayloadParam` and propagates it with `?`, while preserving the valid write bytes and clearing focused, full VMM, Clippy, rustfmt, and diff-hygiene gates.

## Source owner

The exact-current `PayloadParam` arm generates the kernel command line and then performs:

```rust
mem.write_slice(
    cmdline.as_cstring().unwrap().as_bytes_with_nul(),
    GuestAddress(section.address),
)
.unwrap();
```

The same VMM already uses `vm_memory::GuestMemoryError` as the source for typed guest-memory copy failures. This lane keeps the repair at the exact write boundary rather than adding destination metadata prevalidation or translating the failure to generic I/O.

## Authoritative execution

- Fieldwork tested head: `73ea0d88b006be2df60cb93c0150797a985314a0`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31589641689`
- job: `94091382581`
- artifact: `9138749769`
- artifact digest: `sha256:d4211e4b1b2188643705b8c09fec4388d49b8ee6425ed7cbcdb6fdc74d85b230`
- features: `tdx,kvm`

## Baseline result

A 4 KiB `GuestMemoryMmap` exercises the same guest-memory API boundary. The valid control writes the ordinary command-line bytes at `0x800` and reads them back unchanged:

```text
TDVF_PAYLOAD_PARAM_CONTROL bytes=[99, 111, 110, 115, 111, 108, 101, 61, 116, 116, 121, 83, 48, 0]
```

The invalid address `0x2000` reproduces the current panic owner:

```text
called `Result::unwrap()` on an `Err` value: InvalidGuestAddress(GuestAddress(8192))
TDVF_PAYLOAD_PARAM_BASELINE panicked=true
```

The paired no-panic invariant loses on baseline as intended:

```text
TDVF_PAYLOAD_PARAM_BASELINE_INVARIANT_RC=101
TDVF_PAYLOAD_PARAM_INVARIANT panicked=true
invalid PayloadParam destination must not panic the VMM
```

The workflow restores `vmm/src/vm.rs` to exact source before applying the candidate, so candidate-only evidence excludes the probe.

## Candidate

Minimum VMM-side candidate:

1. add typed `Error::LoadPayloadParam(#[source] vm_memory::GuestMemoryError)`;
2. add `write_tdx_payload_param(&GuestMemoryMmap, &[u8], u64) -> Result<()>` around the existing `write_slice()`;
3. map only the guest-memory failure to `LoadPayloadParam`;
4. call the helper with `?` from the existing PayloadParam arm;
5. add one focused regression covering invalid and valid destinations.

Focused result:

```text
TDVF_PAYLOAD_PARAM_CANDIDATE invalid_result=LoadPayloadParam(InvalidGuestAddress(GuestAddress(8192)))
TDVF_PAYLOAD_PARAM_CANDIDATE control_bytes=[99, 111, 110, 115, 111, 108, 101, 61, 116, 116, 121, 83, 48, 0]
```

The candidate deliberately leaves `cmdline.as_cstring().unwrap()`, section cardinality, other TDVF destination paths, BFV/CFV firmware source ranges, missing TdHob, and payload-file exact-read semantics separate.

## Candidate-only diff review

Complete authoritative candidate-only diff scope:

```text
vmm/src/vm.rs | 34 ++++++++++++++++++++++++++++++----
1 file changed, 30 insertions(+), 4 deletions(-)
```

Reviewed contents are exactly:

- one typed `LoadPayloadParam` error variant;
- one tiny production write helper;
- replacement of the one PayloadParam `write_slice(...).unwrap()` boundary;
- one focused regression.

Candidate-only diff SHA-256:

```text
78d696341cf53662559aecde88d7462af0ae6302052cd7f4633a351d50347ba9
```

## Broad and quality gates

Authoritative run `31589641689` / job `94091382581`:

```text
candidate focused propagation: success
full VMM tdx,kvm library: 105 passed, 0 failed, 0 ignored
clippy: success
nightly rustfmt: success
git diff --check: success
```

Clippy uses `-D warnings` while allowing the already identified exact-current unrelated x86 warning classes plus `unfulfilled-lint-expectations`; the latter is required by an existing expectation in `vmm/src/lib.rs:796`, outside the candidate file/lines.

## Harness / candidate-materialization history

Earlier runs remain separate from the final product verdict:

1. Run `31588612727` proved the baseline but the first candidate call passed the loaded guest-memory guard by value instead of borrowing it; the compiler required `&mem`. This was a candidate-carrier compile error, not product behavior.
2. Run `31589321810` repaired that borrow and passed the candidate-focused test plus the full 105/0 VMM suite. Its only red was the same unrelated exact-current `unfulfilled-lint-expectations` Clippy failure already seen in LF-R590H.
3. The authoritative run above repeats the same product/candidate behavior with only that baseline lint class suppressed and every gate green.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor panics when a `PayloadParam` section targets unmapped guest memory because the guest-memory write result is unconditionally unwrapped. The minimum typed propagation candidate preserves valid writes, returns the actual `InvalidGuestAddress` through `LoadPayloadParam`, and passes focused, full VMM, Clippy, rustfmt, and diff-hygiene gates.

This remains a distinct #590 owner. Separate lanes own BFV/CFV raw source ranges (LF-R590E), missing TdHob (LF-R590H), section-type validity (LF-R590T), BFV/CFV guest destination handling (LF-R590D), and future exact-read/cardinality work.
