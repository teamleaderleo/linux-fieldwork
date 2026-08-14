# Per-library guest bridge build-system contract — 2026-08-14

## Goal

Make the validated resident-executable ownership model easy to apply without turning it into one process-global immortal bridge library.

The build unit is:

```
ordinary lib<name>-guest.so          unloadable
libfex-<name>-bridge.so              process-resident (DF_1_NODELETE)
```

Only libraries that publish guest executable addresses beyond wrapper lifetime need the companion.

## Proposed CMake responsibility

A small helper should sit next to `generate()` / `add_guest_lib()` and perform only packaging/wiring. Conceptually:

```cmake
add_guest_bridge(
  LIBRARY      cuda
  GENERATOR    libcuda
  SONAME       libfex-cuda-bridge.so
  SOURCE_DIR   ../libcuda_bridge
  EXTRA_DEPS   ../libcuda
)
```

The exact syntax is secondary; the required behavior is:

1. depend on `<generator-name>-guest-bridge-gen` so direct thunkgen bridge definitions and accessors exist before compilation;
2. create a guest companion target from library-local bridge source;
3. give the companion access to the normal guest include path plus library-specific type headers;
4. link the ordinary wrapper to the companion so generated accessor symbols resolve;
5. mark **only the companion** `LINKER:-z,nodelete` for shared guest builds;
6. preserve the ordinary wrapper's original SONAME and unload semantics;
7. keep install layout library-local and explicit.

## What the helper must not do

It must not:

- add NODELETE to the ordinary guest wrapper;
- combine unrelated thunk libraries into a single global bridge automatically;
- move ordinary `fexfn_pack_*` API packers into the bridge;
- decide which function-pointer signatures escape;
- infer custom library lifetime semantics from CMake target names;
- introduce unload retirement / quiescence policy.

Those decisions belong to thunkgen role metadata and the library-specific integration respectively.

## Direct generator inputs

For a generated library `<gen>`:

```
thunkgen_guest_<gen>.inl
thunkgen_bridge_<gen>.inl
thunkgen_bridge_accessors_<gen>.inl
```

The ordinary wrapper includes:

- `thunkgen_bridge_accessors_<gen>.inl`;
- `thunkgen_guest_<gen>.inl`.

The companion includes:

- common guest bridge primitives;
- library-specific type definitions as needed;
- `thunkgen_bridge_<gen>.inl`.

No generated-C++ parser is part of this build path.

## Role boundary

Thunkgen, not CMake, decides per canonical signature whether the companion contains:

```
needs_caller
needs_unpacker
```

The build helper only makes the companion available and resident.

This is important for GL: all 736 current stock bridge signatures are caller-only. A build helper that blindly instantiates callback unpackers would recreate the false 23-argument callback compile problem even if the packaging boundary were otherwise correct.

## Custom bridge source

Library-specific escaped executable targets can live in the same companion source tree alongside generated bridge definitions.

Examples:

- GL allocator callback target;
- Vulkan/GL fixed X11 callback families;
- Wayland runtime protocol-signature dispatcher.

The 32-bit Wayland `wl_array` special case does **not** require a separate resident guest unpacker family: its special code is the process-lived host-side `CallGuestPtrWithWaylandArray` packer. A 32-bit validation should pair that existing host packer with the same resident guest-unpacker ownership used by the Wayland companion.

This keeps one lifetime owner per thunk library while allowing generated and semantic/custom bridge families to coexist.

## Validation required before introducing a common helper

Do not refactor the repeated experimental CMake into a common helper until these gates are green:

1. direct role-aware Vulkan caller bridge;
2. direct role/accessor GL caller-only generation;
3. direct role/accessor CUDA `callback_member` moved-reload retained callback;
4. generalized Wayland 41-signature companion runtime regression.

The first, second, and fourth gates are already green. CUDA direct role/accessor integration is the remaining gate.

After that, replace repeated experimental target wiring with the helper and rerun at least Vulkan, CUDA, and Wayland before treating the helper itself as validated.
