# Per-library guest bridge helper promotion — 2026-08-14

## Result

The repeated experimental CMake wiring for process-resident guest companions has converged on one common `add_guest_bridge()` helper in the owned FEX research fork.

Exact product baseline for the helper validation lanes:

`f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`

The helper is now runtime-green across the three required discriminator libraries:

- CUDA retained generated `callback_member` callback;
- generalized Wayland retained listener;
- Vulkan dynamic PFN across physical wrapper close and moved reload.

This clears the build-system prerequisite gate recorded in `per-library-guest-bridge-build-contract-20260814.md`.

## Common helper contract exercised

The helper creates one ordinary unloadable guest wrapper plus one library-local process-resident companion:

```text
lib<name>-guest.so              ordinary unloadable wrapper
libfex-<name>-bridge.so         DF_1_NODELETE companion
```

For a helper-backed wrapper, the validated CMake behavior is:

- companion target created through the ordinary guest-library path;
- optional generated `-guest-bridge` dependency;
- library-specific dependency/include propagation;
- wrapper `DT_NEEDED` on the companion;
- wrapper `$ORIGIN` runpath so the installed sibling companion is discoverable without a global loader path;
- `DF_1_NODELETE` applied to the companion only;
- wrapper remains physically unloadable.

The runtime/role policy stays outside the CMake helper. Thunkgen decides caller/unpacker roles, and library-specific code decides semantic fixed callback families such as Vulkan X11 unpackers.

## CUDA common-helper gate

Owned FEX branch:

`diagnostic/cuda-common-bridge-helper-f3ab-20260814`

Workflow run:

`31792606593`

Head under test:

`2bfedafd870bc9932b314764b18381d2dbd1b6d3`

Both matrix arms completed successfully and emitted retained artifacts:

- `cuda-common-helper-local-31792606593`
- `cuda-common-helper-resident-31792606593`

The resident arm uses the common helper plus direct thunkgen bridge definitions/accessors. It preserves the established discriminator: generation 1 unloads, generation 2 moves, and the retained native registration invokes the generation-1 guest callback again only when the callback unpacker belongs to the resident companion.

## Wayland common-helper gate

Owned FEX branch:

`diagnostic/per-library-bridge-helper-f3ab-20260814`

Workflow run:

`31793198473`

Head under test:

`fcfcd6e5eb4862f397e1e2a2d9184e3ec20db87e`

Runtime receipt:

```text
WAYLAND_GEN1 add=0x7ffff7ebb830 trigger=0x7ffff7ebb820 ranges=6
WAYLAND_HOST_RETAIN trampoline=0x7ffff7e7f000 data=0x12345678 proxy=0x7fffffffb3d0
WAYLAND_TRIGGER1_RETURN count=1 value=41
WAYLAND_CLOSE1 add_mapped=0
RESERVED 0x7ffff7eb8000-0x7ffff7eba000
RESERVED 0x7ffff7eba000-0x7ffff7ebd000
RESERVED 0x7ffff7ebd000-0x7ffff7ebe000
RESERVED 0x7ffff7ebe000-0x7ffff7ebf000
RESERVED 0x7ffff7ebf000-0x7ffff7ec0000
RESERVED 0x7ffff7ec0000-0x7ffff7ec1000
WAYLAND_GEN2 add=0x7ffff7e3a830 trigger=0x7ffff7e3a820 moved=1
WAYLAND_TRIGGER2_ENTER retained-registration-only
WAYLAND_HOST_TRIGGER value=42 trampoline=0x7ffff7e7f000
WAYLAND_GUEST_CALLBACK count=2 value=42 data=0x12345678
WAYLAND_TRIGGER2_RETURN count=2 value=42
WAYLAND_HELPER_OK
```

Dynamic-link receipt:

```text
wrapper NEEDED  libfex-wayland-client-bridge.so
wrapper RUNPATH $ORIGIN:.../guest:
bridge FLAGS_1  NODELETE
```

Binary-size receipt for this research build:

```text
text   data bss   dec   file
21697  1008   8 22713  libwayland-client-guest.so
10713   872   8 11593  libfex-wayland-client-bridge.so
```

The same retained trampoline address survives physical wrapper unload and forced moved reload.

## Vulkan common-helper gate

Owned FEX branch:

`diagnostic/per-library-bridge-helper-f3ab-20260814`

Workflow run:

`31793272172`

Head under test:

`d2438ca4d74eb22d562f28b42476e07a3b8f6b64`

The Vulkan integration uses generated typed resident caller accessors for dynamic PFNs. The three fixed persistent X11 unpackers remain explicit Vulkan companion ownership because they are semantic custom callback families rather than ordinary generated API callback parameters.

Dynamic-link receipt:

```text
wrapper NEEDED  libfex-vulkan-bridge.so
wrapper RUNPATH $ORIGIN:.../guest:
bridge FLAGS_1  NODELETE
```

Close arm:

```text
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7e60380
PROBE tracked-path=.../libvulkan.so.1 mappings=5 anchor=0x7ffff7eb1440
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
PROBE about-to-call-stale-pfn=0x7ffff76c80f4
PROBE return where=after-real-close result=0 version=0x403113 maps=11
exit=0
```

Moved-reload arm:

```text
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7e60380
PROBE tracked-path=.../libvulkan.so.1 mappings=5 anchor=0x7ffff7eb1440
PROBE reserved-old-generation-ranges=5
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7e60380
PROBE tracked-path=.../libvulkan.so.1 mappings=5 anchor=0x7ffff7680440
PROBE acquired generation=2 ... old-gipa=0x7ffff7eb1440 new-gipa=0x7ffff7680440 old-pfn=0x7ffff76c80f4 new-pfn=0x7ffff76c80f4 same-pfn=1 maps=16
PROBE return where=after-reload-new-pfn result=0 version=0x403113 maps=16
exit=0
```

The exact wrapper generation moves while the native PFN and selected resident host invoker remain stable.

## Promotion decision

The common per-library guest-bridge helper is now the preferred build-system cut for the resident-companion design.

The helper itself carries no callback-lifetime policy. Its job is narrowly mechanical: create/install the companion, connect generated dependencies, keep the wrapper unloadable, make the sibling companion discoverable, and pin only the companion.

The historical whole-wrapper `NODELETE` candidate remains useful as a containment reference. The helper-backed resident companion preserves logical wrapper unload/reset while protecting escaped executable adapters.

## Next gate

Exercise the installed GuestThunks layout instead of manually copying wrapper/companion files into a test rootfs:

1. install a helper-backed pair through the normal GuestLibs install path;
2. verify wrapper and companion land together in `GuestThunks` (and later `GuestThunks_32` where supported);
3. launch FEX using the installed thunk tree without an experiment-only library path;
4. rerun at least the Vulkan moved-reload PFN discriminator;
5. record binary/RSS/PSS/relocation cost once installed discovery is proven.
