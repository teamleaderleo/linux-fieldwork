# Split resident Vulkan/X11 callback bridge result

## Result

**Success.** On hosted ARM64, pristine FEX main `71afe476751deac24adabd1adb575fd2337b6e0a` successfully executed a retained real Vulkan Xlib PFN after the ordinary guest Vulkan wrapper had physically unloaded, while the host-to-guest callback unpackers lived in a separate process-resident guest bridge DSO.

GitHub Actions run: `teamleaderleo/FEX` run `31778519424`, job `94699001615`.

FEX experiment branch: `ci/split-vulkan-bridge-x11-callback-20260814`.

The workflow completed successfully end-to-end.

## What was resident and what was unloadable

The experiment intentionally did **not** mark `libvulkan-guest.so` `NODELETE`.

The workflow verified the ordinary Vulkan wrapper's dynamic section did not contain `DF_1_NODELETE` and printed:

```text
SPLIT_X11_WRAPPER_REMAINS_UNLOADABLE
```

A separate x86-64 guest DSO, `libfex-vulkan-bridge.so.1`, was linked with `-z nodelete`. Its dynamic section contained:

```text
FLAGS_1 Flags: NODELETE
```

That small resident DSO exported four addresses:

- the generated guest-to-host `CallHostFunction` adapter for `vkGetPhysicalDeviceXlibPresentationSupportKHR`;
- `CallbackUnpack<decltype(XSync)>::Unpack`;
- `CallbackUnpack<decltype(XGetVisualInfo)>::Unpack`;
- `CallbackUnpack<decltype(XDisplayString)>::Unpack`.

The actual guest X11 callback targets remained in an ordinary guest `libX11.so.6` stub, not in the resident bridge.

## Exact runtime trace

The resident bridge initialized at stable guest addresses:

```text
SPLIT_X11_BRIDGE_READY pfn=0x7ffff7e43270 xsync=0x7ffff7e43230 xgetvisual=0x7ffff7e432e0 xdisplay=0x7ffff7e43250
```

A real Vulkan instance was created through the FEX Vulkan thunk:

```text
PROBE create-instance result=0 instance=0xfff4d1851000 vulkan-maps=5 bridge-maps=5 x11-maps=5
```

The real native host PFN for `vkGetPhysicalDeviceXlibPresentationSupportKHR` was linked to the resident guest adapter:

```text
SPLIT_X11_PFN_LINK H=0x7ffff77c7ee4 T=0x7ffff7e43270
PROBE acquired xlib-pfn=0x7ffff77c7ee4 physical=0xfff4d197b020 vulkan-maps=5 bridge-maps=5 x11-maps=5
```

Before close, the PFN caused the host Vulkan thunk to call back through FEX into the guest X11 targets:

```text
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
Opening host-side X11 display: 0x12345000 -> 0xfff4d197c000
PROBE before-close-xlib result=0
```

Then the guest Vulkan wrapper was physically removed while the resident bridge and guest X11 target library remained mapped:

```text
PROBE after-dlclose vulkan-maps=0 bridge-maps=5 x11-maps=5 retained-xlib-pfn=0x7ffff77c7ee4
```

The same retained native Vulkan PFN was called again **after the guest Vulkan wrapper had zero mappings**:

```text
PROBE AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
Opening host-side X11 display: 0x12346000 -> 0xfff4d197e800
PROBE after-close-xlib result=0 vulkan-maps=0 bridge-maps=5 x11-maps=5
SPLIT_VULKAN_X11_CALLBACK_PASS
```

The workflow's final assertion printed:

```text
SPLIT_VULKAN_X11_CALLBACK_PHYSICAL_UNLOAD_OK
```

The guest process exited 0.

## What this proves

For this real Vulkan/X11 path, both executable bridge directions can outlive `libvulkan-guest.so` without pinning the entire Vulkan wrapper:

```text
native Vulkan H
    -> resident guest CallHostFunction<signature> adapter
    -> host Vulkan thunk
    -> host X11Manager / FEX host callback trampoline
    -> resident guest CallbackUnpack<signature>::Unpack
    -> ordinary guest libX11 callback target
```

The guest Vulkan wrapper is absent during the second call.

This is strong evidence that the tested generated adapters are not semantically owned by the Vulkan wrapper generation. The wrapper currently acts as the place where those adapters happen to be instantiated and the place that supplies their addresses to FEX. Their useful lifetime is broader.

The result also rules out a weaker interpretation of the earlier whole-wrapper `NODELETE` control. Callback survival does **not** require the whole Vulkan guest image to remain resident. Keeping only the immutable bridge executable code resident is sufficient for the tested path.

## What this does not prove

This does not make arbitrary callback targets immortal.

The experiment deliberately kept the actual guest X11 target library mapped. A callback target whose own owning DSO unloads still requires revocation, generation tracking, or another lifetime policy.

It also does not prove that every Vulkan bridge is stateless. Per-instance/device data, custom repacking code with wrapper-local state, TLS, or other generation-dependent machinery must be classified separately.

## Architectural implication

The tested ownership split is now experimentally viable in both directions:

```text
process/FEX-thunk-runtime lifetime:
    immutable generated signature bridge executable code

ordinary library lifetime:
    libvulkan-guest.so
    constructors/destructors
    Vulkan wrapper state
    real loader-visible unload/reload

callback-target owner lifetime:
    guest libX11 target functions
```

This strengthens the case for a process-owned guest bridge runtime rather than whole-wrapper residency or immediate implementation of the full physical-unload reclamation protocol for immutable signature adapters.
