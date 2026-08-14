# Vulkan allocator destroy repack identity receipt — 2026-08-14

## Scope

Carrier: `teamleaderleo/FEX` branch `ci/vulkan-allocator-repack-identity-20260814`, head `b5a31c1b9784ab45fea7d9037ab802509cc43811`.

Exact FEX product under test: `71afe476751deac24adabd1adb575fd2337b6e0a`.

GitHub Actions run: `31784948644` (`Vulkan allocator repack identity ARM64`). The workflow itself completed successfully because it was a diagnostic collector; the guest execution returned `139`.

## Result

The allocator callback mediation path correctly repacks the application allocator on `vkCreateBuffer`, and native Vulkan successfully calls the guest allocation callback through the generated host trampoline.

Observed create-side repack:

```
API_CREATE_ENTER a=0x561ffbfe67dc b=0x561ffbfe67fe c=0x561ffbfe9024
ALLOC_REPACK_BEGIN seq=1 guest_user=0x561ffbfe9024 host_user=0x561ffbfe9024 guest_alloc=0x561ffbfe67dc guest_realloc=0x561ffbfe67ed guest_free=0x561ffbfe67fe guest_internal_alloc=(nil) guest_internal_free=(nil)
ALLOC_REPACK_END seq=1 host_user=0x561ffbfe9024 host_alloc=0x7ffff7e3e090 host_realloc=0x7ffff7e3e0c0 host_free=0x7ffff7e3e0f0 host_internal_alloc=(nil) host_internal_free=(nil)
CB_ALLOC_ENTER a=0x561ffbfe9024 b=0x90 c=0x8
CB_ALLOC_RETURN a=0x561ffc00c218 b=0x561ffc00c200 c=0x1
API_CREATE_RETURN a=0x0 b=0x561ffc00c218 c=0x561ffc00c218
```

The probe then calls `vkDestroyBuffer(device, buffer, &cb)` with the same application-side `VkAllocationCallbacks` object. The second custom repack invocation receives an already-zeroed guest allocator layout:

```
API_DESTROY_ENTER a=0x561ffc00c218 b=0x561ffc00c218 c=0x561ffc00c200
ALLOC_REPACK_BEGIN seq=2 guest_user=(nil) host_user=(nil) guest_alloc=(nil) guest_realloc=(nil) guest_free=(nil) guest_internal_alloc=(nil) guest_internal_free=(nil)
ALLOC_REPACK_END seq=2 host_user=(nil) host_alloc=(nil) host_realloc=(nil) host_free=(nil) host_internal_alloc=(nil) host_internal_free=(nil)
```

The process then exits `139` before any guest `pfnFree` entry. A preceding no-free control likewise showed the crash occurs before the guest free body. A host-side free-wrapper discriminator also failed to observe entry before the crash.

## Interpretation

This sharply moves the primary failure boundary upstream of callback execution. The destroy call is reaching `fex_custom_repack_entry(host_layout<VkAllocationCallbacks>&, const guest_layout<VkAllocationCallbacks>&)` with a null/zero guest representation despite the application passing `&cb`.

The leading hypothesis is therefore generated argument/member marshalling for a pointer to `VkAllocationCallbacks` on destroy-style calls, rather than guest callback ABI or guest `free()` behavior.

The create result demonstrates that the same type-level custom repack can work when the allocator arrives on a create call. The asymmetry between create and destroy is the next thing to explain.

## Next discriminators

1. Inspect generated host thunk code for one create function and its matching destroy function, especially pointer direction / temporary lifetime around `const VkAllocationCallbacks*`.
2. Add a pre-custom-repack trace at the generated wrapper boundary to determine whether the pointer is lost before `guest_layout<VkAllocationCallbacks>` construction or during that construction.
3. Compare a second Vulkan create/destroy pair (`vkCreateImage`/`vkDestroyImage` or `vkAllocateMemory`/`vkFreeMemory`) to establish whether this is generic for destroy/free-style allocator arguments.
4. Keep callback lifetime work separate until this marshalling defect is resolved; the allocator crash no longer provides clean evidence about callback executable lifetime.
