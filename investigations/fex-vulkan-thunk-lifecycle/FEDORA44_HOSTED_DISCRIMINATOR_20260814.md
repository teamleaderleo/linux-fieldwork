# Fedora 44 hosted discriminator — 2026-08-14

The clean exact-FEX-2608 Ubuntu 24.04 guest application A/B completed with:

```text
normal=0
nodelete=0
```

That removes FEX source drift as an explanation for the hosted non-reproduction, but the historical target-executed crash used Fedora 44 x86-64 `vulkaninfo` rather than Ubuntu 24.04.

A new owned-fork workflow therefore keeps the FEX runtime fixed at exact FEX-2608 while changing the guest userspace to Fedora 44:

- branch: `ci/fex2608-nodelete-vulkaninfo-ab-clean-20260814`
- carrier commit: `88c5e44ae77664c61647ba3ec2f1d2ffcc45b584`
- workflow: `.github/workflows/fex2608-fedora44-vulkaninfo-ab.yml`

The workflow verifies committed product source against `e869aa644a16e4332cdc15c1ea0b4d13d482385d` before building.

It exports an amd64 Fedora 44 base image without running it. The ARM runner's native DNF is then used only as a package solver/installer with an x86-64 installroot (`--forcearch=x86_64`). No Fedora x86-64 executable is run while the rootfs is prepared. FEX is the only x86-64 execution engine used by the actual application test.

The same runtime-only historical `vkCreateDebugReportCallbackEXT` routing diagnostic is applied in both arms. The same FEX-2608 guest Vulkan source is built twice: normal and Vulkan-only `DF_1_NODELETE`.

Interpretation matrix:

- `normal=139`, `nodelete=0`: strong localization of the historical trigger to Fedora guest loader/tool/userspace behavior, with host llvmpipe held constant;
- `normal=0`, `nodelete=0`: Fedora guest package identity alone is insufficient; next split is host Mesa/Vulkan loader version, VM/runtime timing, or another workstation-only environment feature;
- failure before application execution: classify as carrier/rootfs machinery and repair without changing either application arm.
