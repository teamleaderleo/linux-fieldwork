# Vulkan allocator mediation guest-state corruption — 2026-08-14

## Scope

This note records a failure in the **owned-fork allocator mediation candidate**, not a new pristine-FEX defect claim.

The candidate makes `VkAllocationCallbacks` repackable, converts its five callback function pointers to host-callable trampolines, and exercises a guest-valid `vkCreateBuffer` / `vkDestroyBuffer` pair using the same stack-local `VkAllocationCallbacks cb` on both calls.

Owned-fork run:

`31786206977`

Exact FEX product source before applying the diagnostic allocator mediation:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Artifact:

- id: `9213700983`
- name: `agent-b-allocator-guest-state-31786206977`
- digest: `sha256:14b5ca13bd305b844c2ca5255fe25ce405934611ccac63a5db9b99b322b0903a`

## Question

An earlier cross-call trace showed:

- create-side repacking received a fully populated guest allocator and built host trampolines;
- `vkCreateBuffer` succeeded and invoked the guest allocation callback;
- destroy-side repacking later saw an all-NULL guest allocator;
- the process then died 139.

Because the guest source visibly passes `&cb` to both create and destroy, the open question was whether:

1. guest memory itself was corrupted/zeroed between calls; or
2. destroy-side marshalling was reading the wrong representation.

## Direct guest-state trace

The follow-up prints the same guest `VkAllocationCallbacks` object before create, immediately after create returns, and immediately before destroy.

Before create:

```text
GUEST_CB_BEFORE_CREATE_A a=0x7fffffffd560 b=0x55b9c16d0024 c=0x55b9c16cc7dc
GUEST_CB_BEFORE_CREATE_B a=0x55b9c16cc7ed b=0x55b9c16cc7fe c=0x0
GUEST_CB_BEFORE_CREATE_C a=0x0 b=0x0 c=0x0
```

The object address is `0x7fffffffd560`. `pUserData`, allocation, reallocation, and free callbacks are all populated.

Host repack sequence 1 sees the same values and creates host trampolines:

```text
ALLOC_REPACK_BEGIN seq=1 guest_user=0x55b9c16d0024 guest_alloc=0x55b9c16cc7dc guest_realloc=0x55b9c16cc7ed guest_free=0x55b9c16cc7fe ...
ALLOC_REPACK_END seq=1 host_user=0x55b9c16d0024 host_alloc=0x7ffff7e3e090 host_realloc=0x7ffff7e3e0c0 host_free=0x7ffff7e3e0f0 ...
CB_ALLOC_ENTER a=0x55b9c16d0024 b=0x90 c=0x8
CB_ALLOC_RETURN a=0x55b9c16f3218 b=0x55b9c16f3200 c=0x1
API_CREATE_RETURN a=0x0 b=0x55b9c16f3218 c=0x55b9c16f3218
```

Immediately after `vkCreateBuffer` returns, **the same guest object at `0x7fffffffd560` is all zero**:

```text
GUEST_CB_AFTER_CREATE_A a=0x7fffffffd560 b=0x0 c=0x0
GUEST_CB_AFTER_CREATE_B a=0x0 b=0x0 c=0x0
GUEST_CB_AFTER_CREATE_C a=0x0 b=0x0 c=0x0
```

It remains zero immediately before destroy:

```text
GUEST_CB_BEFORE_DESTROY_A a=0x7fffffffd560 b=0x0 c=0x0
GUEST_CB_BEFORE_DESTROY_B a=0x0 b=0x0 c=0x0
GUEST_CB_BEFORE_DESTROY_C a=0x0 b=0x0 c=0x0
```

Destroy-side host repack sequence 2 therefore correctly observes the already-zero guest object:

```text
ALLOC_REPACK_BEGIN seq=2 guest_user=(nil) guest_alloc=(nil) guest_realloc=(nil) guest_free=(nil) ...
ALLOC_REPACK_END seq=2 host_user=(nil) host_alloc=(nil) host_realloc=(nil) host_free=(nil) ...
```

The process later exits 139.

## Interpretation

This falsifies the hypothesis that destroy marshalling independently dropped a still-valid allocator pointer or read a different guest representation.

The callback-bearing `VkAllocationCallbacks` object itself is overwritten between entry to `vkCreateBuffer` and the guest-visible return from that call.

The current custom repack exit hook is empty, and the Vulkan API parameter is `const VkAllocationCallbacks*`, so a correct mediation implementation must preserve the caller-owned allocator object unchanged across the call.

The immediate mechanism of the zeroing is **not yet established**. In particular, the first guess that generic 64-bit callback packing used `GuestStackBumpAllocator` was wrong: the generic 64-bit callback packer keeps its `PackedArguments` on the host stack; that guest-stack bump path is used for 32-bit guests.

Therefore the next source/runtime target is the host-to-guest callback return/CPU-state restoration path and any generated repack/argument storage that can write to the caller's guest stack object during or after the nested allocation callback.

## Design impact

The earlier `VkAllocationCallbacks` raw callback defect still needs callback mediation. This result adds a separate correctness condition for a faithful fix:

> converting the callbacks must not mutate or destroy the application-owned `VkAllocationCallbacks` object that was passed through a `const` pointer.

A type-level callback-member design should prefer the same rule already demonstrated by the DRM generator prototype: copy callback-bearing caller input to temporary thunk-owned storage, rewrite the temporary copy, and never repurpose the caller's object as host scratch state.

This run is fork-local diagnostic evidence, not upstream-ready contribution code.