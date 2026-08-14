# Real `vulkaninfo` combined-repair result — 2026-08-14

## Result

The historical application-level teardown gate is now green under the combined diagnostic repair on exact FEX-2608.

Tested FEX source:

```text
e869aa644a16e4332cdc15c1ea0b4d13d482385d  (FEX-2608)
```

Fieldwork carrier branch/head:

```text
probe/fex-vulkan-combined-repair
d5061ee75d9d7501826ee8ec77dded5c586ea08a
```

GitHub Actions run:

```text
31776746325
```

Evidence artifact:

```text
combined-vulkan-evidence-31776746325
artifact id: 9210319366
sha256: c4acc589b79380aef963b9881f8abce7a5552e3f6737405794ffd730db839558
```

## What was actually executed

The application gate uses Ubuntu 24.04's amd64 `vulkan-tools` package and its real `/usr/bin/vulkaninfo` binary. The amd64 rootfs is built without executing amd64 Docker binaries on the ARM runner: the Ubuntu image is exported while stopped, an isolated host-side apt state downloads the amd64 package closure, and `dpkg-deb -x` extracts it into the FEX rootfs.

The distro Vulkan loader in that rootfs is replaced only at the guest `libvulkan.so.1` path by the rebuilt FEX guest Vulkan thunk. FEX then runs:

```text
/usr/bin/vulkaninfo --summary
```

against the host lavapipe ICD. No external `dlclose`-suppression preload is used.

The combined diagnostic candidate contains the two already-isolated repair components:

1. explicit custom routing for both `vkCreateDebugReportCallbackEXT` and `vkDestroyDebugReportCallbackEXT`;
2. process-lifetime retention of the FEX guest Vulkan wrapper after it has been loaded.

The real Vulkan guest `OnInit()` is restored before the combined/application gate, so its ordinary X11 helper registration path is present rather than disabled for isolation.

## Exact application receipt

Two independent fresh FEX processes were run.

```text
attempt-1=0
attempt-2=0
```

Both application logs contain a real Vulkan summary, including:

```text
Vulkan Instance Version: 1.3.275
Devices:
    deviceName         = llvmpipe (LLVM 20.1.2, 128 bits)
    driverName         = llvmpipe
```

Therefore the result is not merely “process did not crash before printing anything”: the real application reached Vulkan enumeration and then completed teardown with exit status 0 twice.

## Focused lifetime differential in the same run

Before the application gate, the same job preserves the isolated guest-wrapper lifetime differential:

```text
baseline=20
candidate=0
```

Baseline loses the final guest-wrapper mapping after the application's close. The candidate retains the wrapper and completes the saved-PFN/reopen checks.

The combined synthetic Vulkan gate also exits 0 and exercises instance creation, dynamic debug-report create/destroy, instance destruction, application close, retained wrapper mapping, and a post-close version call.

## Correction to the preceding red application run

The preceding application attempt (`31774750169`) was a harness failure and supplied no `vulkaninfo` product evidence.

It tried to start an amd64 Ubuntu container directly on an ARM64 Actions runner in order to install `vulkan-tools`. Docker reached the guest `/usr/bin/bash` and failed with:

```text
exec /usr/bin/bash: exec format error
```

The focused combined Vulkan gate had already passed in that job. The corrected carrier avoids executing any amd64 binary during rootfs construction and is the first hosted application-level result from this branch.

## What this establishes

This closes the immediate application-level gate for the **combined** repair family:

- the routing change removes the earlier callback lookup failure;
- keeping the guest Vulkan wrapper executable for process lifetime removes the historical llvmpipe teardown crash in this carrier;
- the result repeats in a second fresh FEX process;
- no preload pin workaround is involved.

Together with the historical controls (no-op guest `dlclose` -> exit 0, bogus preload -> exit 139, pin only guest Vulkan -> exit 0), this is strong evidence that guest-wrapper executable lifetime is causal for the observed teardown failure.

## What this does not establish

This result does **not** directly capture the final historical stale bridge dispatch or prove that a particular CustomIR row is the sole immediate caller at the old crash RIP.

It also does not prove that process-lifetime retention is the only acceptable generic design. If FEX requires true guest-wrapper unload/reload semantics, owner generations, revocation/rebinding, code-cache retirement, and transition quiescence remain relevant.

A separate real normal-vs-`DF_1_NODELETE` wrapper A/B is being used to decide whether ELF loader-enforced `NODELETE` is a cleaner narrow implementation of the process-lifetime policy than the constructor self-`dlopen` experiment.

Finally, retaining an FEX-owned guest thunk does not solve the generic case where a host trampoline retains an arbitrary `GuestTarget` located in an unrelated guest DSO that later unloads. That remains a separate callback-target lifetime problem.