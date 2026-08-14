# Resident bridge runtime scope sketch — provisional

This note scopes a possible long-term design beyond whole-wrapper NODELETE. It is a design checkpoint, not a product decision.

## Source property that makes a shared runtime plausible

Thunkgen's guest-side function-pointer bridge hash is derived from the canonical function signature:

```text
sha256("fexcallback_" + function_pointer_signature)
```

It is not qualified by thunk-library name. The generated special thunk is therefore conceptually a signature adapter, not Vulkan/GL/CUDA state.

Likewise, ordinary `CallHostFunction<signature>` and ordinary `CallbackUnpack<signature>::Unpack` are generic cross-ISA bridge code parameterized by signature.

This suggests that the process-lifetime ownership boundary can be smaller than a complete guest thunk wrapper.

## Scope ladder

### Narrow integration proof

Use one Vulkan-only resident sidecar and move only:

- the `vkEnumerateInstanceVersion` dynamic-PFN `CallHostFunction` adapter;
- the fixed Vulkan X11 callback unpackers.

Keep `libvulkan-guest.so` ordinary/unloadable. This is enough to test the real generated path after physical wrapper unmap.

### Per-library resident sidecar

For each thunk that publishes executable guest bridge addresses, generate a small resident bridge DSO containing its escaped generic adapters/unpackers and any library-specific custom bridge helpers.

This is relatively easy to fit into the existing per-library thunkgen/CMake model.

### Generic process-resident signature runtime

Longer term, aggregate ordinary signature-only bridge code across thunk libraries:

```text
process-lived generic bridge runtime
  - CallHostFunction<sig A>
  - CallHostFunction<sig B>
  - CallbackUnpack<sig A>
  - CallbackUnpack<sig C>
  ...

unloadable wrappers
  - Vulkan policy/name lookup/state
  - GL policy/name lookup/state
  - CUDA policy/name lookup/state
  - ordinary direct API wrappers
```

The existing signature-only callback hash is a natural deduplication key.

### Library-specific resident extensions

Not every callback path is generic. For example Wayland has custom callback handling that relocates `wl_array` arguments and performs library-specific packing logic.

Such helpers can remain in small library-specific resident bridge extensions while ordinary signature adapters are shared globally.

## Why this is attractive

- Already-selected bridge executable code remains mapped, closing the demonstrated selected-before-wrapper-unmap race for wrapper-owned bridge bytes.
- Ordinary wrapper constructor/static state can physically reset if that ever becomes useful.
- Dynamic PFN adapters for aliases with the same signature naturally converge on the same stable bridge implementation.
- Whole-wrapper residency cost becomes unnecessary for wrappers whose only escaped lifetime dependency is generic bridge code.
- No extra wrapper is inserted into the hot dynamic-PFN call path; publication can obtain the address of the exact `CallHostFunction<signature>` instantiation once and keep the existing custom r11/mm0 ABI.

## Remaining questions

1. Whether the resident runtime should be per-library first or process-global from the start.
2. How to aggregate/deduplicate signatures across independently generated thunk interfaces without making the build graph awkward.
3. How loader namespaces should interact with process-global FEX thunk state; current H registration and several host helper objects are already process-global, so true `dlmopen` isolation is a broader design problem than bridge residency.
4. Which custom guest callback helpers, beyond standard `CallbackUnpack`, need library-specific resident ownership.
5. Whether any bridge code itself eventually needs reclamation. If yes, execution hazard/lease semantics return as a requirement.

## Current experiment

Owned-FEX branch `diagnostic/generated-vulkan-split-bridge` is testing the narrow Vulkan integration shape. The first build reached thunkgen successfully and stopped on a missing X11 declaration include in the sidecar; that mechanical error was corrected and the same test was rerun. Do not interpret that first compile failure as evidence for or against the design.

The production direction should only move up this scope ladder after the narrow real-generated Vulkan discriminator succeeds.
