# Generated Vulkan split resident bridge — forced moved wrapper reload

Date: 2026-08-14

## Result

The thunkgen-produced resident Vulkan bridge survives a **forced moved physical reload** of the ordinary Vulkan guest wrapper without changing the native Vulkan PFN or the resident bridge target.

Generation 1 of `libvulkan-guest.so` is physically unloaded. Every mapping belonging to that exact guest-wrapper file is then reserved with `PROT_NONE | MAP_FIXED_NOREPLACE`, forcing generation 2 to load elsewhere. The native Vulkan PFN remains bit-identical, the wrapper GIPA address moves, and both the newly reacquired PFN and the old retained PFN continue to call native ARM64 Lavapipe through the same process-resident bridge.

No FEX core lifetime/rebind code is changed.

## Owned-fork carrier

Repository: `teamleaderleo/FEX`

Branch: `diagnostic/generated-vulkan-split-bridge`

Reviewed stock base: `71afe476751deac24adabd1adb575fd2337b6e0a`

Workflow head:

```text
3425e3ddd58ed348fa3d52a0c93e5acf4a780db6
```

Workflow: `.github/workflows/generated-vulkan-split-moved-reload-arm64.yml`

Run: `31778518692`

Job: `94698999515`

Artifact: `generated-vulkan-split-moved-31778518692`

Artifact ID: `9210868629`

Artifact zip SHA-256:

```text
ca093e4a24ec91b0f415a9cae947b65001c30457cace41e5adab745c6e809cfa
```

## Harness correction retained

An earlier moved-reload run matched any `/proc/self/maps` pathname containing `libvulkan.so.1`. That accidentally included the persistent native host Vulkan library as well as the x86 guest wrapper, so its attempt to reserve a still-live native mapping correctly failed with `EEXIST`.

The evidentiary run fixes that harness. It first finds the exact mapped file containing generation-1 guest `vkGetInstanceProcAddr`, then reserves only mappings whose full pathname matches that guest-wrapper file.

This also reinforces the existing lifetime map: the native Vulkan implementation remains process-resident independently of guest-wrapper physical unload.

## Generation 1

FEX publishes the real native Vulkan PFN to a resident bridge address:

```text
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7e71390
```

Generation 1:

```text
WRAPPER_PATH .../rootfs-moved/usr/lib/x86_64-linux-gnu/libvulkan.so.1
GEN1 gipa=0x7ffff7ea23a0 H=0x7ffff76c80f4 version=4206867 ranges=5 bridge_maps=5
```

After final close, generation-1 GIPA is unmapped while the retained H remains callable:

```text
GEN1_CLOSED retained_H_ok=1
```

The five former wrapper mappings are then successfully reserved:

```text
RESERVED 0x7ffff7e75000-0x7ffff7e82000
RESERVED 0x7ffff7e82000-0x7ffff7eae000
RESERVED 0x7ffff7eae000-0x7ffff7ebf000
RESERVED 0x7ffff7ebf000-0x7ffff7ec0000
RESERVED 0x7ffff7ec0000-0x7ffff7ec1000
```

## Generation 2

The wrapper must move because its former mappings are unavailable:

```text
GEN2 gipa=0x7ffff76713a0 H=0x7ffff76c80f4 moved=1 same_H=1 bridge_maps=5
```

So:

```text
gipa1 = 0x7ffff7ea23a0
gipa2 = 0x7ffff76713a0
H1    = 0x7ffff76c80f4
H2    = 0x7ffff76c80f4
```

The newly reacquired generation-2 PFN succeeds:

```text
GEN2_CALL_OK version=4206867
```

The old retained H value also remains usable after the moved reload:

```text
OLD_H_AFTER_MOVED_RELOAD_OK version=4206867
```

Final marker:

```text
GENERATED_VULKAN_SPLIT_MOVED_RELOAD_OK
```

Process exit: `0`.

## Meaning

This is the lifecycle property the split bridge was intended to create:

```text
wrapper generation 1 T_wrapper1  -> unload
resident bridge T_bridge         -> unchanged
wrapper generation 2 T_wrapper2  -> different address
native H                          -> unchanged
```

FEX does not need to retire and recreate the dynamic H dispatch merely because the ordinary wrapper generation moves. H already targets process-lived bridge code rather than generation-owned wrapper code.

The result removes several complications from the dynamic-PFN lifetime path when physical wrapper unload is desired:

- no generation-specific H->wrapper-T target to revoke/rebind;
- no translated H path that must be invalidated merely because the wrapper moved;
- no check-to-use race between selecting the bridge and wrapper unmap, because the selected bridge remains executable;
- stale and newly reacquired raw H values naturally converge on the same process-lived adapter.

Library/API state can still have its own lifetime rules; this result is specifically about FEX-created escaped executable bridge state.

## Current generated split evidence

The same generated Vulkan sidecar now has three real runtime properties:

1. retained dynamic `vkEnumerateInstanceVersion` works after physical wrapper unload;
2. retained `vkGetPhysicalDeviceXlibPresentationSupportKHR` plus host->guest X11 callbacks work after physical wrapper unload;
3. forced moved wrapper reload keeps H stable and both old/new H use working while wrapper GIPA moves.

A separate build proof also shows thunkgen can emit the bridge signatures directly from `fex_gen_type<function-type>` without fake companion API functions.

## Remaining engineering

The design is now bottlenecked less by lifetime semantics and more by generator integration:

- generate all per-library indirect bridge signatures automatically from the ordinary thunk interface;
- publish a stable per-library name->resident-invoker table rather than hand-overriding selected Vulkan names;
- make generated callback-parameter registration obtain resident `CallbackUnpack` implementations rather than instantiating wrapper-local unpackers;
- carry library-specific custom callback helpers (for example Wayland's array relocation) in library-specific resident bridge code;
- audit compatibility identity before attempting process-global cross-library signature deduplication, because parameter annotations can affect host wrapper semantics beyond the textual C signature.

Whole-wrapper NODELETE remains the smaller near-term containment. The generated split bridge is now a demonstrated unload-preserving architecture rather than only a synthetic design.

All code and CI work stayed on owned repositories/forks. No upstream interaction occurred.
