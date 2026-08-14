# Wayland generalized resident listener bridge — 2026-08-14

## Build/generalization result

Workflow run `31789560955` completed successfully on ARM64.

The transform moved every currently recognized **64-bit** typed Wayland listener allocation site behind one per-library resident allocator:

```
FEXWaylandAllocateResidentListener(callback, normalized_signature)
```

Transform receipt:

```
Wayland resident listener diagnostic applied to 41 typed allocation sites
```

The unloadable wrapper continues to own:

- protocol message parsing / normalization;
- listener table allocation and proxy bookkeeping;
- normal Wayland API entrypoints.

The resident companion owns the finite typed callback-unpacker dispatcher used when creating FEX host-to-guest trampolines.

## ELF boundary

The ordinary wrapper remains unloadable and has a dynamic dependency on the companion:

```
NEEDED libfex-wayland-client-bridge.so
SONAME libwayland-client.so.0.20.0
```

It has no `DF_1_NODELETE` flag.

The companion has:

```
SONAME libfex-wayland-client-bridge.so
FLAGS_1 NODELETE
```

## Size receipt

`size` on the two guest DSOs:

```
   text   data  bss    dec    hex  filename
  21368   1000    8  22376   5768  libwayland-client-guest.so
  10713    872    8  11593   2d49  libfex-wayland-client-bridge.so
```

This is the intended ownership granularity: the resident code is a small companion rather than the whole Wayland wrapper.

## Runtime regression using the full dispatcher

Workflow run `31790050047` completed successfully after the already-proven synchronous retained-listener carrier was switched from the narrow one-signature resident prototype to this full 41-signature dispatcher.

The discriminator remains unchanged:

### local wrapper-owned unpacker

- generation-1 callback value 41 succeeds while the wrapper is mapped;
- generation 1 physically unloads;
- old mappings are reserved;
- generation 2 loads at a different guest address;
- generation 2 does **not** re-register the listener;
- trigger-only invocation of the generation-1 retained host trampoline exits 139 before callback value 42 returns.

### generalized resident dispatcher

- the same generation-1 callback value 41 succeeds before unload;
- generation 1 physically unloads and generation 2 moves;
- generation 2 performs only the trigger call;
- the generation-1 retained host trampoline reaches the resident unpacker;
- guest callback value 42 returns successfully;
- process exits 0.

So the narrow causal proof survives the mechanical generalization across all 41 recognized 64-bit signature allocation sites.

## What this proves

Wayland now has both:

1. a causal moved-reload retained-registration-only lifetime A/B; and
2. a compiling/linking per-library resident dispatcher covering the complete currently recognized 64-bit listener signature table, with the known-good `"u"` path revalidated through that generalized dispatcher.

This supports the per-library/per-escaped-family model without pinning the whole Wayland wrapper.

## Remaining Wayland scope

The special `wl_array` callback relocation path used for 32-bit guests is still separate. Do not treat these 64-bit results as validation of 32-bit `a` / `iia` / `uoa` callback relocation semantics.

A future 32-bit gate should keep the same ownership boundary but move the special resident unpacker that performs guest-stack `wl_array` relocation rather than substituting the ordinary typed `CallbackUnpack` path.
