# Fedora 44 hosted result — 2026-08-14

## Result

The clean Fedora 44 guest discriminator completed successfully on exact FEX-2608.

Owned-fork run:

`31780850819`

The workflow verifies committed FEX product source against:

`e869aa644a16e4332cdc15c1ea0b4d13d482385d`

before applying the historical debug-report routing diagnostic and building the two guest Vulkan wrappers.

Guest package receipts:

```text
glibc.x86_64        2.43-8.fc44
libX11.x86_64       1.8.13-1.fc44
vulkan-tools.x86_64 1.4.341.0-1.fc44
```

The guest application is a real Fedora 44 x86-64 `vulkaninfo`. Both arms run through FEX against the same Ubuntu-host llvmpipe Mesa 25.2.8 stack and exit cleanly:

```text
normal=0
nodelete=0
```

Both enumerate llvmpipe successfully. The reported Vulkan Instance Version is 1.3.275 because the native host Vulkan loader/ICD side remains the Ubuntu-host stack.

## Interpretation

Fedora 44 guest userspace by itself is **not** sufficient to recreate the historical teardown crash.

We have now held the following constant or reproduced closely in the hosted lane:

- exact FEX-2608 source;
- Fedora 44 x86-64 guest userspace;
- real distro `vulkaninfo`;
- the historical debug-report create routing diagnostic;
- real guest Vulkan wrapper behavior;
- llvmpipe rather than Venus.

The major remaining software-stack difference is the native host Vulkan/Mesa side. Historical evidence used Mesa 25.3.6 in the Fedora 44 ARM VM; the hosted runner uses Mesa 25.2.8 from Ubuntu 24.04.

Therefore the next high-value application discriminator is:

> keep exact FEX-2608 and the Fedora 44 x86-64 guest fixed, but run the native host Vulkan side against Mesa 25.3.6 llvmpipe.

If that recreates `normal=139` while `NODELETE=0`, the trigger localizes to a host loader/driver behavior change that alters the native PFN/teardown sequence or timing. If it remains `0/0`, the remaining major classes are the Lima/krunkit VM environment, host Vulkan-loader version/configuration, scheduling/timing, or another workstation-only environmental difference.

## Important non-result

This `0/0` result does not weaken the direct lifetime evidence:

- the historical Fedora workstation run changes 139→0 when only the guest Vulkan wrapper is pinned;
- the focused FEX residency probe proves ordinary `dlclose` removes exactly the guest Vulkan mappings and `DF_1_NODELETE` preserves them;
- the deterministic in-flight test proves deregistration + cache invalidation can still lose after a target has already been selected.

It only says the hosted Fedora application does not naturally enter the same bad teardown ordering under the current host environment.
