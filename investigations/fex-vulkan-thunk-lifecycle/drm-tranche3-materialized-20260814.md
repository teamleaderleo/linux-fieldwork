# DRM clean source tranche 3 — 2026-08-14

## Clean source branch

`integration/per-library-resident-bridges-drm-f3ab-20260814`

Commit:

`1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a`

Commit message:

`Research: add DRM resident callback bridge`

Parent:

`c348a19d91219d4df6cdaa86839607565e001fa2`

The branch is exactly one commit ahead of GL tranche 2.

Exact source files changed:

```text
ThunkLibs/GuestLibs/CMakeLists.txt
ThunkLibs/libdrm/Guest.cpp
ThunkLibs/libdrm/libdrm_interface.cpp
ThunkLibs/libdrm_bridge/Guest.cpp
```

GitHub compare against `c348a19d91219d4df6cdaa86839607565e001fa2` reports exactly those four files:

- `ThunkLibs/GuestLibs/CMakeLists.txt`: +5 / -0
- `ThunkLibs/libdrm/Guest.cpp`: +4 / -0
- `ThunkLibs/libdrm/libdrm_interface.cpp`: +10 / -1
- `ThunkLibs/libdrm_bridge/Guest.cpp`: +5 / -0

No diagnostic workflow, probe, fake native library, runtime-only unpacker getter, transform script, or receipt is present in the source commit.

## Materialization gate

Diagnostic workflow:

`.github/workflows/materialize-drm-resident-bridge-tranche3.yml`

Workflow carrier commit:

`c7ac84144a8ea4fe649ba71785f40828c3157a81`

Run:

`31798887242`

Job:

`94761971930` (`build-and-materialize`)

Result:

`success`

The workflow checked out exact clean GL tranche-2 source `c348a19d91219d4df6cdaa86839607565e001fa2`, copied only the validated DRM transform into `/tmp`, applied it there, required the exact four-file source delta above, rebuilt the combined resident-thunk set, checked role and ELF boundaries, then created and pushed one source-only commit.

Materialization artifact:

- name: `materialized-drm-resident-tranche3-31798887242`
- ID: `9218560147`
- SHA-256: `a5b8301227922a49abbcd7ee792591c1f522bbd5cc8d13180068af6e5edbcbdb`

Artifact commit receipt:

```text
input-source:       c348a19d91219d4df6cdaa86839607565e001fa2
integration-parent: c348a19d91219d4df6cdaa86839607565e001fa2
integration-commit: 1e8b042e7d50335cdbf2b1b6bfd0c888296dd73a
```

Gate marker:

```text
COMBINED_TRANCHE3_BUILD_ELF_OK
```

## Combined host / guest build

The materializer rebuilt together:

Host side:

- `thunkgen`
- `GL-host-64`
- `vulkan-host-64`
- `cuda-host-64`
- `wayland-client-host-64`
- `drm-host-64`

Guest side:

- `GL-guest` + `GL_bridge-guest`
- `vulkan-guest` + `vulkan_bridge-guest`
- `cuda-guest` + `cuda_bridge-guest`
- `wayland-client-guest` + `wayland-client_bridge-guest`
- `drm-guest` + `drm_bridge-guest`

All passed in one build from exact clean GL tranche-2 source plus the four-file DRM delta.

## Role regression receipt

GL remains exactly:

- 736 generated `caller=1 unpacker=0` signatures;
- zero generated unpacker roles.

DRM is exactly three generated bridge signatures, all unpacker-only:

```text
FEX_BRIDGE_ROLE index=0 caller=0 unpacker=1 hash=0d6be1284d30cf3423bdc235dfe0a0664c1455f019f9c36ec90548960076e2dc void (int, unsigned int, unsigned int, unsigned int, unsigned int, void *)
FEX_BRIDGE_ROLE index=1 caller=0 unpacker=1 hash=716d5ac8035bbe770a43d44c4736033c9f2e18bfe3f83527f1bd46cf1e73552d void (int, unsigned long, unsigned long, unsigned long)
FEX_BRIDGE_ROLE index=2 caller=0 unpacker=1 hash=15faee5a1a2e831f6a79ab3295240b6a8b99f85f0d850f98e8c1d75cc3b5ad02 void (int, unsigned int, unsigned int, unsigned int, void *)
```

There are zero DRM caller roles.

## Combined ELF ownership receipt

Every ordinary wrapper remains unloadable and depends on its per-library companion with `$ORIGIN` present in RUNPATH:

- GL → `libfex-GL-bridge.so`
- Vulkan → `libfex-vulkan-bridge.so`
- CUDA → `libfex-cuda-bridge.so`
- Wayland → `libfex-wayland-client-bridge.so`
- DRM → `libfex-drm-bridge.so`

Every companion carries `FLAGS_1 NODELETE`.

No wrapper carries NODELETE.

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
  28585    664   8   29257    7249  guest/libdrm-guest.so
   1992    472   8    2472     9a8  guest/libfex-drm-bridge.so
```

## Runtime proof carried into promotion

Before materialization, the exact DRM direct candidate passed two independent runtime gates:

- run `31798196251`: direct callback_member generation, exactly three unpacker-only roles, common-helper packaging, and real pipe-fed `drmHandleEvent` callback execution;
- run `31798437804`: a generation-1 native host-retained callback trampoline executed after physical wrapper unload, all retired wrapper mappings were reserved, generation 2 moved, generation 2 did not re-register the callback, and the saved trampoline reached guest a second time.

The clean source tranche therefore contains only the validated DRM source delta.
