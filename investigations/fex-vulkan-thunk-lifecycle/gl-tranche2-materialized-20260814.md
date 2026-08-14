# GL clean source tranche 2 — 2026-08-14

## Clean source branch

`integration/per-library-resident-bridges-gl-f3ab-20260814`

Commit:

`c348a19d91219d4df6cdaa86839607565e001fa2`

Commit message:

`Research: add GL resident guest bridge`

Parent:

`48e28a2ce9da1334feb8d7b77dbade66efa24be2`

The branch is exactly one commit ahead of tranche 1 and has no other ancestry change.

Exact source files changed:

```text
ThunkLibs/GuestLibs/CMakeLists.txt
ThunkLibs/libGL/libGL_Guest.cpp
ThunkLibs/libGL_bridge/Guest.cpp
```

GitHub compare against `48e28a2ce9da1334feb8d7b77dbade66efa24be2` reports exactly those three files:

- `ThunkLibs/GuestLibs/CMakeLists.txt`: +6 / -0
- `ThunkLibs/libGL/libGL_Guest.cpp`: +11 / -8
- `ThunkLibs/libGL_bridge/Guest.cpp`: +32 / -0

No diagnostic script, workflow, runtime hook, or generated receipt is present in the source commit.

## Materialization gate

Diagnostic workflow:

`.github/workflows/materialize-gl-resident-bridge-tranche2.yml`

Workflow carrier commit:

`cd18087ecc04bbf52e42afa6fca583eb872fe733`

Run:

`31797731729`

Job:

`94758417368` (`build-and-materialize`)

Result:

`success`

The workflow checked out exact clean tranche-1 source `48e28a2ce9da1334feb8d7b77dbade66efa24be2`, copied only the already-validated GL transform into `/tmp`, applied it there, required an exact three-file source diff, built the combined resident-thunk set, checked all ELF boundaries, then created and pushed the source-only commit.

Materialization artifact:

- name: `materialized-gl-resident-tranche2-31797731729`
- ID: `9218133266`
- SHA-256: `dfd02ea574f8abd0805049da2a00fda5101529165f4b23bafb88fcca6b4ee3fc`

Artifact commit receipt:

```text
input-source:       48e28a2ce9da1334feb8d7b77dbade66efa24be2
integration-parent: 48e28a2ce9da1334feb8d7b77dbade66efa24be2
integration-commit: c348a19d91219d4df6cdaa86839607565e001fa2
```

Gate marker:

```text
COMBINED_TRANCHE2_BUILD_ELF_OK
```

## Combined host / guest build

The materializer rebuilt together:

Host side:

- `thunkgen`
- `GL-host-64`
- `vulkan-host-64`
- `cuda-host-64`
- `wayland-client-host-64`

Guest side:

- `GL-guest` + `GL_bridge-guest`
- `vulkan-guest` + `vulkan_bridge-guest`
- `cuda-guest` + `cuda_bridge-guest`
- `wayland-client-guest` + `wayland-client_bridge-guest`

All passed in one build from the exact clean tranche-1 source plus the three-file GL delta.

## GL direct-role receipt

The direct generated GL bridge contains:

- `736` `caller=1 unpacker=0` signatures;
- `0` signatures containing `unpacker=1`.

The allocator and fixed X11 unpackers remain GL-semantic custom resident code.

## Combined ELF ownership receipt

Every ordinary wrapper remains unloadable and depends on its per-library companion with `$ORIGIN` present in RUNPATH:

- GL → `libfex-GL-bridge.so`
- Vulkan → `libfex-vulkan-bridge.so`
- CUDA → `libfex-cuda-bridge.so`
- Wayland → `libfex-wayland-client-bridge.so`

Every companion carries `FLAGS_1 NODELETE`.

No wrapper carries `NODELETE`.

## Combined size receipt

```text
   text   data bss     dec     hex  filename
 997597   6800  88 1004485   f53c5  guest/libGL-guest.so
 244425    608   8  245041   3bd31  guest/libfex-GL-bridge.so
 311789   4680  88  316557   4d48d  guest/libvulkan-guest.so
 156407    592   8  157007   2654f  guest/libfex-vulkan-bridge.so
 196742   3784  88  200614   30fa6  guest/libcuda-guest.so
 121373    576   8  121957   1dc65  guest/libfex-cuda-bridge.so
  21376   1000   8   22384    5770  guest/libwayland-client-guest.so
  10713    872   8   11593    2d49  guest/libfex-wayland-client-bridge.so
```

## Runtime proof carried into promotion

Before materialization, the exact GL source transform passed real moved-reload lifetime run `31797129095` with exit 0. The wrapper physically unmapped, retired ranges were reserved, generation 2 moved, native PFNs were reused, resident caller `T` addresses were reused, and retained generation-1 GLX callback execution succeeded after generation 2 closed.

The clean source tranche therefore carries only code that already passed both the independent runtime lifetime gate and this combined source build/ELF gate.
