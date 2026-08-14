# Common per-library guest bridge helper — CUDA validation — 2026-08-14

## Result

Branch:

`teamleaderleo/FEX:diagnostic/cuda-common-bridge-helper-f3ab-20260814`

Workflow run:

`31792606593` — local and resident ARM64 matrix jobs both completed successfully.

The branch remains an exact-product diagnostic carrier: before workflow transforms, `ThunkLibs`, `FEXCore`, and `Source` match `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

## Helper contract exercised

The research CMake helper is:

```cmake
add_guest_bridge(BRIDGE_NAME SONAME
  OUTPUT_NAME ...
  WRAPPER_TARGET ...
  GENERATOR ...
  DEP_TARGETS ...
  INCLUDE_DIRS ...)
```

It performs only packaging/wiring:

- creates `lib<bridge>-guest-deps`;
- inherits generic and library-local include/dependency targets;
- creates the bridge with normal `add_guest_lib` machinery;
- sets `DF_1_NODELETE` only on the bridge for shared guest builds;
- optionally depends on `<generator>-guest-bridge-gen`;
- links the already-created ordinary wrapper to the companion;
- adds the same generator dependency to the wrapper when required.

It does not select bridge signatures or infer lifetime semantics.

CUDA now uses one call:

```cmake
add_guest_bridge(cuda_bridge "libfex-cuda-bridge.so"
  OUTPUT_NAME "fex-cuda-bridge"
  WRAPPER_TARGET cuda-guest
  GENERATOR libcuda
  DEP_TARGETS libcuda-guest-deps
  INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/../libcuda")
```

This replaces the earlier repeated manual target/link/NODELETE/dependency block.

## Runtime gate

The helper-backed CUDA build retained the exact parser-free direct-generator lifetime discriminator:

- generated `callback_member` path executes successfully before unload;
- generation-1 wrapper physically unloads;
- all old wrapper mappings are reserved;
- generation 2 is forced to a different guest address;
- generation 2 does not re-register the callback;
- local wrapper-owned `GuestUnpacker` lies in the retired wrapper and exits 139;
- helper-packaged resident `GuestUnpacker` lies outside the retired wrapper and the retained callback returns successfully.

Both workflow jobs passed their full expected-result assertions.

## Consequence

The common helper has one full causal consumer and did not change the lifetime semantics established by direct thunkgen bridge/accessor output.

Next helper gates:

1. generalized Wayland custom listener companion;
2. real Vulkan direct caller companion.

If both pass, the repeated experimental CMake wiring can be replaced by this helper across the validated per-library companion designs without changing the ownership boundary.
