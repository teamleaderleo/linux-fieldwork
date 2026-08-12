# Cloud Hypervisor TDVF BFV/CFV exact-read follow-up

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590X
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: PROVEN

## Result

Exact-current BFV/CFV population uses non-exact `read_volatile_from()` and ignores its returned byte count. A short ordinary firmware source can therefore be accepted as a successful partial copy.

The repaired hosted discriminator proved:

```text
TDVF_SHORT_READ_CONTROL requested=16 copied=16
TDVF_SHORT_READ_BASELINE requested=16 copied=8 bytes=[90, 90, 90, 90, 90, 90, 90, 90, 0, 0, 0, 0, 0, 0, 0, 0]
TDVF_SHORT_READ_BASELINE_INVARIANT_RC=101
TDVF_SHORT_READ_INVARIANT requested=16 copied=8
```

So with a valid guest destination and an 8-byte source, a 16-byte request succeeds with only 8 bytes copied; the untouched guest tail remains zero.

## Dependency contract

Exact Cloud Hypervisor pins `vm-memory = 0.18.0`. Its `read_volatile_from()` returns a completed byte count, while `read_exact_volatile_from()` converts `completed != expected` into:

```text
GuestMemoryError::PartialBuffer { expected, completed }
```

R590X uses that existing exact-read contract rather than inventing a parallel file-length error.

## Validated stacked candidate

R590X is intentionally stacked on the already-proven BFV/CFV destination-error layer LF-R590D.

The workflow first materialized LF-R590D from immutable Fieldwork commit:

`133b608558690e65eeb1a66b33b2d8cfe8c7ef37`

and verified its exact diff SHA-256:

`dee0bbf66069621261b7c0218737032b3ffe7b2763b14dd504493e3bf671132e`

Only then was the X delta applied:

```rust
fn copy_tdx_firmware_section(
    mem: &GuestMemoryMmap,
    firmware_file: &mut File,
    address: u64,
    size: usize,
) -> Result<()> {
    mem.read_exact_volatile_from(GuestAddress(address), firmware_file, size)
        .map_err(Error::FirmwareLoad)
}
```

The X-only delta SHA-256 is:

`588ba336126224078808b9ce2f8ca3608af35621fbf0bf636a2f940cebccb3d6`

The complete D+X stacked diff SHA-256 is:

`3ed41f84dc89eeeedfdf8ae734da28cf6a383599a6f55461cab2a6f5a631e252`

Complete stacked diff review found only the existing D helper/call-site regression plus the X exact-read conversion and X focused regression.

## Candidate evidence

Short source:

```text
TDVF_SHORT_READ_CANDIDATE short_result=FirmwareLoad(PartialBuffer { expected: 16, completed: 8 })
```

Valid exact-length control:

```text
TDVF_SHORT_READ_CANDIDATE control_bytes=[90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
```

The already-proven destination-error regression also remained green after the exact-read delta.

## Validation receipt

Tested Fieldwork head:

`3201f2235802b8890cd01443a8f9c4c00883bead`

Hosted Actions:

- run: `31595478497`
- job: `94109814850`
- conclusion: success
- artifact: `9141095709`
- artifact digest: `sha256:9060ad1bc5d4aa6998637cefee131dc5d5d2bc91a0290d12ddcd2da48a9663ae`

All gates passed:

- exact source pin and structural source-boundary check;
- baseline exact-length control;
- baseline successful short-copy witness;
- baseline exact-copy invariant expected red;
- exact-source restoration;
- byte-for-byte verification of LF-R590D base diff;
- exact-read-only delta;
- focused destination + exact-read matrix;
- full `vmm` `tdx,kvm`: **106 passed / 0 failed**;
- Clippy with warnings denied except previously identified exact-current baseline classes;
- nightly rustfmt;
- `git diff --check`;
- complete X-only and stacked diff review.

## Harness note

The first execution run (`31592742655`) produced no product evidence because a brittle post-format source-text assertion failed before any baseline test ran. Artifact `9139811421` showed the probe had only added tests and had not changed the production copy path. The v2 workflow replaced that assertion with a structural source-boundary check before instrumentation; no candidate semantics changed because of the harness repair.

## Remaining adjacent owners

Keep separate:

- Payload file header/body I/O and Payload guest destination failures;
- TDX-init host-range error propagation (independently proven by LF-R590M);
- earlier start-only boot-RAM range decision;
- parser and section-cardinality policy.

The record-only commit after this tested head is not a substitute for the tested carrier.
