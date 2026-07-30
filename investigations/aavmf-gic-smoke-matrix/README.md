# AAVMF boot behavior across QEMU GIC modes

Tracking: issue #246, Nixpkgs issue #485220, and the ecosystem candidate scan.

## TL;DR

Newer Nixpkgs AAVMF firmware was reported to stop after its UEFI banner under AArch64 macOS QEMU/HVF. The latest public finding says removing `gic-version=max` allows the same firmware to boot.

The public standalone flake does not test AAVMF on x86_64 Linux: it switches to x86 firmware there. This investigation uses current x86_64-linux QEMU's AArch64 system emulator under TCG and runs exact good, bad, and current `aarch64-linux` firmware through default, GICv2, GICv3, and `max` machine modes.

The pass marker is systemd-boot startup from an EFI filesystem, not merely the firmware banner.

## Explain like I'm five

AAVMF is the alarm clock that wakes an AArch64 virtual computer.

The interrupt controller—GIC—is the doorbell system. QEMU can offer an older doorbell, a newer doorbell, or say “use the newest one available.”

The reported failure looks like this:

```text
firmware wakes up
→ prints its name
→ newer/max doorbell selected
→ never reaches the boot menu
```

Removing `max` lets the boot menu appear.

The question is whether the firmware and doorbell disagree everywhere, or only when Apple's HVF accelerator is involved.

## Why care

The answer changes the owner and fix:

- same failure under TCG: firmware/GIC compatibility candidate;
- only HVF fails: QEMU/HVF or host-accelerator boundary;
- old firmware works and new firmware fails broadly: firmware revision or pflash layout;
- current firmware passes: candidate expired or changed shape;
- no AArch64 artifacts available to the runner: capability gap, not a product verdict.

A test that stops at the UEFI banner would certify the exact broken state. The matrix creates a FAT EFI filesystem with `BOOTAA64.EFI` and waits for systemd-boot output.

## Live overlap

The 2026-07-31 refresh found:

- Nixpkgs PR #489505: draft enabling `QEMU_PV_VARS`;
- Nixpkgs PR #522698: draft OVMF package-set refactor.

Neither carries the default/v2/v3/max AAVMF boot matrix. This branch supplies evidence only and does not implement a competing OVMF packaging design.

## Exact identities

Firmware revisions:

```text
known good  d41f19d0a8017b17cc4d527938bcf94a3e0b0a81
known bad   45788a75f5dbf0f449f6168b2fd647d49135e841
current     396e6226eab2fd092b1690abcd33ea522fde16dc
```

QEMU and host tools use current pinned Nixpkgs:

```text
396e6226eab2fd092b1690abcd33ea522fde16dc
```

Host and guest:

```text
host derivation: x86_64-linux
guest artifacts: aarch64-linux
accelerator:     TCG
CPU model:       max
firmware files:  FV/AAVMF_CODE.fd and FV/AAVMF_VARS.fd
boot payload:    systemd-bootaa64.efi as EFI/BOOT/BOOTAA64.EFI
```

The script names each exact artifact directly. It does not search for the first `.fd` file and cannot silently fall back to host-architecture firmware.

## Matrix

For every firmware revision:

| Mode | QEMU machine argument |
|---|---|
| `default` | `-machine virt` |
| `2` | `-machine virt,gic-version=2` |
| `3` | `-machine virt,gic-version=3` |
| `max` | `-machine virt,gic-version=max` |

Everything else remains constant: QEMU revision, TCG, CPU, memory, pflash files, writable VARS copy, EFI filesystem, and boot payload.

## Process and cleanup contract

The Nix-built host script:

- refuses an existing case directory;
- validates all exact firmware, bootloader, and QEMU files;
- creates one unpredictable work directory below the case evidence directory;
- launches QEMU in a new process group;
- detects systemd-boot, early QEMU exit, or a bounded firmware timeout;
- terminates and reaps the full QEMU process group;
- removes only its exact validated work directory;
- retains command, QEMU version, store paths, outcome, and full QEMU log.

The Python runner adds a larger infrastructure timeout. An internal firmware timeout is an ordinary matrix result; a Python subprocess timeout invalidates the environment.

## Classification

### `all-gic-modes-reach-systemd-boot`

TCG does not reproduce the reported boundary. HVF or another host-specific layer remains required.

### `max-only-fails`

The reported boundary reproduces portably. Preserve the exact firmware/QEMU pair and begin an edk2/GIC bisect.

### `gicv3-and-max-fail`

The defect follows GICv3 rather than only QEMU's `max` selector.

### `default-mode-does-not-reach-systemd-boot`

The firmware fails more broadly in this environment. Inspect firmware revision, pflash layout, boot payload, and QEMU logs before attributing the result to GIC.

### `case-app-build-failed`

The x86_64 runner could not realize the pinned AArch64 artifacts or host script. This is retained as a capability result, not converted into firmware failure.

## Evidence controls

A valid environment requires:

- all three Nix case apps realized;
- all twelve QEMU cases completed without infrastructure timeout;
- known-good/default reached systemd-boot;
- complete exact-head GitHub provenance.

The reported boundary is a separate decision bit:

```text
tcg_reproduces_reported_boundary =
    valid environment
    and known-bad/default passes
    and known-bad/max fails
```

Thus a valid negative result remains green evidence.

## Reproduction

```sh
python3 -m unittest tests.test_aavmf_gic_smoke_matrix -v
python3 investigations/aavmf-gic-smoke-matrix/run_matrix.py \
  --results "$PWD/evidence/aavmf-manual"
```

Hosted CI is the supported path because it installs a pinned Nix implementation, retains build logs, and uploads all case records.

## Evidence boundary

This matrix does not exercise HVF, KVM, macOS, real AArch64 hardware, Secure Boot key enrollment, TPM, PV variable storage, or a guest kernel. It proves only whether AAVMF reaches an AArch64 systemd-boot binary under the exact TCG matrix.

The known-bad revision came from the upstream issue's manual firmware revision sampling, not a complete dependency bisect.

A TCG reproduction supports a firmware/GIC candidate; it does not establish which edk2 commit is responsible. A TCG non-reproduction makes HVF a named next boundary; it does not prove HVF is defective.

## Current disposition

`INVESTIGATE` until exact-head hosted execution completes.

Next decision:

- portable GIC reproduction → bisect firmware and compare PR #489505;
- valid TCG negative → retain an HVF capability gate and offer the matrix as regression design only after authorization;
- broad failure → repair the fixture or firmware identity before product claims;
- capability failure → identify a runner with cached/buildable AArch64 artifacts.

## Authority

Internal Linux Fieldwork work only. Public source and issue reading are authorized. No Nixpkgs, QEMU, edk2, or reporter contact is included or authorized.
