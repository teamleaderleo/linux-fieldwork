# GL direct-helper build diagnostic — 2026-08-14

## Scope

This receipt covers the direct thunkgen + common helper conversion for GL on FEX branch:

`diagnostic/gl-direct-helper-f3ab-20260814`

Exact product source remains:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

The lifetime intent remains unchanged: keep the normal GL guest wrapper unloadable and place escaped guest executable families in `libfex-GL-bridge.so`:

- dynamic PFN callers from direct thunkgen accessors;
- fixed X11 callback unpackers;
- the allocator executable target itself.

## First direct-helper build: negative result

GitHub Actions run: `31794231350`

Job: `94747651553` (`gl-build`)

Checked-out diagnostic head: `227b233455ec6a4ef237a9abbcdb81bc4e7ea885`

The exact-product provenance gate passed: there was no pre-patch difference under `ThunkLibs`, `FEXCore`, or `Source` relative to `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

All five transforms then applied successfully and `git diff --check` passed. Host `thunkgen` also built successfully.

The failure occurred compiling the x86_64 guest resident bridge translation unit:

`ThunkLibs/libGL_bridge/Guest.cpp`

The generated direct bridge contains real GL/GLX signature types. The bridge TU only had the common guest/X11 includes, so those GL declarations were unavailable there. The first compiler failures were:

- `GLXHyperpipeConfigSGIX` was not declared in `thunkgen_bridge_libGL.inl:32`;
- `GLXHyperpipeNetworkSGIX` was not declared in `thunkgen_bridge_libGL.inl:44`.

The later template errors are downstream consequences of those missing types.

This run therefore did not reach the direct role-count gate or the ELF boundary checks. Preserve it as a type-visibility build failure, with no ELF/runtime conclusion attached.

Artifact receipt from the failed run:

- artifact name: `gl-direct-helper-build-31794231350`
- artifact ID: `9216761225`
- artifact SHA-256: `f027b6c4462f429879d4bd707f1cbcb523a304d1f73d20cf9dc5f5933766e0ae`

## Diagnostic fix

FEX diagnostic commit:

`cb93582fe73bcd42d05850772ccffa803f0c2ab3`

Commit message:

`fix: expose GL signature types to resident bridge`

The transform now emits the same GL declaration prologue used by `ThunkLibs/libGL/libGL_Guest.cpp` before including the generated direct bridge:

```cpp
#define GL_GLEXT_PROTOTYPES 1
#define GLX_GLXEXT_PROTOTYPES 1

#include <GL/glx.h>
#include <GL/glxext.h>
#include <GL/gl.h>
#include <GL/glext.h>

#undef GL_ARB_viewport_array
#include "glcorearb.h"
```

It retains the existing X11/custom resident exports for `XSync`, `XGetVisualInfo`, `XDisplayString`, and `FEXGLBridgeMalloc`.

## Validation status after the fix

The repository connector commit did not create a fresh Actions run. The diagnostic workflow still has only run `31794231350`, whose checkout is the earlier head `227b233455ec6a4ef237a9abbcdb81bc4e7ea885`.

Rerunning that failed run would execute the earlier checkout and reproduce the pre-fix transform, because `actions/checkout@v4` checks out the run ref/SHA and the workflow invokes the transform from that checkout.

The local sandbox also cannot resolve `github.com`, so a local clone/build could not substitute for the hosted runner.

Current state:

- source diagnosis: complete;
- diagnostic transform fix: committed at `cb93582fe73bcd42d05850772ccffa803f0c2ab3`;
- post-fix GL guest build: pending a run from the new head;
- post-fix direct role gate: pending;
- post-fix ELF boundary gate: pending;
- moved-reload PFN/GLX callback runtime: pending;
- clean GL source tranche 2: blocked on those gates.

## Next gate

Run `.github/workflows/gl-direct-helper-build.yml` from diagnostic head `cb93582fe73bcd42d05850772ccffa803f0c2ab3` (or a descendant carrying the same transform fix). Require:

1. `GL-guest` and `GL_bridge-guest` build;
2. exactly 736 generated `caller=1 unpacker=0` GL roles and zero unpacker roles;
3. unloadable wrapper with `NEEDED libfex-GL-bridge.so` and `$ORIGIN` lookup;
4. NODELETE only on `libfex-GL-bridge.so`;
5. resident exports for allocator target and fixed X11 unpackers;
6. then rerun the proven moved-reload GL runtime before creating tranche 2.
