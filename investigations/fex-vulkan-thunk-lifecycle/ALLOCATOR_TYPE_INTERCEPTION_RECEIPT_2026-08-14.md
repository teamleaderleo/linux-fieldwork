# Vulkan allocator type-level interception receipt — 2026-08-14

Status: **runtime demonstrated** for the representative generic `vkCreateBuffer` path on x86-64 guest / ARM64 host.

Reviewed FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Question

Can FEX stop raw guest `VkAllocationCallbacks` function pointers from reaching native Vulkan through the large generic command surface **without** adding a custom wrapper for every allocator-taking command?

## Experimental policy

The owned-fork experiment changed `VkAllocationCallbacks` from an opaque pass-through type to a normally repacked type:

```cpp
template<>
struct fex_gen_type<VkAllocationCallbacks> {};
```

All six pointer-bearing members were marked `custom_repack`:

```text
pUserData
pfnAllocation
pfnReallocation
pfnFree
pfnInternalAllocation
pfnInternalFree
```

`pUserData` preserved the guest pointer value. Each non-NULL callback member was replaced with a host-callable diagnostic stub. A NULL guest callback remained NULL.

This was deliberately a **safety/interception** experiment, not a fidelity implementation. The diagnostic stub prints which callback native Vulkan attempted to invoke and aborts.

## Generator discriminators

Before the runtime test, two synthetic ThunkGen controls established that the existing generator can repack this kind of type without a generic generator relaxation:

1. one function-pointer struct member marked `custom_repack` — pass on x86-32 and x86-64;
2. one `void*` user-data member plus five callback members, all six custom-repacked — pass on x86-32 and x86-64.

The real Vulkan experiment initially used `emit_layout_wrappers` and was rejected as an unsupported parameter. Source tracing showed that `emit_layout_wrappers` deliberately assigns `TypeCompatibility::None`; it means “emit definitions despite incompatibility,” not “perform normal custom repacking.”

Using a plain registered `VkAllocationCallbacks` type plus six custom members allowed normal compatibility analysis and host-thunk generation. A subsequent one-line qualifier correction was needed to assign the const guest view of `pUserData` to Vulkan's mutable `void* pUserData` field.

## Runtime receipt

Owned fork:

```text
repository: teamleaderleo/FEX
branch: linux-fieldwork/vulkan-procaddr-native-first-experiment
workflow: Vulkan allocator type-level stub experiment
run: 31781850508
job: 94709116994
carrier head: b44edd1b64db39f4baa2a3243ee87d27ce6efb84
product source: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9212094555
artifact name: allocator-type-stub-31781850508
artifact SHA-256: 571fd463407ec8e7333eb30a2a936c324e5440111ad0526583306b71a0147a0c
```

Native ARM64 control:

```text
MARK instance result=0 ...
MARK device result=0 ...
MARK create-buffer-enter guest_alloc=...
MARK create-buffer-return result=0 ... alloc=1 realloc=0 free=0
MARK destroy-buffer-enter
MARK destroy-buffer-return alloc=1 realloc=0 free=1
PASS allocator callbacks observed
```

FEX x86-64 guest:

```text
MARK instance result=0 ...
MARK device result=0 ...
MARK create-buffer-enter guest_alloc=...
FEX_ALLOCATOR_STUB callback=pfnAllocation
timeout: the monitored command dumped core
```

Final matrix:

```text
native=0
fex=134
```

The FEX exit 134 is the deliberate host-side abort from the diagnostic stub. It replaces the previous raw cross-ISA callback escape / illegal-instruction failure.

## Conclusion

**Proven:** one `VkAllocationCallbacks` type-level repacking policy intercepts the generic Vulkan allocator path. `vkCreateBuffer` did not need to become `custom_host_impl`.

This is the important scaling result. The source audit counted 125 generic allocator-taking commands. The experiment does not claim all 125 were executed, but it demonstrates that their shared generic argument-repacking path can be governed by the allocator type rather than by per-command wrappers.

The next fidelity discriminator replaces the host diagnostic stubs with FEX's existing cached host-to-guest callback trampolines. That experiment also registers `VkSystemAllocationScope` and `VkInternalAllocationType`, because those enum arguments appear only inside the allocator callback signatures and therefore need explicit guest-layout generation for host callback packing.

## Boundaries

This type-level policy does **not** automatically fix the eight current custom allocator wrappers that explicitly discard the allocator and pass `nullptr` to native Vulkan. Those wrappers must separately stop suppressing the parameter if full allocator fidelity is selected.

The first custom-wrapper fidelity target is `vkCreateInstance`, because the existing create/destroy asymmetry is already runtime-demonstrated and `vkDestroyInstance` is generic. A type-level allocator policy should mediate the generic destroy path—including a destroy function obtained through GIPA—without making destroy custom.

## Reopen conditions

Reopen the type-level conclusion if a generic allocator-taking command is found that bypasses the normal generated argument repacker, or if a callback-member signature cannot be represented by the existing host-to-guest callback machinery. The safety interception result itself remains valid for the retained `vkCreateBuffer` receipt above.
