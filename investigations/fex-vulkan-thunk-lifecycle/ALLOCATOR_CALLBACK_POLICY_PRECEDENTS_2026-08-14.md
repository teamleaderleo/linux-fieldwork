# FEX callback-policy precedents for Vulkan allocators — 2026-08-14

## Question

The Vulkan allocator experiments now prove three separate facts:

1. raw guest `VkAllocationCallbacks` function pointers can reach native ARM code and fault;
2. consistent NULL suppression can remove that crash but silently discards valid guest allocator semantics;
3. a newly safe custom wrapper is still unsafe through GIPA unless dynamic custom registration follows the declaration.

The remaining product question is what FEX normally does when callbacks cross a thunk boundary, and which existing machinery can be reused for `VkAllocationCallbacks` rather than inventing a Vulkan-only convention.

Reviewed FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Existing callback mechanisms

### 1. Supported direct callbacks use host-to-guest trampolines

The thunk generator detects function-pointer parameters. For ordinary supported callbacks, guest packing calls `AllocateHostTrampolineForGuestFunction(...)`; host unpacking finalizes that preallocated trampoline with `FinalizeHostTrampolineForGuestFunction(...)` before calling the native API.

The common thunk runtime documents and implements the full host-to-guest callback path:

```text
guest callback target
  -> guest-side callback unpacker identity
  -> preallocated host trampoline
  -> host packer
  -> FEX callback transition
  -> guest callback
```

This is normal FEX thunk machinery, not a Vulkan-specific experiment.

### 2. Wayland supports callback tables explicitly

`wl_proxy_add_listener` is a stronger precedent than a single function-pointer argument. Its listener parameter is a table of guest callbacks with signatures determined from Wayland protocol metadata.

FEX marks the function custom, receives the guest callback table, derives each listener signature, and calls `FinalizeHostTrampolineForGuestFunction` for each callback entry. A special host packer handles `wl_array` for the 32-bit case.

So FEX already supports a model where one API parameter contains multiple callbacks that must be individually converted to host-callable trampolines.

### 3. Unsupported OpenGL debug callbacks use `callback_stub`

The generator exposes `fexgen::callback_stub`. OpenGL applies it to:

```text
glDebugMessageCallback
glDebugMessageCallbackARB
glDebugMessageCallbackAMD
```

For a stubbed callback, generated host code substitutes a host-callable stub instead of forwarding the guest function pointer. If the native library invokes the callback, the stub prints:

```text
FATAL: Attempted to invoke callback stub for <function>
```

and aborts.

This is an explicit unsupported-feature policy. It is deliberately different from allowing a cross-ISA guest address to reach native code.

## Why `VkAllocationCallbacks` currently falls outside those mechanisms

FEX declares `VkAllocationCallbacks` as `opaque_type`.

That tells the generator to pass pointers to the struct through without inspecting or repacking its members. The five callback members therefore remain guest function addresses when a generic Vulkan command forwards a non-NULL allocator.

The generator's normal struct-repacking logic already knows that function-pointer **members** cannot be copied naively: when it emits a `host_layout<T>` for a non-opaque struct, function-pointer members are zero-initialized by default and may be handled explicitly through custom member repacking.

The important distinction is therefore:

```text
current Vulkan policy:
VkAllocationCallbacks = opaque
  -> generator never sees nested callbacks
  -> raw guest callback pointers can cross

repacked-type policy:
VkAllocationCallbacks = inspected/repacked
  -> nested function pointers become explicit policy points
```

## Design options that fit existing FEX patterns

### A. Full mediation — highest fidelity

Teach the thunk generator or Vulkan guest packing to allocate/finalize host trampolines for the five callback members:

- `pfnAllocation`
- `pfnReallocation`
- `pfnFree`
- `pfnInternalAllocation`
- `pfnInternalFree`

`pUserData` remains the application data pointer carried with those callbacks.

This best matches FEX's ordinary callback and Wayland listener-table behavior.

The scalable form is a reusable nested-callback/member annotation, because 133 Vulkan commands accept this one struct type. Per-command custom guest entrypoints would duplicate the same transformation across a large API surface.

Open design work for full mediation:

- guest-side allocation of the correct trampoline/unpacker for each nested callback signature;
- host-side finalization during struct repacking;
- lifetime/reuse rules for allocator structs that may be used across object lifetime;
- callback `pUserData` semantics;
- 32-bit pointer/layout behavior in the generated host representation.

### B. Explicit unsupported callback stubs — safe and diagnostic, low fidelity

A type-level custom repacker could replace each nested guest allocator callback with a host-callable fatal stub, analogous to `callback_stub`.

This prevents raw guest addresses from reaching native code and produces an intelligible failure if native Vulkan actually uses the allocator.

It is still not Vulkan fidelity: valid non-NULL allocators would abort when used. It is stronger diagnostically than SIGILL and more explicit than silently ignoring the allocator.

### C. Consistent NULL suppression — demonstrated safe for one pair, low fidelity

The `vkCreateInstance` / `vkDestroyInstance` A/B proves that forcing NULL on both sides prevents the demonstrated callback escape and lets destroy return.

However, this hides a valid application allocator entirely. Extending it to the full 133-command surface also requires a scalable way to null the allocator parameter consistently rather than adding 125+ custom wrappers.

### D. Early rejection of non-NULL allocators

A generated/type-aware check could reject or abort before entering native Vulkan when a guest supplies a non-NULL allocator.

This is conceptually close to callback stubbing but fails at API entry rather than waiting for the host to invoke a callback. It may be easier to reason about than a fatal callback stub, but requires a deliberate project-level error policy because Vulkan APIs do not generally provide an FEX-specific unsupported-feature return code.

## Type-level experiment suggested by the source

The cheapest next technical discriminator is not another object-specific Vulkan wrapper. It is a type-level repacking experiment:

1. stop treating `VkAllocationCallbacks` as opaque;
2. emit/repack its layout;
3. mark the five function-pointer members for custom repacking;
4. initially fill them with host-side diagnostic stubs;
5. run a representative generic API such as `vkCreateBuffer` plus the instance create/destroy pair.

Useful outcomes:

- **build succeeds and diagnostic stub is called:** one type-level policy can cover the generic allocator surface, proving per-command wrappers are unnecessary;
- **generator cannot repack the struct cleanly:** identifies the exact generator capability needed before allocator policy can be centralized;
- **native Vulkan rejects the repacked allocator before callback:** tells us entry-time rejection/nulling may be the cleaner policy surface;
- **raw guest callback still executes:** indicates another passthrough path remains and the type-level assumption is wrong.

This experiment should remain internal research. A fatal-stub prototype is not a proposed upstream fix.

## Current recommendation

For fidelity, full callback mediation best matches existing FEX thunk design. For an interim safety policy, explicit rejection/stubbing is more observable than raw forwarding and more semantically honest than silent NULL suppression.

Before selecting a production policy, prove whether `VkAllocationCallbacks` can be centralized as one repacked callback-bearing type. If it can, the 133-command surface becomes a type-policy problem rather than a per-function maintenance problem.

## Reopen conditions

Reopen this recommendation if:

- allocator callback lifetimes cannot be represented safely by the existing host-to-guest trampoline lifetime model;
- Vulkan or loader behavior requires preserving allocator pointer identity in a way a repacked host copy cannot provide;
- another FEX thunk library provides a stronger nested-callback precedent than the Wayland listener table;
- a project convention explicitly prefers silent feature suppression over diagnostic rejection for unsupported callbacks.
