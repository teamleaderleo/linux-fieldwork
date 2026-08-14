# Hosted ARM64 direct-driver-loading pNext callback escape — 2026-08-14

Status: demonstrated runtime finding on exact reviewed FEX product source.

Product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX carrier commit: `f9ff66c7e314372b557278b06b83ba4355051cc9`.
Workflow run: `31769421527`.
Job: `94672035952`.
Runner: GitHub hosted `ubuntu-24.04-arm`.

The workflow verified that the carrier had no product-source delta under `ThunkLibs`, `FEXCore`, or `Source` relative to `71afe476751deac24adabd1adb575fd2337b6e0a` before building FEX.

## Probe contract

The probe exercises `VK_LUNARG_direct_driver_loading` through `VkInstanceCreateInfo::pNext`.

A `VkDirectDriverLoadingListLUNARG` contains one `VkDirectDriverLoadingInfoLUNARG` whose application-provided `pfnGetInstanceProcAddr` returns NULL. The callback entrypoint has the same x86/ARM64 instruction discriminator used by the other callback probes in this investigation: normal x86 execution reaches the callback body, while a raw ARM64 branch to the guest x86 address produces SIGILL before the body executes.

The callback requires no ordinary Vulkan ICD. Exclusive direct-driver mode causes the loader to query the supplied driver callback directly during `vkCreateInstance`.

## Native ARM64 control

Observed:

```text
GUEST_CALLBACK=<native-arm callback>
MARK create-enter
CALLBACK direct-driver count=1 name=vk_icdNegotiateLoaderICDInterfaceVersion
MARK create-return result=-9 callbacks=1 instance=(nil)
PASS callbacks=1 result=-9
```

Exit:

```text
native=0
```

The native loader therefore invokes the application callback exactly once and returns normally after the callback returns NULL.

## Exact FEX result

Observed:

```text
GUEST_CALLBACK=<guest-x86 callback>
MARK create-enter
```

There is no callback-body marker and no `MARK create-return`.

The process terminates:

```text
fex=132
Illegal instruction
```

## Interpretation

This demonstrates a cross-ISA function-pointer escape through a callback-bearing Vulkan `pNext` structure.

At the reviewed FEX source, the custom `vkCreateInstance` handling does not mediate `VkDirectDriverLoadingInfoLUNARG::pfnGetInstanceProcAddr`. The 64-bit structure layout is forwarded to the native loader with the guest callback pointer intact. The native ARM64 loader invokes that pointer during `vkCreateInstance`, entering guest x86 code as ARM64 and producing SIGILL before the guest callback body runs.

This path is independent of Finding A's dynamic `vkGetInstanceProcAddr` return-value routing defect:

- no `vkCreateDebugReportCallbackEXT` or `vkCreateDebugUtilsMessengerEXT` call is involved;
- the failure occurs inside `vkCreateInstance` through input `pNext` data;
- adding missing custom-function lookup entries cannot repair this callback-bearing structure.

It is also independent of the `VkAllocationCallbacks` findings: the probe passes a NULL Vulkan allocator.

## Scope implication

The result shows that callback safety cannot be achieved only by maintaining a list of customized Vulkan commands. Callback-bearing members nested in input structures and `pNext` chains need explicit cross-ISA handling as well.

The source inventory should continue to track at least:

- debug-report create-info callbacks;
- debug-utils messenger create-info callbacks;
- direct-driver-loading `pfnGetInstanceProcAddr`;
- device-memory-report callbacks;
- `VkAllocationCallbacks` function pointers.

Each family needs mediation, deliberate supported suppression, or explicit rejection before a guest function pointer can reach native code.

## Evidence boundary

Demonstrated here: pristine current reviewed FEX product source, native single-callback control, FEX SIGILL after `create-enter` and before callback body/create return.

Not demonstrated by this run: a repair candidate for direct-driver-loading or the behavior of every other callback-bearing `pNext` structure.
