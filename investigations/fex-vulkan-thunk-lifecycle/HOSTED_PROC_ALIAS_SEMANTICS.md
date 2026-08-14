# Hosted native-vs-FEX Vulkan proc alias semantics

## Purpose

Check whether the clean Vulkan proc-routing candidate preserves native loader availability semantics across global, instance, and real-device queries, including promoted core commands and their KHR aliases.

The test deliberately uses native ARM64 Vulkan as the oracle rather than hardcoding expected null/non-null behavior. The exact same C probe source is compiled once for ARM64 and once for x86-64; the x86 binary is then run through FEX against the same Lavapipe driver.

## Exact receipt

```text
repository: teamleaderleo/FEX
exact product candidate: c011366706eaf65a00380003989b3a10811212b6
Actions run: 31784780121
job: 94718161765
workflow commit: 441c799bcdc9ece6742d911a6be931bdd85f32d4
artifact: 9213192790
artifact SHA-256: 5ea214733053fb8c70d5e231bbf8d7485f33e33672b5d4595a98c7a568c04b60
runner: ubuntu-24.04-arm
host Vulkan: Mesa Lavapipe
```

Both native and FEX probes report:

```text
SUPPORTED_API=1.3.275
REQUESTED_API=1.3.275
```

FEX probe process exit:

```text
0
```

## Result

```text
NATIVE_FEX_MISMATCH=0
```

The complete normalized native and FEX tables are byte-identical.

The matrix covers:

### `vkGetInstanceProcAddr(NULL, ...)`

- loader/global commands such as `vkCreateInstance`, enumeration functions, and GIPA itself
- invalid NULL-scope instance/device commands
- core/KHR promoted pairs such as physical-device-properties2 and physical-device-groups
- debug report / debug utils callback creators

### `vkGetInstanceProcAddr(instance, ...)`

- instance commands
- device commands returned through GIPA
- core/KHR promoted pairs:
  - `vkGetPhysicalDeviceProperties2` / `KHR`
  - `vkGetPhysicalDeviceFeatures2` / `KHR`
  - `vkGetPhysicalDeviceMemoryProperties2` / `KHR`
  - `vkGetPhysicalDeviceQueueFamilyProperties2` / `KHR`
  - `vkEnumeratePhysicalDeviceGroups` / `KHR`
  - `vkGetPhysicalDeviceExternalBufferProperties` / `KHR`
- debug callback creators with their extensions not enabled

### `vkGetDeviceProcAddr(device, ...)`

- GDPA self-query
- normal device commands
- core/KHR promoted pairs:
  - `vkBindBufferMemory2` / `KHR`
  - `vkGetBufferMemoryRequirements2` / `KHR`
  - `vkGetImageMemoryRequirements2` / `KHR`
  - `vkCreateDescriptorUpdateTemplate` / `KHR`
  - `vkTrimCommandPool` / `KHR`
  - `vkCmdDispatchBase` / `KHR`
- invalid instance/physical-device commands queried through GDPA

## Representative behavior

On this Vulkan 1.3 instance/device with no KHR extension enablement, native Lavapipe exposes promoted core names and leaves the tested KHR aliases null. FEX matches that behavior exactly.

Examples:

```text
GIPA_INSTANCE|vkGetPhysicalDeviceProperties2|1
GIPA_INSTANCE|vkGetPhysicalDeviceProperties2KHR|0

GDPA_DEVICE|vkBindBufferMemory2|1
GDPA_DEVICE|vkBindBufferMemory2KHR|0

GDPA_DEVICE|vkDestroyInstance|0
GDPA_DEVICE|vkGetPhysicalDeviceProperties2|0
```

The NULL-instance scope also matches exactly, including:

```text
GIPA_NULL|vkGetInstanceProcAddr|1
GIPA_NULL|vkGetDeviceProcAddr|0
GIPA_NULL|vkCreateShaderModule|0
GIPA_NULL|vkCreateDebugReportCallbackEXT|0
GIPA_NULL|vkCreateDebugUtilsMessengerEXT|0
```

## Interpretation

The final proc-routing candidate preserves native Vulkan availability semantics for the tested promoted/alias families and scopes. This adds confidence that the native-first availability gate is doing what it was intended to do rather than merely fixing the original callback crash.

This is coverage, not a proof over the entire Vulkan command registry. A future Vulkan-XML-driven corpus can broaden the same native-vs-FEX method mechanically without changing the oracle model.

## Next open seam

The strongest nearby source-maintenance seam that remains comparatively underexplored is 32-bit `pNext` custom repacking. FEX carries a large manually maintained `custom_repack` inventory for 32-bit Vulkan structures; a mechanical inventory/completeness audit should precede any runtime bug claim.