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

A cheaper Vulkan-specific prototype is also available without changing the generic generator. `ThunkLibs/libvulkan/Guest.cpp::OnInit()` already sends guest callback-unpacker addresses to host setup functions for X11. The same pattern can send the five allocator callback unpackers once at library initialization. The allocator custom repacker can then combine each stored unpacker with the per-application guest callback target using `MakeHostTrampolineForGuestFunctionAt(...)`. That is a useful fidelity discriminator before deciding whether the mechanism deserves a generic member annotation.

The FEX trampoline cache is keyed by guest target plus guest unpacker and reuses existing trampolines. Vulkan's current specification also requires application allocation functions to be called from the same thread that invoked the provoking Vulkan command. That aligns with FEX's existing host-to-guest callback path, which rejects unrelated asynchronous host-thread callbacks.

Open design work for full mediation:

- prove that a guest allocator's returned memory pointer is usable by native Vulkan through the existing shared address-space model;
- test all five callback signatures, including internal-allocation notifications;
- preserve `pUserData` exactly;
- verify 32-bit layout/guest-pointer behavior at source/build level while the current Linux Vulkan guest DSO remains 64-bit-only;
- separately convert the existing custom Vulkan wrappers that currently hardcode allocator NULL, because type repacking cannot help a wrapper that discards the parameter before native entry.

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

## Type-level generator discriminators

The first type-level prototype exposed a useful annotation distinction.

A synthetic `.ThunkGen` fixture with a struct containing only one function-pointer member marked `custom_repack` passes for both x86-32 and x86-64. A second synthetic allocator-like struct containing one `void*` user-data field plus five callback fields also passes when all six pointer-bearing members are marked `custom_repack`.

Receipt for the corrected single-callback case:

```text
workflow: Thunkgen custom repack function-pointer experiment
run: 31780646128
job: 94705465635
result: all 16 generator tests passed
```

The expanded allocator-like control is run `31781148262`; it also completed successfully.

Therefore ThunkGen already supports the **kind** of custom member repacking required by `VkAllocationCallbacks`.

The initial real Vulkan prototype instead used:

```cpp
template<>
struct fex_gen_type<VkAllocationCallbacks> : fexgen::emit_layout_wrappers {};
```

and continued to fail with:

```text
Unsupported parameter type 'const VkAllocationCallbacks *'
```

Source tracing explains why. `GenerateThunkLibsAction::OnAnalysisComplete()` deliberately assigns `TypeCompatibility::None` to every type carrying `emit_layout_wrappers`, bypassing normal compatibility analysis. That annotation means “emit wrappers even though compatibility checks would otherwise fail”; it is not an opt-in to normal custom repacking.

So the corrected experiment uses a plain registered type:

```cpp
template<>
struct fex_gen_type<VkAllocationCallbacks> {};
```

with all six pointer-bearing members marked `custom_repack`. This lets the normal compatibility pass decide whether the type is `Repackable`, matching the successful synthetic controls. The corrected hosted build/runtime discriminator is run `31781496151` on the owned fork.

This distinction is important: no generic generator relaxation is justified by the evidence so far.

## Type-level runtime discriminator

The representative runtime target remains `vkCreateBuffer`, because it previously demonstrated a raw allocator callback escape through an otherwise generic Vulkan thunk.

The first safety-only prototype fills non-NULL allocator callback members with host diagnostic stubs. Its useful outcomes are:

- **host stub is invoked instead of SIGILL:** proves one type-level policy intercepts generic allocator calls without per-command wrappers;
- **build fails after normal compatibility analysis:** identifies a real remaining type-layout limitation;
- **raw guest callback still executes:** proves another passthrough path remains.

If interception succeeds, the next discriminator should replace the diagnostic stubs with real cached host-to-guest trampolines using the Vulkan setup-hook pattern described above. Success for `vkCreateBuffer` would require allocator callbacks to execute in guest code, return normally, and leave the native Vulkan create/destroy pair successful.

## Current recommendation

For fidelity, full callback mediation best matches existing FEX thunk design. For an interim safety policy, explicit rejection/stubbing is more observable than raw forwarding and more semantically honest than silent NULL suppression.

The generator controls now show that `VkAllocationCallbacks` can plausibly remain a single type-policy problem rather than a 133-function wrapper problem. The current discriminator is whether the real Vulkan type passes normal repacking and intercepts the previously crashing `vkCreateBuffer` allocator path.

## Reopen conditions

Reopen this recommendation if:

- allocator callback lifetimes cannot be represented safely by the existing host-to-guest trampoline lifetime model;
- Vulkan or loader behavior requires preserving allocator pointer identity in a way a repacked host copy cannot provide;
- another FEX thunk library provides a stronger nested-callback precedent than the Wayland listener table;
- a project convention explicitly prefers silent feature suppression over diagnostic rejection for unsupported callbacks;
- the corrected normal-compatibility `VkAllocationCallbacks` experiment still cannot produce a repackable host representation despite the successful synthetic allocator-like control.
