# Cloud Hypervisor TDVF missing-TdHob panic

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590H
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: **PROVEN — missing TdHob reaches a production unwrap panic; typed VMM repair validated**

## Narrow question

When TDVF metadata contains no `TdHob` section, does exact-current Cloud Hypervisor reach the consumer boundary with `hob_offset == None` and panic at `TdHob::start(hob_offset.unwrap())`? Can the minimum VMM-side repair preserve all present-HOB behavior while returning a typed error for the missing case?

Yes. Exact-current source reproducibly panics on the missing case. The minimum candidate converts only that terminal `None` case into `Error::TdxHobMissing`, preserves present-HOB behavior and the existing `Option<u64>` return contract, and clears focused, full VMM, Clippy, rustfmt, and diff-hygiene gates.

## Source owner

`Vm::populate_tdx_sections()` initializes `hob_offset = None`, overwrites it when a `TdvfSectionType::TdHob` record is encountered, and after processing all sections unconditionally executes:

```rust
let mut hob = TdHob::start(hob_offset.unwrap());
```

This carrier deliberately does not change TDVF section cardinality or duplicate-section policy. The current loop's semantics are retained: if one or more TdHob records exist, the final observed address remains the HOB start. Only the `None` terminal case is changed.

EDK2's TDVF metadata source documents `TD_HOB` as the section designating the region where the host VMM writes physical-memory information for guest firmware. That supports treating Cloud Hypervisor's missing-HOB state as malformed/unusable input for this consumer, without making a broader claim that every external TDVF dialect must have identical section cardinality.

## Authoritative execution

- Fieldwork tested head: `b70ad71716ea26afd03b490da909a85050290afb`
- exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
- workflow run: `31589563250`
- job: `94091131632`
- artifact: `9138587527`
- artifact digest: `sha256:33f46d71c6f6de434f6f965cabcafbfd994b8ac5aa3a83cdc8f40c8b1339dc59`
- features: `tdx,kvm`

## Baseline result

The baseline probe mirrors the production scan and terminal unwrap boundary. A present-HOB control remains green:

```text
TDVF_HOB_CONTROL offset=0x4000
```

The missing-HOB witness reproduces the exact failure owner:

```text
called `Option::unwrap()` on a `None` value
TDVF_HOB_BASELINE sections=1 panicked=true
```

The paired no-panic safety invariant loses on exact-current source as intended:

```text
TDVF_HOB_BASELINE_INVARIANT_RC=101
TDVF_HOB_INVARIANT sections=1 panicked=true
missing TdHob must not panic the VMM
```

The workflow then restores `vmm/src/vm.rs` to exact source before applying the candidate, so candidate-only evidence excludes the baseline probe.

## Candidate

Minimum VMM-side candidate:

1. add typed `Error::TdxHobMissing`;
2. add `required_tdx_hob_offset(Option<u64>) -> Result<u64>`;
3. derive a separate `hob_start` for `TdHob::start()` instead of unwrapping;
4. leave the existing `hob_offset: Option<u64>` intact for the function's existing `Ok(hob_offset)` return;
5. add one focused regression proving `None -> TdxHobMissing` and `Some(0x4000) -> 0x4000`.

Focused result:

```text
TDVF_HOB_CANDIDATE missing_result=TdxHobMissing
TDVF_HOB_CANDIDATE control_offset=0x4000
```

This retains section-processing order and duplicate-TdHob behavior and does not touch BFV/CFV file-range validation, guest destination ranges, Payload/PayloadParam handling, HOB size/layout, or TDX memory initialization.

## Candidate-only diff review

Complete candidate-only diff scope:

```text
vmm/src/vm.rs | 24 +++++++++++++++++++++++-
1 file changed, 23 insertions(+), 1 deletion(-)
```

Reviewed contents are exactly:

- one typed error variant;
- one tiny conversion helper;
- replacement of the single production `hob_offset.unwrap()` boundary;
- one focused regression.

Candidate-only diff SHA-256:

```text
0b4158f175543eeb9dc6e7c1ad188ce084518a59d663bef80880514820e51756
```

## Broad and quality gates

Authoritative run `31589563250` / job `94091131632`:

```text
candidate focused boundary: success
full VMM tdx,kvm library: 105 passed, 0 failed, 0 ignored
clippy: success
nightly rustfmt: success
git diff --check: success
```

Clippy uses `-D warnings` while allowing the previously encountered exact-current unrelated x86 warning classes plus `unfulfilled-lint-expectations`. The latter is required because exact-current `vmm/src/lib.rs:796` has an existing `#[expect(clippy::collapsible_match)]` that this Rust 1.89 Clippy considers unfulfilled; it is outside the candidate file/lines and was independently reproduced before the allow was added.

## Harness / candidate-materialization history

Earlier non-authoritative runs are retained separately from the product verdict:

1. Run `31588250565` proved the baseline panic but the first candidate materialization shadowed `hob_offset: Option<u64>` with a `u64`, conflicting with the existing `Result<Option<u64>>` return. This was a candidate-carrier compile bug, not product evidence.
2. Run `31589150820` repaired that materialization and passed the candidate-focused gate plus the full 105/0 VMM suite. Its only red was the unrelated existing `unfulfilled-lint-expectations` Clippy failure in `vmm/src/lib.rs:796`.
3. The authoritative run above repeats the same product/candidate evidence with that exact baseline lint class suppressed and every gate green.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor panics when the processed TDVF section set lacks a `TdHob` record because `populate_tdx_sections()` unconditionally unwraps the missing offset. The minimum VMM-side candidate returns typed `TdxHobMissing`, preserves the existing present-HOB and return semantics, and passes focused, full VMM, Clippy, rustfmt, and diff-hygiene gates.

This remains a distinct #590 owner. Separate lanes own BFV/CFV raw source ranges (LF-R590E), section-type validity (LF-R590T), PayloadParam guest-memory write propagation (LF-R590P), and future destination/cardinality/exact-read work.
