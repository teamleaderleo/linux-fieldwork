# Cloud Hypervisor TDX payload validation regression

Updated: 2026-08-13
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Narrow question

Does current generic payload validation accidentally disable Cloud Hypervisor's intended TDX direct-kernel handoff by rejecting `firmware + kernel` and deleting `cmdline` before `VmConfig::validate()` checks whether TDX is enabled?

## Historical contract

Cloud Hypervisor commit `3c421593c322466bca750553fa76a49e28082768` added the TDX `Payload` / `PayloadParam` consumers specifically so `--kernel` and `--cmdline` could be copied into addresses supplied by TDVF metadata.

The later configuration refactor `3793ffe888dbc9c4aaf929d1b4846e50f1122d6c` moved TDX firmware into the generic `PayloadConfig`, but its own documentation still showed:

```text
--platform tdx=on
--firmware tdshim
--kernel bzImage
--cmdline "root=/dev/vda3 console=hvc0 rw"
```

At that refactor revision, `PayloadConfig` was only a data struct; `VmConfig::validate()` required firmware for TDX but did not reject the simultaneous kernel or cmdline.

## Exact-current regression shape

Current `PayloadConfig::validate()` runs before TDX-specific validation and applies generic firmware semantics:

- `firmware + kernel` -> `FirmwarePlusOtherPayloads`;
- `firmware + cmdline` -> validation succeeds only after setting `cmdline = None`;
- `firmware + initramfs` -> initramfs is also cleared.

Only afterward does `VmConfig::validate()` compute whether TDX is enabled and require firmware.

That ordering conflicts with the TDX `Payload` and `PayloadParam` consumers still present in `vmm/src/vm.rs`.

## Baseline matrix

Use full `VmConfig::validate()` with serde-built, hardware-free configurations and dummy paths:

1. TDX + firmware + kernel + cmdline: current validation must fail with `FirmwarePlusOtherPayloads`.
2. TDX + firmware + cmdline, no kernel: current validation succeeds but cmdline becomes `None`.
3. non-TDX + firmware + kernel: remains rejected; this is a negative control for candidate scope.
4. non-TDX + firmware + cmdline: current generic behavior continues to clear cmdline.

No firmware files or TDX hardware are needed because this is purely configuration validation.

## Minimum candidate

Keep generic `PayloadConfig::validate()` semantics unchanged for non-TDX callers. Add an internal TDX-aware validation path selected by `VmConfig::validate()` before generic payload mutation:

- TDX firmware + kernel is allowed;
- TDX cmdline is preserved with or without kernel, because `PayloadParam` consumes it;
- TDX initramfs remains ignored/cleared because the current TDVF population path has no initramfs consumer;
- non-TDX firmware+kernel remains rejected;
- non-TDX firmware+cmdline remains ignored as before;
- existing IGVM and fw_cfg validation still runs.

## Gates

- exact source pin and clean tree;
- baseline full-`VmConfig` matrix;
- candidate full-`VmConfig` matrix;
- full `vmm` library tests with `tdx,kvm`;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only diff and SHA-256 receipt.

## Follow-up implication

If this regression is proven and the TDX direct-kernel mode is restored, the previously isolated TDVF `Payload` guest-memory-copy panic becomes reachable again. Do not compose that experimental repair until this configuration owner is independently resolved first.
