# GL direct-helper build diagnostic — 2026-08-14

## Scope

This receipt covers the direct thunkgen + common helper conversion for GL on FEX branch:

`diagnostic/gl-direct-helper-f3ab-20260814`

Exact product source remains:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

The lifetime intent remains unchanged: keep the normal GL guest wrapper unloadable and place escaped guest executable families in `libfex-GL-bridge.so`:

- dynamic PFN callers from direct thunkgen accessors;
- fixed X11 callback unpackers;
- allocator executable target plus allocator unpacker.

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

## Fix 1 — GL/GLX type visibility

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

A compare against the failed carrier head showed this commit was one commit ahead and changed only `LinuxFieldwork/apply_gl_helper_direct_bridge.py` (11 additions, 1 deletion).

## Artifact audit found two more deterministic transform bugs

The first failed artifact ZIP was downloaded and inspected directly. Its `product.diff` preserved transformed wrapper text that the compiler had not yet reached because the bridge TU failed first.

### Fix 2 — allocator unpacker stayed wrapper-local

The transform removed the wrapper-local `malloc_wrapper` target and changed the first argument of `GL_SetGuestMalloc` to `FEXGLBridgeMalloc`, but left this second argument behind:

```cpp
(uintptr_t)CallbackUnpack<decltype(malloc_wrapper)>::Unpack
```

That is both a compile error after deleting `malloc_wrapper` and a lifetime error: the allocator callback family requires the guest target and unpacker to remain resident together.

FEX diagnostic commit:

`501e40e1d290fb86ac2367621eae959ad2100751`

Commit message:

`fix: keep GL allocator unpacker resident`

The companion now exports:

- `FEXGLBridgeMalloc`
- `fex_gl_bridge_malloc_unpacker`
- `fex_gl_bridge_xsync_unpacker`
- `fex_gl_bridge_xgetvisualinfo_unpacker`
- `fex_gl_bridge_xdisplaystring_unpacker`

`OnInit` passes the resident allocator target and resident allocator unpacker together.

### Fix 3 — declaration injection split `static void OnInit`

The original transform searched for the substring:

```cpp
void OnInit() {
```

inside the real source spelling:

```cpp
static void OnInit() {
```

The artifact therefore contained an invalid first declaration beginning with:

```cpp
static extern "C" void* FEXGLBridgeMalloc(...)
```

and `OnInit` itself lost its `static` prefix.

FEX diagnostic commit:

`01a52df6d0c0c4c9635450f3cb89c9dc05435122`

Commit message:

`fix: preserve static GL OnInit declaration`

The transform now anchors on the full `static void OnInit() {` spelling and inserts declarations before it.

## Receipt hardening

The generated companion source is a new untracked file during the diagnostic transform, so plain `git diff` omitted it from the first artifact's `product.diff`.

Build workflow commit:

`77a650b725140d597510189af05d569abb91f2b2`

Commit message:

`ci: audit transformed GL bridge source before build`

The build workflow now:

- marks `ThunkLibs/libGL_bridge/Guest.cpp` intent-to-add before `git diff --check` / `product.diff`;
- asserts `static void OnInit()` survives;
- rejects `static extern "C"`;
- rejects any remaining `malloc_wrapper` reference in the wrapper;
- requires the resident allocator unpacker call;
- requires the GLX declaration include set;
- checks the allocator unpacker export in the ELF boundary gate.

## Actions registration correction

Initial connector polls immediately after diagnostic commits returned no new workflow runs. A draft PR carrier (`#3`) was created as a temporary trigger experiment.

Later branch-level Actions polling showed the push runs had registered after a delay. The earlier "no run visible" observation was therefore a polling-timing result, not evidence that connector-authored pushes cannot trigger Actions.

The diagnostic PR carrier was closed without merge and retained only as a receipt.

## Second direct-helper build: negative result

GitHub Actions run: `31796842469`

Job: `94755677208` (`gl-build`)

Checked-out diagnostic head: `77a650b725140d597510189af05d569abb91f2b2`

Results before the failure:

- exact-product provenance passed;
- all direct/helper transforms applied;
- hardened transformed-source audit passed;
- `git diff --check` passed;
- host `thunkgen` built successfully.

The x86_64 resident bridge then failed immediately with:

```text
ThunkLibs/libGL_bridge/Guest.cpp:11:10: fatal error: glcorearb.h: No such file or directory
   11 | #include "glcorearb.h"
```

The compile command for the companion had generated-output and common thunk include directories, but no `ThunkLibs/libGL` include directory. This differs from the ordinary wrapper because quoted `"glcorearb.h"` naturally resolves beside `ThunkLibs/libGL/libGL_Guest.cpp`; the new companion source lives under `ThunkLibs/libGL_bridge`.

The role and ELF gate was skipped because compilation stopped first.

Artifact receipt:

- artifact name: `gl-direct-helper-build-31796842469`
- artifact ID: `9217732251`
- artifact SHA-256: `fd8075a0e36cc6491e58633e9a4c8ee1e8ffdb83db4fa7f0cf0bae09f47e8546`

The hardened artifact was downloaded and inspected. Its `product.diff` includes the new bridge source and confirms before this include-path failure:

- `static void OnInit()` is preserved;
- `malloc_wrapper` is removed;
- `GL_SetGuestMalloc` receives `&FEXGLBridgeMalloc` plus `fex_gl_bridge_malloc_unpacker()`;
- the bridge defines the allocator target/unpacker and fixed X11 unpackers.

## Fix 4 — inherit GL's local header directory

Repository inspection confirms the FEX-owned header is:

`ThunkLibs/libGL/glcorearb.h`

The common `add_guest_bridge` helper already supports library-specific `INCLUDE_DIRS`, applying them to the companion dependency target.

FEX diagnostic commit:

`0dc102a565320d28a0b30a1f1bd53b9c5f9a799d`

Commit message:

`fix: expose local GL headers to resident bridge`

The GL bridge integration now adds:

```cmake
INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/../libGL"
```

This keeps the bridge C++ include prologue identical to the ordinary GL wrapper while using the common helper's existing include inheritance path.

Because the transform file is in both workflow path filters, this commit is expected to start fresh build/ELF and moved-reload runtime runs after Actions registration.

## Direct-helper moved-reload runtime gate

Runtime workflow commit:

`d972f6ee4766f807713a9ba117a438b02d0eb7d2`

Workflow:

`.github/workflows/gl-direct-helper-runtime.yml`

Original run from that workflow commit:

`31796930801`

Job:

`94755951349` (`gl-runtime`)

This original run predates Fix 4 and was already in its build step when Fix 4 was committed. Preserve its eventual result independently; a fresh run from `0dc102a565320d28a0b30a1f1bd53b9c5f9a799d` is the relevant post-fix gate.

The runtime gate applies the same exact-product direct-helper transforms and adds runtime-only observability. It deliberately avoids restoring the older companion name-to-caller map. Instead, two magic diagnostic queries in the wrapper expose the already-generated `HostPtrInvokers` caller addresses for `glGetError` and `glXGetFBConfigs` only for the test.

The probe checks:

- generated PFN caller `T` addresses lie in `libfex-GL-bridge.so`;
- allocator target and allocator unpacker lie in the companion;
- X11 unpackers lie in the companion;
- PFN and `glXGetFBConfigs` callback path work before close;
- wrapper mappings physically disappear after `dlclose`;
- resident caller/allocator/X11 executable addresses remain mapped;
- the callback path still executes after wrapper close, with diagnostic `GL_BRIDGE_MALLOC`, `XSync`, and `XDisplayString` receipts;
- retired wrapper ranges are reserved with `MAP_FIXED_NOREPLACE`;
- generation 2 wrapper base moves;
- the same native PFNs are reused;
- direct hash/type-stable caller `T` addresses are reused from the resident companion;
- generation-1 retained PFNs still execute after generation 2 closes.

## Promotion rule

Create GL source tranche 2 only after a post-Fix-4 build/role/ELF run and the moved-reload runtime are green. Keep all diagnostic hooks/workflows/scripts off the clean integration branch.
