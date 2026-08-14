# Full X11 `vulkaninfo` discriminator — 2026-08-14

This checkpoint records a negative but useful environment discriminator for the FEX-2608 Vulkan thunk lifetime investigation.

## Question

Earlier hosted application reproductions were headless and printed `DISPLAY environment variable not set... skipping surface info`. The historical workstation failure involved Vulkan's X11 callback plumbing, so a plausible explanation was that hosted runs simply skipped the trigger.

## Controlled run

Owned-fork workflow run:

- `teamleaderleo/FEX` Actions run `31784273123`
- branch `ci/fex2608-nodelete-vulkaninfo-ab-clean-20260814`
- exact FEX-2608 base `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- Fedora 44 x86-64 guest userspace
- host Ubuntu Mesa/lavapipe
- Xvfb display reachable as `127.0.0.1:99`
- full `/usr/bin/vulkaninfo`, not `--summary`
- historical `vkCreateDebugReportCallbackEXT` custom-routing diagnostic
- normal unloadable Vulkan guest wrapper versus otherwise-identical Vulkan-only `DF_1_NODELETE` wrapper

The native control and both FEX arms verified the X11 WSI path rather than silently falling back to headless behavior. Receipts include:

- `VK_KHR_xlib_surface`
- `Presentable Surfaces`
- XCB/Xlib presentation support
- FEX log line `Opening host-side X11 display`
- no `DISPLAY ... not set` skip

## Result

```text
normal=0
nodelete=0
```

Both the ordinary unloadable wrapper and the Vulkan-only `NODELETE` wrapper completed full X11-backed `vulkaninfo` successfully.

## Interpretation

This rules out the simple explanation that the historical teardown crash occurs merely because X11 WSI/presentation code is exercised while the hosted tests were headless. Combined with earlier exact-FEX-2608 Fedora and Mesa-version controls, the missing historical trigger is now more likely to involve a narrower timing/concurrency/lifetime window, another loader/layer interaction, or a workstation/VM condition not reproduced by the hosted run.

This result does **not** weaken the executable lifetime evidence:

- ordinary `dlclose` under FEX is independently proven to remove the guest Vulkan wrapper mappings;
- wrapper retention/self-pin/NODELETE independently prevents those mappings from disappearing;
- a deterministic select→retire→unmap race independently proves registry cleanup and cache invalidation are insufficient once another thread already holds an executable target;
- same-address reload independently demonstrates an ABA problem for raw callback addresses.

For that reason, further work should prioritize deterministic execution-lifetime fixtures and the resident-bridge / generation-aware descriptor designs over broad package-version guessing.
