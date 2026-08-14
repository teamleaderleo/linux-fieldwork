# Wayland 32-bit resident `wl_array` compatibility — 2026-08-14

## Source and goal

Clean source under test:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

Diagnostic branch:

`diagnostic/wayland32-resident-array-compat-20260814`

The compatibility question is narrow: keep the existing 32-bit host-side `CallGuestPtrWithWaylandArray` packer and prove it interoperates with the already-resident guest listener unpacker in `libfex-wayland-client-bridge.so`.

This gate does not introduce another resident guest executable family.

## First run — negative result before 32-bit source compilation

Workflow:

`.github/workflows/wayland32-resident-array-compat.yml`

Carrier head:

`3bfa8d5cc275db94558579c65f1d8433be72755e`

Run:

`31799488314`

Job:

`94763840019` (`wayland32-array`)

Result:

`failure`

Artifact:

- name: `wayland32-resident-array-compat-31799488314`
- ID: `9218713033`
- SHA-256: `ec3afdb1a0356a1f37fd8e5c31fdb8a57df8353633cb81475a966d46794211ba`

Exact clean-source provenance passed before the runtime-only diagnostic hook was added.

The job then stopped during the main host CMake configure, before `wayland-client-host-32`, the 32-bit guest wrapper, or the resident companion compiled. The artifact contains `cmake-host.log`, `pre-patch-product-source-diff.txt`, and `runtime-only.diff`; there is no host build log or guest CMake/build log.

Exact configure failure:

```text
CMake Error at /usr/local/share/cmake-3.31/Modules/FindPackageHandleStandardArgs.cmake:233 (message):
  Could NOT find OpenGL (missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY
  OPENGL_INCLUDE_DIR)
Call Stack (most recent call first):
  /usr/local/share/cmake-3.31/Modules/FindPackageHandleStandardArgs.cmake:603 (_FPHSA_FAILURE_MESSAGE)
  /usr/local/share/cmake-3.31/Modules/FindOpenGL.cmake:579 (FIND_PACKAGE_HANDLE_STANDARD_ARGS)
  ThunkLibs/HostLibs/CMakeLists.txt:168 (find_package)

-- Configuring incomplete, errors occurred!
```

## Classification

This is a diagnostic workflow dependency failure. The workflow installed `libwayland-dev` but omitted `libgl-dev`; the top-level FEX host configure traverses the thunk host CMake and requires OpenGL even when the requested build target is the 32-bit Wayland host thunk.

No conclusion about 32-bit Wayland source compatibility, ELF32 packaging, host `wl_array` relocation, resident unpacker execution, or callback correctness follows from this run.

## Fix and next gate

Add `libgl-dev` to the diagnostic workflow dependency set only. Keep product source and the test logic unchanged.

The next run must still prove, in order:

1. 32-bit Wayland host thunk builds from the repository host configuration;
2. `libwayland-client-guest.so` and `libfex-wayland-client-bridge.so` build as ELF32;
3. wrapper stays unloadable with `NEEDED libfex-wayland-client-bridge.so` and `$ORIGIN`;
4. companion remains NODELETE;
5. runtime-only `listener_a` unpacker address lies inside the resident companion;
6. a fake native one-event interface with signature `"a"` drives the real 32-bit host `CallGuestPtrWithWaylandArray` path;
7. the i386 guest callback receives a 12-byte guest `wl_array` with `size=7`, `alloc=9`, and `data=NULL`;
8. callback exits successfully with the resident guest unpacker.
