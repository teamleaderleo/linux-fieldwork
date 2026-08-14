# Vulkan allocation-callback surface audit — 2026-08-14

Status: source-level scope audit plus pointers to retained ARM64 runtime evidence.

FEX product revision reviewed: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Pinned Vulkan-Headers submodule: `450bd2232225d6c7728a4108055ac2e37cef6475` (`VK_HEADER_VERSION 337`).

## Root design fact

`ThunkLibs/libvulkan/libvulkan_interface.cpp` declares `VkAllocationCallbacks` opaque and carries the explicit TODO that supporting its contained function pointers needs more work.

That is important because `VkAllocationCallbacks` contains application function pointers, while many Vulkan commands accept `const VkAllocationCallbacks* pAllocator`.

The current 64-bit thunk surface does not apply one uniform policy to those parameters.

## Class 1 — custom wrappers that neutralize the allocator

At the reviewed revision, `ThunkLibs/libvulkan/Host.cpp` explicitly forwards `nullptr` instead of the guest allocator for at least:

- `vkCreateInstance`
- `vkCreateDevice`
- `vkCreateShaderModule`
- `vkAllocateMemory`
- `vkFreeMemory`
- `vkCreateDebugReportCallbackEXT`
- `vkDestroyDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`

For these calls, guest allocator callbacks do not cross directly to the native Vulkan implementation.

## Class 2 — ordinary generated commands that accept allocators

The pinned Vulkan headers show a broad core command family with `pAllocator`, including:

- `vkCreateFence` / `vkDestroyFence`
- `vkCreateSemaphore` / `vkDestroySemaphore`
- `vkCreateQueryPool` / `vkDestroyQueryPool`
- `vkCreateBuffer` / `vkDestroyBuffer`
- `vkCreateImage` / `vkDestroyImage`
- `vkCreateImageView` / `vkDestroyImageView`
- `vkCreateCommandPool` / `vkDestroyCommandPool`
- `vkCreateEvent` / `vkDestroyEvent`
- `vkCreateBufferView` / `vkDestroyBufferView`
- `vkCreatePipelineCache` / `vkDestroyPipelineCache`
- `vkCreateComputePipelines` / `vkDestroyPipeline`
- `vkCreateGraphicsPipelines` / `vkDestroyPipeline`
- `vkCreatePipelineLayout` / `vkDestroyPipelineLayout`
- `vkCreateSampler` / `vkDestroySampler`
- `vkCreateDescriptorSetLayout` / `vkDestroyDescriptorSetLayout`
- `vkCreateDescriptorPool` / `vkDestroyDescriptorPool`
- `vkCreateFramebuffer` / `vkDestroyFramebuffer`
- `vkCreateRenderPass` / `vkDestroyRenderPass`

The FEX interface marks many of these as ordinary generated commands rather than callback-aware custom implementations. The retained ARM64 `vkCreateBuffer` experiment demonstrates the consequence on one representative command: NULL allocator returns normally, while a valid guest allocator reaches the native side and faults before `vkCreateBuffer` returns.

That runtime result should be generalized only to commands whose source path is shown to raw-forward the allocator; the list above is a source audit, not a claim that every command has separately been executed.

## Class 3 — create/destroy policy asymmetry

There is a more severe shape than simple raw forwarding.

Some object creators are custom and force the host allocator to NULL, while their corresponding destroy commands remain generic. This can transform a Vulkan-valid guest create/destroy pair into a mismatched host pair.

Strong examples at the reviewed revision:

```text
guest vkCreateInstance(..., &A, ...)
    -> FEX custom wrapper
    -> host vkCreateInstance(..., NULL, ...)

guest vkDestroyInstance(..., &A)
    -> generic thunk
    -> host receives guest-layout/raw allocator A
```

The same source shape exists for at least:

- `vkCreateInstance` / `vkDestroyInstance`
- `vkCreateDevice` / `vkDestroyDevice`
- `vkCreateShaderModule` / `vkDestroyShaderModule`
- `vkCreateDebugUtilsMessengerEXT` / `vkDestroyDebugUtilsMessengerEXT`

This is distinct from a guest application incorrectly mixing allocators. The guest can use one allocator consistently at API boundaries; FEX itself changes only the create side to NULL.

An owned ARM64 workflow launched on 2026-08-14 tests the instance pair directly using a native-valid allocator probe. Its result should be retained separately once the run completes.

## Implication for candidate design

A narrow fix for `vkCreateBuffer` is insufficient. Vulkan thunking needs an explicit allocator policy:

1. implement callback mediation for `VkAllocationCallbacks`; or
2. deliberately suppress allocators consistently across every affected create/destroy/free pair where that policy is permitted by the project; or
3. reject/diagnose unsupported non-NULL allocators before a raw cross-ISA callback can occur.

Mixing silent NULL substitution on one side with generic raw forwarding on the other is the worst state because it both violates the guest application's allocator pairing and exposes guest function pointers to native code.

## Evidence boundary

Demonstrated at runtime so far: representative generic `vkCreateBuffer` allocator escape on ARM64.

Source-proven: opaque callback type, broad generic allocator surface, and the create/destroy asymmetries listed above.

Pending runtime promotion: valid instance create/destroy allocator pair and additional representative pairs if needed.
