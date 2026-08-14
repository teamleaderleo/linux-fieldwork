# Real generated Vulkan — split resident bridge X11 callback runtime

Date: 2026-08-14

## Result

The split resident bridge now has real generated-Vulkan coverage for the **host→guest callback direction** as well as dynamic native PFNs.

Under stock FEX core, `libvulkan.so.1` remains an ordinary unloadable guest wrapper while `libfex-vulkan-bridge.so` remains resident and owns the fixed callback unpackers whose addresses escape wrapper lifetime.

Reviewed stock FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier commit: `af024a87947322e13c1ed18134cd9b039ffbdec7`.

Workflow run: `31777195632`.

Artifact: `real-vulkan-split-x11-callback-v2-31777195632`.

Artifact digest:

```text
sha256:c6e989fba7941814b47f0a34675679f9a55d14cf81820a9384ee6ec450b8ed55
```

No upstream FEX interaction was made.

## Exact wrapper ownership check

The probe resolves guest `vkGetInstanceProcAddr`, finds the exact `/proc/self/maps` pathname that owns that guest address, and tracks only that exact path.

Before close:

```text
WRAPPER_PATH /home/runner/work/FEX/FEX/rootfs/usr/lib/x86_64-linux-gnu/libvulkan.so.1
MAPS_BEFORE exact_wrapper=5 bridge=5
```

The resident bridge has five mappings and the actual generated Vulkan wrapper has five mappings.

## Real Vulkan/X11 setup before close

The guest wrapper obtains real native Vulkan functions and links them to resident adapters:

```text
Linking address 0x7ffff77c7bd0 to resident host invoker 0x7ffff7e79c80
Linking address 0x7ffff76c4d60 to resident host invoker 0x7ffff7e79d30
Linking address 0x7ffff77c7ee4 to resident host invoker 0x7ffff7e848a0
```

A real Vulkan instance is created with Xlib surface support:

```text
CREATE_INSTANCE result=0 instance=0xff4187451000
PHYSICAL count=1 first=0xff418757b000 xlib_pfn=0x7ffff77c7ee4
```

The real retained Vulkan Xlib PFN invokes guest X11 targets before close:

```text
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
Opening host-side X11 display: 0x12345000 -> 0xff418757c000
BEFORE_CLOSE_XLIB result=0
```

The fixed callback unpackers used to perform those host→guest transitions live in `libfex-vulkan-bridge.so`, not the unloadable Vulkan wrapper.

## Wrapper physically disappears

After ordinary guest `dlclose(libvulkan.so.1)`:

```text
MAPS_AFTER exact_wrapper=0 bridge=5
```

The exact guest wrapper path has no mappings left. The resident bridge remains mapped.

This is the ownership condition the earlier loose-substring probe failed to distinguish; that first run counted unrelated Vulkan mappings and aborted before the post-close callback.

## Retained callback works after wrapper physical unload

Only after the exact wrapper mapping count is confirmed zero does the probe call the previously retained real Vulkan Xlib PFN again with a fresh guest Display token:

```text
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
Opening host-side X11 display: 0x12346000 -> 0xff418757e800
AFTER_CLOSE_XLIB result=0
REAL_SPLIT_VULKAN_X11_CALLBACK_OK
```

The process exits `0`.

## Meaning

This closes the real generated-Vulkan callback-direction gate for the split architecture.

The same generated wrapper split now has direct runtime evidence for both bridge classes:

### Dynamic native PFN → guest adapter

`REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md` proves:

- the real Vulkan wrapper physically unloads;
- a previously advertised native Vulkan PFN remains callable because H targets resident signature glue;
- forced moved wrapper reload succeeds under stock FEX core.

### Host → guest callback

This receipt proves:

- the real Vulkan wrapper physically unloads;
- retained Vulkan host-side callback machinery remains usable;
- the fixed guest unpackers live in the resident bridge;
- actual guest X11 targets continue to execute after wrapper close.

Together with `FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`, the split resident bridge now covers:

- generation handoff;
- wrapper physical unload/reset;
- retained H execution;
- retained host→guest callbacks;
- the exact selected-before-wrapper-unmap race.

## Architecture implication

The Vulkan-specific split prototype is now complete enough to justify generalizing the mechanism in thunk generation/build logic.

The long-term implementation direction is:

```text
per-bitness process-resident guest bridge runtime
    deduplicated signature-specific CallHostFunction adapters
    deduplicated fixed CallbackUnpack functions
    process-long executable ownership

unloadable library wrapper DSO
    constructors
    mutable/library-specific state
    generated pack/repack wrappers
    registration calls referencing resident bridge addresses
```

A policy layer may still mark advertised H entries ACTIVE/REVOKED if stale logical API use should be rejected. That policy no longer needs to make executable wrapper reclamation depend on invalidating an already-selected wrapper-owned target.

All code in this experiment is diagnostic/research code on owned surfaces. Any upstream implementation must be independently derived and written by a human in compliance with FEX policy.