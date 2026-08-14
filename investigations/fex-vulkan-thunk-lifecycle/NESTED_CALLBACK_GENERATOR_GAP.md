# Nested callback generator gap: conversion and containing-object lifetime are separate axes

Date: 2026-08-14

## Why this note exists

The DRM runtime work now proves three distinct stages on exact current FEX main (`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`):

1. raw callback-bearing ABI-compatible structures can pass x86 guest function pointers directly into native ARM libraries and crash;
2. the existing FEX two-stage callback trampoline protocol repairs both synchronous and retained DRM callbacks while the ordinary guest wrapper remains loaded;
3. for a retained callback, moving the FEX-owned guest unpacker into a resident per-library sidecar changes the same forced moved-wrapper reload from 139 to 0.

The remaining engineering question is how much of that path thunkgen can own automatically.

## Current direct-callback codegen already has the right protocol

For an ordinary function-pointer parameter that thunkgen classifies as a callback, generated guest code wraps the guest function before crossing to the host:

```cpp
AllocateHostTrampolineForGuestFunction(a_i)
```

Generated host code then finalizes the same partially initialized trampoline with the exact native callback signature before the host call:

```cpp
FinalizeHostTrampolineForGuestFunction(args->a_i)
```

This is exactly the two-stage protocol that repaired `drmHandleEvent` and `drmServerInfo::load_module` in the focused diagnostics.

The resident bridge work adds a compatible lifetime refinement: direct callback parameters can select their guest `CallbackUnpack<signature>::Unpack` from process-lived per-library bridge code by type rather than instantiating that unpacker in an unloadable ordinary wrapper.

So the missing mechanism is not a new callback ABI. It is **classification and code generation for callbacks nested inside structures**.

## Why current member annotations do not solve it

`GeneratorInterface.h` currently offers only one member annotation:

```cpp
fexgen::custom_repack
```

The analysis path accepts member specializations only when they derive from `custom_repack`.

There are two blockers for using that directly on current DRM declarations.

### 1. Callback-bearing DRM structs are declared assumed-compatible

Current DRM interface declarations contain:

```cpp
template<>
struct fex_gen_type<drmServerInfo> : fexgen::assume_compatible_data_layout {};

template<>
struct fex_gen_type<drmEventContext> : fexgen::assume_compatible_data_layout {};
```

Thunkgen explicitly rejects member annotations when the parent `RepackedType` is already assumed compatible:

```text
May not annotate members of opaque types
```

Thus a callback field cannot simply be layered on top of the current `assume_compatible_data_layout` declarations.

### 2. `custom_repack` runs on the host-side repack path

Generated `repack_wrapper` constructs a `host_layout<T>` from guest memory and then calls `fex_apply_custom_repacking_entry(...)` / the user-provided `fex_custom_repack_entry(...)` for annotated members.

That is useful for host-side transformation and can be used to finalize or replace fields in a host-side copy. It does **not** cause generated guest code to allocate the partial callback trampoline before crossing the thunk boundary.

That guest-side allocation matters because a host-to-guest trampoline needs both:

- the application `GuestTarget`; and
- a guest `GuestUnpacker` address.

The `GuestUnpacker` is executable guest code, and for unload-preserving designs it should come from the resident per-library bridge sidecar.

## Host-only allocation is possible in principle, but needs another channel

FEX core exports:

```cpp
FEX::HLE::MakeHostTrampolineForGuestFunction(
    void* HostPacker,
    uintptr_t GuestTarget,
    uintptr_t GuestUnpacker)
```

`common/Host.h` weak-imports that symbol for host thunk DSOs, so a custom host repack implementation could allocate a fully initialized trampoline in one call.

However, the host repack code still does not know the guest-side resident `GuestUnpacker` address. The raw structure only contains the application callback target.

Therefore a host-only nested-callback implementation would require an additional mechanism such as:

- a process-lived signature -> resident guest unpacker registry populated by the guest bridge; or
- hidden per-call metadata carrying the resident guest unpacker address.

Without such a channel, `custom_repack` alone is insufficient.

## Preferred generator direction: extend the existing two-stage callback path into fields

The least novel implementation model is to make nested fields participate in the same protocol already emitted for direct callback parameters.

Conceptually, a member annotation would say that a specific function-pointer field is a guest callback, for example:

```cpp
// illustrative research syntax only
template<>
struct fex_gen_config<&drmEventContext::vblank_handler>
  : fexgen::callback_member {};
```

The exact syntax is not important yet. The semantics are.

For a synchronous input structure such as `drmEventContext`, generated code could:

1. make a guest-side temporary copy of the caller's structure;
2. replace each callback field in that copy with a partially initialized host trampoline using the resident per-library guest unpacker for the exact field type;
3. pass the copy through the normal thunk argument transport;
4. make the host-side repack/finalization path recognize those callback fields and finalize each trampoline with the exact native signature;
5. call native code with the host-side copy;
6. discard the temporary copies after return.

This reuses the proven callback protocol and avoids mutating caller-owned input.

It also gives the derived resident bridge machinery a natural integration point: once analysis classifies a nested callback function type, that signature can be added to the same per-library generated bridge signature set used by ordinary callback parameters.

## Separate axis: does native code retain the containing structure?

Nested callback classification is not enough for every API.

`drmHandleEvent` is synchronous: native libdrm consumes the `drmEventContext` during the call. Temporary guest/host copies are sufficient.

`drmSetServerInfo` is different. Runtime proof shows that registration returns with callback count zero, then a later `drmOpen` uses the previously supplied `drmServerInfo` and invokes `load_module`. Native code retains the containing structure pointer beyond the registration call.

A normal generated `repack_wrapper` owns a temporary host copy whose lifetime ends when the thunk call returns. Even perfect callback-field conversion would therefore leave a dangling native structure pointer for APIs with this ownership contract.

This is an independent generator concern:

> callback-field conversion answers how a callable pointer crosses the ISA boundary; containing-object ownership answers how long the replacement structure must remain alive.

A future metadata model should not conflate them.

## Two-axis model

A useful classification table is:

| Callback field | Containing object | Example | Needed machinery |
|---|---|---|---|
| Direct parameter | call-scoped | ordinary generated callback parameter | existing allocate + finalize path |
| Nested field | call-scoped | `drmEventContext::vblank_handler` | nested callback classification + temporary copies + allocate/finalize |
| Nested field | native-retained | `drmServerInfo::load_module` | nested callback conversion **plus** persistent host replacement-object ownership |
| Nested field | native-retained, wrapper unloadable | moved-reload DRM receipt | above **plus** resident FEX-owned guest unpacker |

The last row is now runtime-proven: wrapper-owned unpacker exits 139 after forced moved reload; resident unpacker exits 0 under the same fixture.

## Metadata implication

If thunkgen is extended, two separate annotations/properties are likely clearer than one overloaded callback marker:

### Callback-field metadata

Needs to identify:

- the field as a guest callback pointer;
- the exact function signature;
- whether a callback is unsupported/stubbed rather than bridged;
- the resident per-library unpacker identity/type.

### Parameter / containing-object lifetime metadata

Needs to identify at least:

- call-scoped input: temporary replacement object is sufficient;
- native-retained input: host replacement object must outlive the thunk call;
- replacement/update semantics: whether a later registration supersedes an earlier retained object;
- explicit destroy/unregister operation if one exists.

The generator should not guess retention from `const` or pointer type.

## Alternative design: resident-unpacker registry

A more invasive but potentially elegant alternative is a process-lived mapping from callback signature identity to resident guest unpacker address.

Then host repack code could use the exported one-shot core API:

```cpp
MakeHostTrampolineForGuestFunction(
    host_packer,
    raw_guest_target,
    resident_guest_unpacker)
```

This would avoid guest-side temporary callback rewriting for the callback field itself.

Tradeoffs:

- it requires a new guest-bridge -> host/core registration mechanism;
- signature identity must be stable and per-library semantics still matter;
- retained containing structures still require explicit host-side ownership;
- it increases core/runtime coupling compared with extending existing thunkgen guest/host code generation.

Given that direct callbacks already use guest allocation + host finalization successfully, the field-extension path is the smaller conceptual change.

## Recommended next implementation experiment

Use `drmHandleEvent`, not `drmSetServerInfo`, as the first generator prototype.

It isolates nested callback conversion without the independent retained-structure ownership problem. A successful prototype should remove the handwritten DRM event guest/host wrappers while preserving the existing ARM64 pipe-fed runtime matrix:

```text
native=0
pristine=132
generated-nested-callback-candidate=0
```

and must still execute exactly one real guest callback and return from `drmHandleEvent`.

Only after that should retained-structure metadata be prototyped on `drmSetServerInfo`.

## Scope

This is an implementation-design note grounded in current source and the retained DRM/Vulkan runtime receipts. It does not claim a finished generator implementation or define final annotation syntax.

No upstream FEX repository was modified or contacted. Any code experiment remains research-only on owned surfaces and is not an upstream contribution.
