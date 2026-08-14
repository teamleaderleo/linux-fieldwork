# Vulkan allocation-callback surface audit — 2026-08-14

Status: source-level scope audit plus retained ARM64 runtime evidence for raw allocator escape, create/destroy asymmetry, and the safety/fidelity tradeoff of consistent NULL suppression.

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

There is a more severe form than simple raw forwarding.

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

The same source form exists for at least:

- `vkCreateInstance` / `vkDestroyInstance`
- `vkCreateDevice` / `vkDestroyDevice`
- `vkCreateShaderModule` / `vkDestroyShaderModule`
- `vkCreateDebugUtilsMessengerEXT` / `vkDestroyDebugUtilsMessengerEXT`

This is distinct from a guest application incorrectly mixing allocators. The guest can use one allocator consistently at API boundaries; FEX itself changes only the create side to NULL.

### Retained instance create/destroy A/B

Owned ARM64 workflow:

```text
repository: teamleaderleo/FEX
workflow: Agent B ARM64 instance allocator lifetime probe
run: 31769093369
job: 94671054516
carrier SHA: 3d0b0f2103deff80d51f1cfa532aee994eca14a4
exact FEX product source: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9207521397
artifact SHA-256: db4666f72bd99b0f69bd8968e9a1adda5cad5d11ae7f08cccae1f1eed342895a
```

The same probe first ran natively on ARM64 with one valid `VkAllocationCallbacks` object supplied to both instance create and destroy. Native Vulkan returned success and invoked the allocator callbacks on both sides:

```text
MARK create-return result=0 ... alloc=165 realloc=4 free=141
MARK destroy-return alloc=165 realloc=4 free=161 free_delta=20
PASS allocator native-valid create/destroy callbacks observed
```

The x86-64 probe under exact FEX product source then used the same Vulkan-valid API pattern. FEX instance creation succeeded, but none of the guest allocator callbacks ran during create, matching the custom wrapper's NULL substitution:

```text
MARK create-return result=0 ... alloc=0 realloc=0 free=0
```

The subsequent guest call supplied the same allocator to `vkDestroyInstance`. The generic destroy path entered and the FEX process terminated before destroy returned:

```text
MARK destroy-enter
timeout: the monitored command dumped core
```

Final matrix:

```text
native=0
fex=132
```

This promotes the instance create/destroy asymmetry from source-level concern to a direct runtime correctness failure. It also demonstrates that simply making create safe by silently replacing a non-NULL allocator with NULL is not sufficient when the paired destroy path still accepts the original guest allocator.

## Consistent-suppression discriminator

A second owned-fork experiment tested the narrow safety question without claiming allocator fidelity.

Experimental delta against exact product source `71afe476751deac24adabd1adb575fd2337b6e0a`:

```cpp
static void FEXFN_IMPL(vkDestroyInstance)(VkInstance instance, const VkAllocationCallbacks* allocator) {
  (void)allocator;
  LDR_PTR(vkDestroyInstance)(instance, nullptr);
}
```

and `vkDestroyInstance` was marked `custom_host_impl`, so its direct thunk path used the wrapper. This mirrors the existing create-side NULL policy.

Receipt:

```text
workflow: Vulkan instance allocator suppression experiment
run: 31777657757
job: 94696390382
carrier: 1b2c3743ddbef00e93d25d09d298d2929c90289b
product: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9210569307
artifact SHA-256: c78babcca47967c00526d97a18c09aab6feff3f342adc538e1fbdb8b72a7f58f
```

Native control remained Vulkan-valid and used the supplied allocator:

```text
MARK create-return result=0 ... alloc=165 realloc=4 free=141
MARK destroy-return alloc=165 realloc=4 free=161 free_delta=20
PASS allocator native-valid create/destroy callbacks observed
```

Under FEX with consistent NULL suppression on create and destroy:

```text
MARK create-return result=0 ... alloc=0 realloc=0 free=0
MARK destroy-enter
MARK destroy-return alloc=0 realloc=0 free=0 free_delta=0
FAIL allocator callbacks not observed
```

Final matrix:

```text
native=0
fex=10
```

The FEX exit code 10 is the probe's deliberate semantic-fidelity failure after destroy returned normally. The previous SIGILL/132 is gone.

This cleanly separates two properties:

- **Safety:** consistent NULL suppression prevents the raw guest allocator callback escape for this pair and lets destroy return.
- **Fidelity:** the application-supplied allocator is silently ignored, so the Vulkan-valid guest behavior is not preserved.

Therefore consistent suppression is a demonstrated safety mechanism, not a complete allocator implementation.

There is also a routing consequence. Once a previously generic command such as `vkDestroyInstance` becomes `custom_host_impl`, dynamic proc-address lookup must select that custom wrapper whenever native Vulkan says the command is available. A generated custom-host registry would acquire that route automatically; a handwritten inventory requires an additional registration change and invariant coverage.

## Implication for candidate design

A narrow fix for `vkCreateBuffer` is insufficient. Vulkan thunking needs an explicit allocator policy:

1. implement callback mediation for `VkAllocationCallbacks`; or
2. deliberately suppress allocators consistently across every affected create/destroy/free pair where that policy is permitted by the project; or
3. reject/diagnose unsupported non-NULL allocators before a raw cross-ISA callback can occur.

Mixing silent NULL substitution on one side with generic raw forwarding on the other is the worst state because it both violates the guest application's allocator pairing and exposes guest function pointers to native code.

The suppression discriminator narrows the policy discussion: option 2 can remove the demonstrated crash for the instance pair, but it intentionally does not honor guest allocator semantics. A project decision is still required before treating that policy as a product fix.

## Evidence boundary

Demonstrated at runtime:

- representative generic `vkCreateBuffer` allocator escape on ARM64;
- a native-valid `vkCreateInstance` / `vkDestroyInstance` pair whose create side is silently changed to NULL by FEX and whose generic destroy side faults when the original guest allocator is forwarded;
- an owned-fork `vkDestroyInstance` NULL-suppression candidate that removes the crash and returns from destroy, while the probe proves zero guest allocator callbacks were honored.

Source-proven: opaque callback type, broad generic allocator surface, and the additional create/destroy asymmetries listed above.

Still open: whether the strongest project-compatible policy is full callback mediation, consistent suppression, or explicit rejection; whether dynamic `vkGetInstanceProcAddr(..., "vkDestroyInstance")` is covered by any future custom suppression candidate; and which additional representative pairs would distinguish those policies rather than merely repeat the same failure class.
