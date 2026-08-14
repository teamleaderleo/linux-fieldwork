# Vulkan allocation-callback surface audit — 2026-08-14

Status: source-level scope audit plus retained ARM64 runtime evidence for raw allocator escape, create/destroy asymmetry, the safety/fidelity tradeoff of consistent NULL suppression, and dynamic proc-address bypass of a newly custom safe wrapper.

FEX product revision reviewed: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Pinned Vulkan-Headers submodule: `450bd2232225d6c7728a4108055ac2e37cef6475` (`VK_HEADER_VERSION 337`).

## Root design fact

`ThunkLibs/libvulkan/libvulkan_interface.cpp` declares `VkAllocationCallbacks` opaque and carries the explicit TODO that supporting its contained function pointers needs more work.

That is important because `VkAllocationCallbacks` contains application function pointers, while many Vulkan commands accept `const VkAllocationCallbacks* pAllocator`.

The current Vulkan thunk surface does not apply one uniform policy to those parameters.

## Exact allocator surface inventory

A machine audit now replaces the earlier examples-only scope estimate.

Owned Fieldwork audit:

```text
script: investigations/fex-vulkan-thunk-lifecycle/audit_vulkan_allocator_surface.py
workflow: Vulkan allocator surface audit
run: 31778164510
job: 94697913017
product: 71afe476751deac24adabd1adb575fd2337b6e0a
Vulkan-Headers: 450bd2232225d6c7728a4108055ac2e37cef6475
```

The pinned Vulkan headers contain **133 distinct commands** whose prototypes accept `VkAllocationCallbacks`.

For both FEX ABI configurations inspected by the interface metadata:

```text
allocator-taking commands: 133
custom_host_impl allocator commands: 8
generic allocator commands: 125
paired custom/generic asymmetries: 4
```

The exact eight custom allocator-taking commands are:

- `vkAllocateMemory`
- `vkCreateDebugReportCallbackEXT`
- `vkCreateDebugUtilsMessengerEXT`
- `vkCreateDevice`
- `vkCreateInstance`
- `vkCreateShaderModule`
- `vkDestroyDebugReportCallbackEXT`
- `vkFreeMemory`

The exact four create/destroy policy asymmetries are:

- `vkCreateInstance` = custom; `vkDestroyInstance` = generic
- `vkCreateDevice` = custom; `vkDestroyDevice` = generic
- `vkCreateShaderModule` = custom; `vkDestroyShaderModule` = generic
- `vkCreateDebugUtilsMessengerEXT` = custom; `vkDestroyDebugUtilsMessengerEXT` = generic

This is a broad API-policy problem rather than a short list of isolated Vulkan functions.

## Class 1 — custom wrappers that neutralize the allocator

At the reviewed revision, `ThunkLibs/libvulkan/Host.cpp` explicitly forwards `nullptr` instead of the guest allocator for at least the eight custom commands above where an allocator is present.

For these calls, guest allocator callbacks do not cross directly to the native Vulkan implementation.

## Class 2 — ordinary generated commands that accept allocators

The remaining **125** allocator-taking commands are generic at the reviewed interface revision. Representative core pairs include:

- `vkCreateFence` / `vkDestroyFence`
- `vkCreateSemaphore` / `vkDestroySemaphore`
- `vkCreateQueryPool` / `vkDestroyQueryPool`
- `vkCreateBuffer` / `vkDestroyBuffer`
- `vkCreateImage` / `vkDestroyImage`
- `vkCreateImageView` / `vkDestroyImageView`
- `vkCreateCommandPool` / `vkDestroyCommandPool`
- `vkCreatePipelineCache` / `vkDestroyPipelineCache`
- `vkCreatePipelineLayout` / `vkDestroyPipelineLayout`
- `vkCreateSampler` / `vkDestroySampler`
- `vkCreateDescriptorPool` / `vkDestroyDescriptorPool`
- `vkCreateFramebuffer` / `vkDestroyFramebuffer`
- `vkCreateRenderPass` / `vkDestroyRenderPass`

The retained ARM64 `vkCreateBuffer` experiment demonstrates the consequence on one representative generic command: NULL allocator returns normally, while a valid guest allocator reaches the native side and faults before `vkCreateBuffer` returns.

That runtime result should be generalized only to commands whose source path is shown to raw-forward the allocator; the exact 125 count is a metadata classification, not a claim that every command has separately been executed.

## Class 3 — create/destroy policy asymmetry

Some object creators are custom and force the host allocator to NULL, while their corresponding destroy commands remain generic. This can transform a Vulkan-valid guest create/destroy pair into a mismatched host pair.

The instance pair is the clearest form:

```text
guest vkCreateInstance(..., &A, ...)
    -> FEX custom wrapper
    -> host vkCreateInstance(..., NULL, ...)

guest vkDestroyInstance(..., &A)
    -> generic thunk
    -> host receives guest-layout/raw allocator A
```

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

This promotes the instance create/destroy asymmetry from source-level concern to a direct runtime correctness failure.

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

Native control remained Vulkan-valid and used the supplied allocator. Under FEX with consistent NULL suppression on create and destroy:

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

This separates two properties:

- **Safety:** consistent NULL suppression prevents the raw guest allocator callback escape for this pair and lets destroy return.
- **Fidelity:** the application-supplied allocator is silently ignored, so the Vulkan-valid guest behavior is not preserved.

Therefore consistent suppression is a demonstrated safety mechanism, not a complete allocator implementation.

## Dynamic GIPA discriminator — direct safety is not enough

A follow-up probe asked a more important routing question: after making `vkDestroyInstance` custom and safe for the direct thunk, what happens if the guest obtains `vkDestroyInstance` through `vkGetInstanceProcAddr`?

Receipt:

```text
workflow: Vulkan instance allocator suppression experiment
run: 31778088761
job: 94697682394
carrier: bbce1e8c1ea9869ef3ddab3e6236dffe060523c1
product: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9210726208
artifact SHA-256: 786da5be1a8675109ff3d86b2e1d527006748c1b61a840cc85ca2b2146546366
```

Exact matrix:

```text
native=0
native_dynamic=0
fex_direct=10
fex_dynamic=132
```

Native direct and GIPA destroy both honored the allocator and returned normally.

FEX direct used the new custom wrapper, returned normally, and then deliberately failed the probe because allocator callbacks remained at zero:

```text
MARK create-return result=0 ... alloc=0 realloc=0 free=0
MARK destroy-enter
MARK destroy-return alloc=0 realloc=0 free=0 free_delta=0
FAIL allocator callbacks not observed
```

FEX dynamic lookup instead returned a guest-callable pointer linked to the native route and crashed as soon as it was called with the guest allocator:

```text
MARK create-return result=0 ... alloc=0 realloc=0 free=0
Linking address 0x7ffff76c7d80 to host invoker 0x7ffff7ea2420
MARK gipa-destroy ptr=0x7ffff76c7d80
MARK destroy-enter
timeout: the monitored command dumped core
```

The shell reported an illegal instruction and exit 132.

This is a concrete successor-function reproduction of the original registration-drift class:

> Marking a function `custom_host_impl` and implementing a correct/safe direct wrapper does not make the dynamic PFN path correct if the handwritten custom lookup inventory is not updated at the same time.

A metadata-generated custom registry would acquire `vkDestroyInstance` automatically when it became `custom_host_impl`. A handwritten registry requires another name entry and can immediately re-open the cross-ISA callback escape.

## Implication for candidate design

A narrow fix for `vkCreateBuffer` is insufficient. Vulkan thunking needs an explicit allocator policy:

1. implement callback mediation for `VkAllocationCallbacks`; or
2. deliberately suppress allocators consistently across every affected create/destroy/free pair where that policy is permitted by the project; or
3. reject/diagnose unsupported non-NULL allocators before a raw cross-ISA callback can occur.

Mixing silent NULL substitution on one side with generic raw forwarding on the other is the worst state because it both violates the guest application's allocator pairing and exposes guest function pointers to native code.

The suppression discriminator narrows the policy discussion: option 2 can remove the demonstrated crash for the instance pair, but it intentionally does not honor guest allocator semantics. The GIPA discriminator adds another non-negotiable condition: any command made custom for allocator safety must also be dynamically routed through that wrapper whenever native proc-address lookup exposes the command.

## Evidence boundary

Demonstrated at runtime:

- representative generic `vkCreateBuffer` allocator escape on ARM64;
- a native-valid `vkCreateInstance` / `vkDestroyInstance` pair whose create side is silently changed to NULL by FEX and whose generic destroy side faults when the original guest allocator is forwarded;
- an owned-fork `vkDestroyInstance` NULL-suppression candidate that removes the direct-path crash and returns from destroy, while the probe proves zero guest allocator callbacks were honored;
- the same newly custom `vkDestroyInstance` obtained through GIPA bypasses the safe direct wrapper and reproduces SIGILL/132 when handwritten dynamic registration is omitted.

Source/machine-proven: opaque callback type, 133 allocator-taking Vulkan commands, 8 current custom allocator commands, 125 current generic allocator commands, and exactly four custom/generic create/destroy asymmetries.

Still open: whether the strongest project-compatible policy is full callback mediation, consistent suppression, or explicit rejection; and whether FEX has an existing callback policy in other thunk libraries that should guide Vulkan rather than inventing a one-off convention.
