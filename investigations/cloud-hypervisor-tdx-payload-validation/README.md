# Cloud Hypervisor TDX payload validation regression

Updated: 2026-08-13
Owning issue: #654
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Tested final Fieldwork head: `921b7ecd5ee25889000d1fcaabbcc578a4cbbc69`
External-contact state: false; upstream remains read-only
State: **PROVEN**

## Result

Current generic payload validation disables Cloud Hypervisor's documented TDX direct-kernel handoff in two ways before TDX-specific validation runs:

- TDX `firmware + kernel` is rejected as `FirmwarePlusOtherPayloads`;
- TDX `firmware + cmdline` validates only after silently clearing `cmdline`.

This conflicts with both exact-current TDX documentation and the still-present TDX implementation that opens the kernel separately and copies kernel/cmdline through TDVF `Payload` / `PayloadParam` sections.

The minimum candidate selects a TDX-aware payload-validation mode only when `platform.tdx` is true. It allows the TDX firmware+kernel combination and preserves cmdline while leaving ordinary non-TDX firmware rules unchanged. Full VMM, Clippy, formatting, and diff-hygiene gates passed.

## Regression introduction

The regression was introduced by Cloud Hypervisor commit:

`dd8687aebbae67e1fcf9a4c2b1063c2ecbd60d27`

`vmm: add enum PayloadConfigError validation to improve error reporting`

Merged 2025-08-15.

That change added `PayloadConfigError`, introduced the global firmware-vs-kernel mutual exclusion, and changed `VmConfig::validate()` to invoke generic payload validation before the existing TDX-specific checks. Its rationale enumerated ordinary firmware-or-kernel bootstrap modes but omitted the already-existing TDX firmware+kernel special case.

## Contract evidence

TDX direct-kernel support predates the regression:

- `3c421593c322466bca750553fa76a49e28082768` added the TDVF `Payload` / `PayloadParam` consumers so the user-supplied kernel and cmdline could be copied into TDVF-designated locations.
- `3793ffe888dbc9c4aaf929d1b4846e50f1122d6c` moved TDX firmware into generic `PayloadConfig` while still documenting `--platform tdx=on --firmware tdshim --kernel bzImage --cmdline ...`.
- exact-current `docs/intel_tdx.md` still advertises TDShim direct boot with firmware + kernel + cmdline.
- completed upstream design issue #4445 explicitly lists “A TDX firmware + kernel image + command line + (optional initramfs)” as a target payload use case.

The exact-current implementation behind that documented mode is also still present:

- `Vm::new()` opens `payload.kernel` into the TDX-only `self.kernel` field;
- `populate_tdx_sections()` consumes that file for `TdvfSectionType::Payload` and uses cmdline for `PayloadParam`;
- TDX returns early from ordinary async `load_payload()`, so allowing firmware+kernel does not enter generic boot code's firmware/kernel `unreachable!()` case.

## Baseline execution

Authoritative baseline + candidate run:

- run `31665016695`
- job `94337586101`
- tested carrier `0727b069684e08394512995610f65e2f9c6c8b6f`
- candidate-only diff SHA-256 `0af9d875fd2b82099fe15f7f6a910d9500293990846bda6d677da1ea16b0da5e`

Exact-current TDX baseline:

```text
TDX_PAYLOAD_VALIDATION_BASELINE kernel_result=Err(PayloadError(FirmwarePlusOtherPayloads))
TDX_PAYLOAD_VALIDATION_BASELINE cmdline_result=Ok({}) cmdline_after=None
TDX_PAYLOAD_VALIDATION_KERNEL_INVARIANT_RC=101
TDX_PAYLOAD_VALIDATION_CMDLINE_INVARIANT_RC=101
```

Non-TDX controls:

```text
non_tdx_kernel=Err(PayloadError(FirmwarePlusOtherPayloads))
non_tdx_cmdline=Ok({}) cmdline_after=None
```

Candidate:

```text
TDX_PAYLOAD_VALIDATION_INVARIANT kernel_result=Ok({})
TDX_PAYLOAD_VALIDATION_INVARIANT cmdline_result=Ok({}) cmdline_after=Some("console=hvc0 root=/dev/vda")
```

The candidate preserved both non-TDX controls.

The baseline/candidate run passed 108 VMM tests with 2 intentionally ignored baseline witnesses. Its only red gate was a Clippy lint in the temporary test probe (`assertions_on_result_states`), not product code. The probe was then cleaned without touching the product candidate.

## Final immutable-candidate receipt

Final hosted run:

- run `31665303619`
- job `94338464368`
- tested Fieldwork head `921b7ecd5ee25889000d1fcaabbcc578a4cbbc69`
- artifact `9167722919`
- artifact digest `sha256:76422931a573bce7428db680ec895bf4d59094fa8ab8bcec239b92878c507b1a`
- candidate-only diff SHA-256 `0af9d875fd2b82099fe15f7f6a910d9500293990846bda6d677da1ea16b0da5e`

The final run first re-created the product candidate from exact source and asserted that its diff hash was byte-for-byte identical to the previously tested candidate. Then it applied only the cleaned test probe.

Final gates:

```text
focused TDX + non-TDX matrix: success
full VMM tdx,kvm: 108 passed, 0 failed, 2 intentionally ignored baseline witnesses
Clippy: success
nightly rustfmt: success
git diff --check: success
```

Complete candidate-only diff review: two product files only, 74 diff lines total:

```text
vmm/src/config.rs
vmm/src/vm_config.rs
```

Product semantics:

1. compute `tdx_enabled` before payload validation;
2. call an internal TDX-aware payload validator only for TDX;
3. allow TDX firmware + kernel;
4. preserve TDX cmdline;
5. continue clearing initramfs in this narrow candidate because current TDVF population has no initramfs consumer;
6. keep public generic payload validation and non-TDX behavior unchanged.

## Disposition

**PROVEN.** Exact-current Cloud Hypervisor rejects a documented, implemented TDX direct-kernel boot configuration and silently discards its documented cmdline. The minimum TDX-aware validation candidate is validated.

## Follow-up

Restoring this documented configuration changes the reachability analysis of issue #590's TDVF `Payload` consumer. The previously isolated guest-memory destination panic must now be revalidated as a separate supported-reachable owner stacked after this configuration candidate.

Keep separate:

- TDX optional initramfs support;
- TDVF Payload guest-memory error propagation;
- TDVF Payload header/body exact-read semantics;
- malformed TDVF metadata validation.
