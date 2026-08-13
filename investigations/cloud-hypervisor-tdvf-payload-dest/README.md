# Cloud Hypervisor TDVF Payload guest-memory destination reachability

Updated: 2026-08-13
Owning issue: #590
Worker/variant: LF-R590Q
Fieldwork base: `f9a45e6a311b59aed58dd6ed525a5d38df1e30b6`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Tested Fieldwork head: `3b671c290a675d86f3c606f99185c5c94488fe77`
External-contact state: false; upstream remains read-only
State: **NEGATIVE FOR SUPPORTED TDX CONFIGURATION / CANDIDATE NOT SELECTED**

## Question and disposition

Exact-current `Vm::populate_tdx_sections()` contains an unwrapped guest-memory copy in the `TdvfSectionType::Payload` arm. An isolated production-shaped helper proves that an unmapped destination panics and that a tiny typed propagation candidate would remove the panic.

However, source reachability review after execution established that the `Payload` arm's file-backed body is not entered by a supported, validated TDX boot configuration:

1. `PayloadConfig::validate()` rejects `firmware + kernel` with `FirmwarePlusOtherPayloads`.
2. `VmConfig::validate()` requires `firmware` when TDX is enabled.
3. `Vm::new()` re-runs `config.validate()` before VM construction, including configurations previously accepted/stored by the HTTP `vm.create` path.
4. The `TdvfSectionType::Payload` arm performs header/body work only inside `if let Some(payload_file) = self.kernel.as_mut()`.

Therefore a validated TDX configuration has `firmware = Some(...)` and `kernel = None`, so the branch containing the remaining Payload header/body unwraps is skipped.

**Disposition:** do not promote the candidate and do not count this as a supported-configuration Cloud Hypervisor bug. Preserve the run as negative reachability evidence and revisit only if the configuration contract changes or another supported construction path supplies `self.kernel` for TDX.

## Isolated execution evidence

Authoritative hosted run:

- run `31662905270`
- job `94331272368`
- tested head `3b671c290a675d86f3c606f99185c5c94488fe77`
- artifact `9166870995`
- artifact digest `sha256:c0d0c92b167bf395c2e7b3f72cbc85688e69cbbbdc764377e3325558341086fd`

The isolated baseline used an ordinary 64-byte file and a 4 KiB `GuestMemoryMmap`:

```text
valid destination 0x800 -> copied=16, bytes all 0x6b
invalid destination 0x2000 -> InvalidGuestAddress(GuestAddress(8192)) -> current unwrap panics
TDVF_PAYLOAD_DEST_BASELINE_INVARIANT_RC=101
```

The experimental candidate added `Error::LoadPayloadMemory(GuestMemoryError)`, wrapped only the existing Payload copy, and returned:

```text
TDVF_PAYLOAD_DEST_CANDIDATE invalid_result=LoadPayloadMemory(InvalidGuestAddress(GuestAddress(8192)))
TDVF_PAYLOAD_DEST_CANDIDATE copied=16 bytes=[107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107]
```

Candidate-only diff SHA-256:

`298ac3ea1ce3062f3967880098d1ed142487a38bc90c64729ae6682289e13772`

The experimental candidate also passed:

```text
full VMM tdx,kvm library: 105 passed, 0 failed, 0 ignored
candidate focused propagation: success
clippy: success
nightly rustfmt: success
git diff --check: success
```

Those green gates establish that the local repair is mechanically viable; they do **not** establish product reachability and are not grounds to select it.

## Why the HTTP path does not reopen the claim

`/api/v1/vm.create` deserializes and stores a `VmConfig` without validating it at that endpoint. That initially looked like a possible route to `firmware + kernel`.

The later boot path closes it: `Vm::new()` calls `config.validate()` before construction. Thus an HTTP-stored invalid payload combination still fails validation before `self.kernel` is opened or `populate_tdx_sections()` executes.

## Remaining useful research

Keep separate and prioritize reachable TDVF semantics, especially relationships between BFV/CFV `data_size` (bytes copied from the firmware file) and `size` (declared memory extent later initialized/measured by TDX).

Do not create a Payload header/body exact-read candidate unless a supported TDX configuration path that reaches `self.kernel` is first demonstrated.
