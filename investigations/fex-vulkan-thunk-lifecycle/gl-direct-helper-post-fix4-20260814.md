# GL direct-helper post-Fix-4 gates — 2026-08-14

## Exact source under test

FEX diagnostic branch:

`diagnostic/gl-direct-helper-f3ab-20260814`

Post-Fix-4 head:

`0dc102a565320d28a0b30a1f1bd53b9c5f9a799d`

Exact product base remains:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

Fix 4 adds the FEX-owned GL local include directory to the resident companion through the already-validated common helper:

```cmake
INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/../libGL"
```

This follows the same helper path already used by the CUDA resident companion.

## Build / role / ELF gate — GREEN

GitHub Actions run:

`31797129061`

Job:

`94756564708` (`gl-build`)

Head:

`0dc102a565320d28a0b30a1f1bd53b9c5f9a799d`

Result:

`success`

The run passed, in order:

1. exact-product provenance against `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`;
2. direct thunkgen + role + common helper + GL transform application;
3. hardened transformed-source audit;
4. host `thunkgen` build;
5. x86_64 `GL-guest` and `GL_bridge-guest` build;
6. direct role gate;
7. ELF ownership/boundary gate;
8. artifact upload.

The resident companion compile line contains the expected GL-local include path:

`-I.../ThunkLibs/GuestLibs/../libGL`

### Direct generator role receipt

Generated `thunkgen_bridge_libGL.inl` contains exactly:

- `736` lines with `caller=1 unpacker=0`;
- `0` lines containing `unpacker=1`.

This keeps GL's direct generated portion caller-only. Fixed X11 and allocator unpackers remain library-semantic custom resident code rather than bogus generated unpacker roles.

### ELF receipt

`guest/libGL-guest.so`:

- `NEEDED libfex-GL-bridge.so`;
- `RUNPATH` contains `$ORIGIN`;
- no `FLAGS_1 NODELETE` tag.

`guest/libfex-GL-bridge.so`:

- `SONAME libfex-GL-bridge.so`;
- `FLAGS_1 NODELETE`.

Resident GL-specific exports present in the companion:

- `FEXGLBridgeMalloc`
- `fex_gl_bridge_malloc_unpacker`
- `fex_gl_bridge_xsync_unpacker`
- `fex_gl_bridge_xgetvisualinfo_unpacker`
- `fex_gl_bridge_xdisplaystring_unpacker`

The symbol receipt gives these companion addresses:

- `FEXGLBridgeMalloc`: `0x1f1b0`
- `fex_gl_bridge_malloc_unpacker`: `0x1f1c0`
- `fex_gl_bridge_xsync_unpacker`: `0x1f1d0`
- `fex_gl_bridge_xgetvisualinfo_unpacker`: `0x1f1e0`
- `fex_gl_bridge_xdisplaystring_unpacker`: `0x1f1f0`

### Size receipt

`size` output:

```text
   text    data     bss     dec     hex  filename
 997597    6800      88 1004485   f53c5  guest/libGL-guest.so
 244425     608       8  245041   3bd31  guest/libfex-GL-bridge.so
```

The process-resident executable companion is therefore about 245 KiB by this `size` accounting, while the ordinary ~1.00 MiB guest wrapper remains unloadable.

### Build artifact

Artifact name:

`gl-direct-helper-build-31797129061`

Artifact ID:

`9217854534`

Artifact SHA-256:

`dad510cb15817d9fc4e13cc2e607559a9fc906135daac8a336183eace4658e20`

Artifact includes:

- generated bridge/accessor output;
- role markers;
- wrapper/companion dynamic sections;
- companion symbol table;
- binary size receipt;
- transform output and exact product diff;
- CMake/build logs.

The exact green `product.diff` confirms the GL promotion delta consists of:

- direct generated accessor include in `libGL_Guest.cpp`;
- `HostPtrInvokers` using `FEXGetResidentCallerForHostFunction`;
- removal of wrapper-local `malloc_wrapper` executable code;
- resident allocator target + resident allocator unpacker;
- resident fixed `XSync`, `XGetVisualInfo`, and `XDisplayString` unpackers;
- new `ThunkLibs/libGL_bridge/Guest.cpp`;
- one GL `add_guest_bridge(...)` call using the common helper and `INCLUDE_DIRS`.

Generator/helper hunks present in the diagnostic artifact are already in clean integration tranche 1 and must not be duplicated in tranche 2.

## Pre-Fix-4 runtime run — negative receipt

The earlier moved-reload runtime run was already in flight when Fix 4 landed:

- run `31796930801`;
- job `94755951349`;
- artifact ID `9217825959`;
- artifact SHA-256 `627eec5b82b2750cc2db5a7986c6e528fd59a4bbea20000e12a628235efb9b54`.

It built the FEX runtime and GL host thunk, then failed building the guest resident bridge at the same pre-Fix-4 missing-header error:

`glcorearb.h: No such file or directory`

It never reached probe construction or runtime execution. Preserve it as an include-path build failure only.

## Post-Fix-4 moved-reload runtime gate

Relevant run:

`31797129095`

Job:

`94756564770` (`gl-runtime`)

Head:

`0dc102a565320d28a0b30a1f1bd53b9c5f9a799d`

At the latest observation it had passed provenance and runtime-only transform audit and was compiling the FEX runtime, GL host thunk, and direct guest pair.

Promotion remains blocked until this exact run, or a descendant carrying identical source transforms, proves the moved-reload PFN + retained callback lifetime gate green.
