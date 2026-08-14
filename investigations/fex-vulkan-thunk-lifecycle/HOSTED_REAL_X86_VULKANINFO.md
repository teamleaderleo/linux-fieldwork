# Real distro x86 `vulkaninfo` on hosted ARM64

## Purpose

Canonical receipt for the hosted ARM64 integration environment that runs an ordinary Ubuntu amd64 Vulkan application through FEX against native ARM64 Lavapipe.

This is useful beyond Finding A: it is a reusable public-runner environment for FEX Vulkan investigation without relying on private rootfs mounts or Apple M5 hardware for routine reproduction.

## Exact receipt

```text
repository: teamleaderleo/FEX
exact product candidate: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31779915833
job: 94703221566
artifact: 9211419091
artifact SHA-256: e361ad5f0a8e6312e908a7d2fea2ce908e411e3463450ddb8c786e5368660d2b
runner: ubuntu-24.04-arm
```

## Guest userspace construction

Guest userspace is Ubuntu 24.04 amd64.

The hosted ARM runner does not execute amd64 package maintainer scripts while constructing the rootfs:

1. foreign `debootstrap` resolves/downloads the amd64 package closure and extracts its base set;
2. the ARM host parses debootstrap's extraction receipt;
3. only package payloads debootstrap deferred are added with host-side `dpkg-deb -x`;
4. generated FEX `libvulkan-guest.so` replaces guest `libvulkan.so.1`;
5. real distro x86 `libX11.so.6` supplies the guest thunk constructor helpers (`XSync`, `XGetVisualInfo`, `XDisplayString`).

This avoids private `/mnt/AutoNFS` roots, QEMU guest execution, and the earlier diagnostic X11 stub library.

## Host Vulkan

Native ARM64 control uses Mesa Lavapipe via the runner's `lvp_icd.json`. Native `vulkaninfo --summary` passes before FEX execution.

## FEX results

```text
FEX /bin/true: exit 0
FEX /usr/bin/vulkaninfo --summary: exit 0
```

Guest `vulkaninfo` reports:

```text
Vulkan Instance Version: 1.3.275
deviceName = llvmpipe (LLVM 20.1.2, 128 bits)
driverName = llvmpipe
driverInfo = Mesa 25.2.8-0ubuntu0.24.04.2 (LLVM 20.1.2)
```

The process exits cleanly after enumeration.

## Interpretation

Hosted ARM64 is now a practical FEX Vulkan execution environment, not merely a build runner or tiny callback-probe environment.

The clean process exit also narrows Finding B: successful ordinary `vulkaninfo` enumeration does not inherently reproduce the teardown failure. The stronger forced-different-remap / stale dynamic-PFN lifetime work remains the meaningful Finding B discriminator.

## Reuse

Future hosted lanes should prefer this package-resolved rootfs pattern when they need a real amd64 distro Vulkan program or real x86 runtime libraries. Keep product SHA receipts exact and continue separating functional success from teardown success.