# Hosted ARM64 Vulkan allocation-callback result — current FEX

Date: 2026-08-14

Owned FEX Actions run `31737446041` tested current reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a` on an ARM64 Ubuntu runner with an x86-64 guest rootfs, the established guest-X11 fixture, FEX Vulkan thunks, and host Lavapipe.

The guest creates a Vulkan instance and device, then calls generic `vkCreateBuffer` twice: once with a null allocator and once with a non-null guest `VkAllocationCallbacks` object.

Runtime matrix:

```text
fex_sha=71afe476751deac24adabd1adb575fd2337b6e0a
null=0
custom=132
```

Null-allocator control reaches:

```text
BEFORE_CREATE_BUFFER custom=0 calls=0
AFTER_CREATE_BUFFER result=0 buffer=<non-null> calls=0
NULL_ALLOCATOR_PASS
```

The non-null allocator case reaches:

```text
BEFORE_CREATE_BUFFER custom=1 calls=0
```

and then terminates with SIGILL / status 132 before `vkCreateBuffer` returns. The workflow asserts exactly `null == 0` and `custom == 132`.

## Interpretation

This promotes `VkAllocationCallbacks` from a source-level hazard to a demonstrated cross-ISA callback-mediation failure on a generic Vulkan command. The same fixture succeeds when no allocator callbacks are supplied, while a valid guest allocator causes execution to leave the normal guest-call path before the call returns.

This result is independent of dynamic `vkGetInstanceProcAddr` routing and independent of the separate Vulkan thunk unload/lifetime finding. It also avoids the create/destroy allocator-pairing ambiguity from an earlier model experiment: the failure occurs during one `vkCreateBuffer` call.

The source result remains consistent with FEX generator metadata that treats `VkAllocationCallbacks` as opaque while noting that its contained function pointers require additional support.

## Evidence boundary

Demonstrated by this run: x86-64 guest to ARM64 host, reviewed FEX `71afe476...`, generic `vkCreateBuffer`, null allocator succeeds, non-null guest allocator exits 132 before return.

Not demonstrated: all allocator-taking Vulkan commands, 32-bit guest execution, or behavior after a prospective allocator-callback mediation change.

FEX upstream remained read-only. The experiment ran only in the owned fork.
