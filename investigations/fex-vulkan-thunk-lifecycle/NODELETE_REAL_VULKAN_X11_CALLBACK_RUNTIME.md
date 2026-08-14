# Clean NODELETE candidate — real Vulkan X11 callback proof

## Candidate

Owned fork branch `ci/nodelete-vulkan-x11-callback-20260814`, based on the clean NODELETE source candidate.

The only lifetime policy in FEX source remains the central shared guest-thunk linker option:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

No FEX core callback-lifetime code is changed.

## Hosted real-Vulkan callback test

Run `31773642361`, job `94684475544`, artifact `9209112705`, workflow head `4ec6f5b6d0d16032639e4334344c94210c61d1a2` completed successfully on hosted ARM64.

The workflow uses:

- native ARM64 Lavapipe;
- the real FEX runtime;
- real `vulkan-host-64`;
- the real generated x86-64 NODELETE `libvulkan-guest.so`;
- Xvfb on the ARM64 host;
- an x86 `libX11.so.6` stub that logs `XSync` and `XDisplayString` guest callbacks;
- an x86 Vulkan probe that creates a real Vulkan instance, enumerates a real physical device, obtains `vkGetPhysicalDeviceXlibPresentationSupportKHR`, and invokes that retained PFN before and after ordinary `dlclose(libvulkan.so.1)`.

A second guest Display token is used after close so FEX's persistent host-side `X11Manager` must create a new host display and therefore execute its retained guest X11 callbacks again. This directly exercises the source-audited callback lifetime class whose `GuestUnpacker` is compiled into `libvulkan-guest.so`.

The generated guest wrapper was verified as:

```text
SONAME: libvulkan.so.1
FLAGS_1: NODELETE
```

## Trace

Before close, the real Vulkan Xlib PFN causes the expected guest callbacks:

```text
PHYSICAL count=1 first=0xff6873b7b020 xlib_pfn=0x7ffff77c7ee4
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
Opening host-side X11 display: 0x12345000 -> 0xff6873b7c000
BEFORE_CLOSE_XLIB result=0
```

After ordinary guest-side `dlclose()` the exact same retained Vulkan PFN is invoked with a new guest Display token:

```text
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
Opening host-side X11 display: 0x12346000 -> 0xff6873b7e800
AFTER_CLOSE_XLIB result=0
REAL_NODELETE_VULKAN_X11_CALLBACK_OK
```

The probe exits `0`.

## Meaning

This is direct real-workload evidence for the host→guest half of the NODELETE containment:

1. a native host-side Vulkan/X11 helper retains FEX-generated host trampolines;
2. those trampolines depend on guest callback unpackers compiled into the generated Vulkan guest wrapper;
3. ordinary `dlclose()` is performed on the guest Vulkan handle;
4. the persistent host helper subsequently invokes the retained trampoline again;
5. the guest `XSync` and `XDisplayString` callbacks execute successfully after close because the NODELETE wrapper remains resident.

Together with the clean real retained-Vulkan-PFN test, the candidate now has real generated/runtime coverage for both observed cross-ISA lifetime directions:

- H→T dynamic Vulkan PFN retained across `dlclose()`;
- host→guest Vulkan X11 callback trampoline retained across `dlclose()`.

The synthetic full-pair test supplies the matched normal-unload failure control for both directions, while this run uses the actual Vulkan host thunk, generated guest wrapper, host driver, and persistent X11 manager path.

All edits and CI work described here are on owned fork/investigation surfaces. No upstream FEX interaction occurred.
