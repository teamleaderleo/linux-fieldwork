# Agent B callback-bearing pNext inventory follow-up

Date: 2026-08-14

This note extends the debug-report/debug-utils callback review beyond their ordinary create commands. FEX upstream stayed read-only. Source was checked at FEX `71afe476751deac24adabd1adb575fd2337b6e0a` (`https://redirect.github.com/FEX-Emu/FEX/commit/71afe476751deac24adabd1adb575fd2337b6e0a`).

## 1. `VK_LUNARG_direct_driver_loading`: deterministic instance-create callback

`VkDirectDriverLoadingInfoLUNARG` contains an application-supplied `pfnGetInstanceProcAddr`, and `VkDirectDriverLoadingListLUNARG` extends `VkInstanceCreateInfo`. The loader uses that function pointer to talk to an application-provided driver.

FEX's Vulkan interface has no function-pointer-aware type specialization for `VkDirectDriverLoadingInfoLUNARG`; its 32-bit custom pNext repack entries for both direct-driver-loading structures are commented out. The 64-bit custom `vkCreateInstance` has no callback handling for this pNext family.

A reduced native x86 probe supplied one exclusive direct driver whose `pfnGetInstanceProcAddr` only counted calls and returned NULL. The system Vulkan loader called it exactly once:

```text
GUEST_CALLBACK=<address>
MARK create-enter
CALLBACK direct-driver count=1 name=vk_icdNegotiateLoaderICDInterfaceVersion
MARK create-return result=-9 callbacks=1 instance=(nil)
PASS callbacks=1
```

This is a useful FEX discriminator because it needs no validation layer and no functioning ICD. A raw ARM call to the guest x86 `pfnGetInstanceProcAddr` would expose the same cross-ISA callback class directly inside `vkCreateInstance`.

Local source: `vk_direct_driver_loading_pnext_probe.c`; native source SHA-256 `f90def92b885ac4a965b98c409e6a4158096958cac32d0dad77971ae1ef1afa2`.

## 2. `VK_EXT_device_memory_report`: device-create callback surface

`VkDeviceDeviceMemoryReportCreateInfoEXT` contains `pfnUserCallback` and `pUserData` and extends device creation. FEX has no function-pointer-aware type specialization for this structure; its custom pNext repack entry is commented out. The 64-bit custom `vkCreateDevice` forwards the supplied `VkDeviceCreateInfo` while only suppressing allocation callbacks.

That makes device-memory-report another source-level callback surface requiring review. The local SwiftShader control did not advertise `VK_EXT_device_memory_report`, so this note does not claim a target runtime failure for it.

## 3. `VkAllocationCallbacks` remains a broader unsupported callback family

FEX explicitly declares `VkAllocationCallbacks` opaque with a source comment that supporting its contained function pointers requires more work. Several custom Vulkan wrappers force allocator arguments to NULL, but generic paths still need an inventory before non-NULL allocators can be considered safe.

## Priority

The direct-driver-loading probe is the next best runtime test after the repaired hosted ARM64 fixture because it gives one deterministic loader callback during `vkCreateInstance` without depending on debug callback registration, proc-address lookup, layers, or a usable driver. Device-memory-report and non-NULL allocation callbacks should remain source-level follow-ups until similarly narrow runtime controls exist.
