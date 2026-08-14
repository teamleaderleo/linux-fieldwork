# Full Vulkan resident bridge derived from normal thunkgen output — runtime proof

Date: 2026-08-14

## Result

The resident Vulkan bridge no longer needs a hand-maintained list of migrated function names or signatures.

A second-stage generator now reads the **normal thunkgen-generated Vulkan guest inl**, extracts every emitted runtime `MAKE_CALLBACK_THUNK` signature, and generates:

- a process-resident `libfex-vulkan-bridge.so` containing the complete indirect bridge signature set;
- typed resident invoker/unpacker accessors consumed by the ordinary unloadable Vulkan wrapper.

The ordinary Vulkan interface remains the single source of truth. The derived bridge passes all three real hosted ARM64/Lavapipe lifecycle discriminators:

1. retained dynamic PFN after physical wrapper unload;
2. retained Vulkan/X11 host->guest callback after physical wrapper unload;
3. forced moved physical wrapper reload with stable native H.

Final marker:

```text
DERIVED_VULKAN_BRIDGE_RUNTIME_OK
```

## Owned-fork carrier

Repository: `teamleaderleo/FEX`

Branch: `diagnostic/thunkgen-guest-bridge-output`

Reviewed stock base: `71afe476751deac24adabd1adb575fd2337b6e0a`

Workflow head:

```text
3288618bdb08cd46b1920d5772e376701e728f70
```

Workflow: `.github/workflows/vulkan-derived-bridge-runtime.yml`

Run: `31779714685`

Job: `94702610284`

Artifact: `vulkan-derived-bridge-runtime-31779714685`

Artifact ID: `9211297020`

Artifact zip SHA-256:

```text
a9650949c881ef1c80456a4594b2e9b584af604a2bea136c2820eab6be06cd19
```

## Derived signature coverage

The runtime receipt records:

```text
SOURCE_SIGNATURES=476
BRIDGE_SIGNATURES=476
```

Thus every deduplicated runtime bridge signature emitted by normal Vulkan guest thunkgen output was also emitted into the resident bridge.

Thunkgen already deduplicates identical function signatures by the callback SHA before it emits `MAKE_CALLBACK_THUNK`, so the second-stage extractor inherits the exact emitted bridge set rather than reconstructing it from API names.

The resident bridge file in this RelWithDebInfo build is:

```text
BRIDGE_FILE_BYTES=2079504
```

about 1.98 MiB on disk. This is a debug-information-bearing ELF file size, not measured RSS.

## Implementation shape

`extract_guest_bridge.py` parses normal generated guest thunk output and emits:

- `thunkgen_guest_libvulkan_bridge.inl` — all signature thunks plus resident invoker/unpacker exports;
- `thunkgen_guest_libvulkan_bridge_accessors.inl` — typed C++ accessors used by the ordinary wrapper.

The wrapper's complete `FOREACH_internal_SYMBOL` dynamic function table now uses:

```text
FEXGetResidentCallerForHostFunction(name)
```

rather than wrapper-local `GetCallerForHostFunction(name)`.

Automatically generated guest callback parameters are also redirected by type so `AllocateHostTrampolineForGuestFunction(...)` obtains a resident callback unpacker rather than publishing a wrapper-local `CallbackUnpack<T>::Unpack` address.

Handwritten Vulkan X11 initialization still uses explicit resident unpacker accessors because those callbacks are configured manually rather than represented as ordinary generated callback parameters.

Exported bridge accessor symbols are library-qualified (`fex_bridge_libvulkan_*`) so multiple per-library resident bridge DSOs do not introduce identically named ELF exports.

## Dynamic PFN after wrapper unmap

FEX publishes the real host PFN against a resident automatically derived invoker:

```text
Linking address 0x7ffff76a80f4 to resident host invoker 0x7ffff7e5b970
DERIVED_PFN_BEFORE gipa=0x7ffff7eb1440 H=0x7ffff76a80f4 bridge_maps=5
```

After final close:

```text
DERIVED_PFN_AFTER_CLOSE gipa_mapped=0 bridge_maps=5
DERIVED_PFN_OK version=4206867
```

The ordinary wrapper is physically gone and the retained real Vulkan PFN still succeeds.

## Host->guest callback after wrapper unmap

The same full derived bridge routes real Vulkan entrypoints through resident invokers:

```text
Linking address 0x7ffff7b97bd0 to resident host invoker 0x7ffff7e5c960
Linking address 0x7ffff76a4d60 to resident host invoker 0x7ffff7e5f4c0
Linking address 0x7ffff7b97ee4 to resident host invoker 0x7ffff7e57530
DERIVED_X11_BEFORE gipa=0x7ffff7eb1440 xlib=0x7ffff7b97ee4
```

Before close:

```text
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
Opening host-side X11 display: 0x12345000 -> 0xff886997c000
```

After final wrapper close:

```text
DERIVED_X11_AFTER_CLOSE gipa_mapped=0
DERIVED_X11_CALLBACK_BEGIN
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
Opening host-side X11 display: 0x12346000 -> 0xff886997e800
DERIVED_X11_CALLBACK_RETURN result=0
DERIVED_X11_OK
```

So the automatically derived resident invoker plus resident handwritten X11 unpackers preserve both concrete bridge directions after physical wrapper reclamation.

## Forced moved wrapper reload

Generation 1:

```text
DERIVED_GEN1 gipa=0x7ffff7eb1440 H=0x7ffff76a80f4 ranges=5
```

After final close and exact old-wrapper range reservation, generation 2 moves while native H remains identical:

```text
DERIVED_GEN2 gipa=0x7ffff7660440 H=0x7ffff76a80f4 moved=1 same_H=1
DERIVED_MOVED_OK
```

The runtime completes successfully without generation-specific H retirement/rebind because H already points at process-lived bridge code.

## Why this matters for implementation scope

This removes the largest maintenance objection to the earlier generated split proof.

The resident bridge can be derived from normal per-library thunkgen output rather than maintaining a second list of Vulkan APIs/signatures. A new thunkgen AST/CLI mode is **not required** to demonstrate a complete per-library bridge set.

A native thunkgen bridge-output mode may still be cleaner long term than parsing generated text, but it is an implementation-quality choice rather than a prerequisite for the architecture.

The same post-process shape should be applicable to GL and CUDA because their normal thunk interfaces already generate runtime indirect signatures. Library-specific escaped callbacks/targets still require small resident extensions, such as GL's wrapper-local `malloc_wrapper` target and Wayland's custom array callback helper.

## Remaining cautions

- Per-library sidecars remain the preferred first general implementation. Host wrapper semantics can depend on per-parameter annotations in addition to textual C function signature, so process-global cross-library signature deduplication needs a compatibility audit.
- Any wrapper-local executable guest **target** published to host state must move as well as its unpacker. GL's current `malloc_wrapper` is one concrete example.
- The second-stage parser depends on thunkgen's generated `MAKE_CALLBACK_THUNK` text format. A native bridge-output mode could remove that textual coupling after the architecture is accepted.
- Real GL/CUDA/Wayland runtime tests remain necessary before calling the mechanism generic across thunk libraries.

## Current ranking

1. Whole-wrapper NODELETE remains the smallest near-term containment if process-lifetime wrapper residency is acceptable.
2. Per-library derived resident bridge + unloadable wrapper is now the strongest demonstrated unload-preserving architecture and no longer requires a hand-maintained Vulkan signature list.
3. Owner/generation + execution lease/hazard/grace period remains the full-reclamation fallback if escaped bridge executable code itself must be reclaimed.

All code and CI work stayed on owned repositories/forks. No upstream interaction occurred.
