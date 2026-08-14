# Generated resident bridge — explicit function-type thunkgen proof

Date: 2026-08-14

## Question

The first real generated Vulkan split-bridge prototype used fake companion API declarations only to force thunkgen to emit the exact indirect function-pointer signatures needed by the resident bridge.

Are those fake API symbols actually necessary?

No.

Thunkgen already accepts explicit function/function-pointer types through `fex_gen_type<T>`. Such types are added directly to its runtime host-function-pointer signature set without creating an ordinary API thunk/export.

## Owned-fork proof

Repository: `teamleaderleo/FEX`

Branch: `diagnostic/generated-vulkan-split-bridge-types`

Workflow: `.github/workflows/generated-vulkan-bridge-types-build.yml`

Run: `31778381951`

Job: `94698584115`

Checked-out head:

```text
d474cf89d3aa67ae069658587bcd9ee3d4fcac76
```

Final marker:

```text
EXPLICIT_TYPE_BRIDGE_BUILD_OK
```

## Interface shape

The bridge companion declares no fake function symbols. It registers only the function types:

```cpp
using EnumerateInstanceVersionSignature = VkResult(uint32_t*);
using XlibPresentationSupportSignature =
  VkBool32(VkPhysicalDevice, uint32_t, Display*, VisualID);

template<typename>
struct fex_gen_type {};

template<>
struct fex_gen_type<VkPhysicalDevice_T> : fexgen::opaque_type {};
template<>
struct fex_gen_type<_XDisplay> : fexgen::opaque_type {};

template<>
struct fex_gen_type<EnumerateInstanceVersionSignature> {};
template<>
struct fex_gen_type<XlibPresentationSupportSignature> {};
```

The type annotations mirror the subset required by the original Vulkan interface for these signatures.

## Build assertions

Thunkgen generated the bridge inl from that type-only interface and both DSOs built successfully:

```text
libfex-vulkan-bridge.so
libvulkan-guest.so
```

The generated bridge inl contains `MAKE_CALLBACK_THUNK` entries, but the workflow explicitly verifies it contains neither fake prototype name from the earlier experiment.

Lifetime/linkage remained correct:

```text
bridge: FLAGS_1 NODELETE
ordinary Vulkan wrapper: no NODELETE
ordinary Vulkan wrapper: NEEDED libfex-vulkan-bridge.so
```

The resident bridge remains very small in this two-signature build; its dynamic section begins around `0x2dd0` and its only runtime `NEEDED` dependency is libc.

## Source support

Thunkgen analysis already has a direct path for `fex_gen_type<T>` where `T` is a function pointer or function type: it canonicalizes the function type and adds it to `thunked_funcptrs` rather than treating it as a normal data-layout type.

Therefore a bridge companion can request runtime bridge signatures directly rather than inventing unused API endpoints.

## Implication

The first production-shaped per-library bridge generator does not need a new fake API surface.

There are still two implementation choices:

1. generate a per-library bridge companion interface containing the required explicit function types; or
2. add a real bridge-only output mode to thunkgen so it can parse the ordinary library interface once and emit its indirect bridge set automatically.

The second removes duplicated signature/type lists and is likely cleaner once the Vulkan prototype's moved-generation runtime is fully validated. The first is already mechanically proven and can serve as a smaller intermediate implementation.

This proof changes only generator/build scaffolding. The real generated PFN and X11 callback runtime evidence remains on `diagnostic/generated-vulkan-split-bridge` and is recorded separately.

All work stayed on owned repositories/forks. No upstream interaction occurred.
