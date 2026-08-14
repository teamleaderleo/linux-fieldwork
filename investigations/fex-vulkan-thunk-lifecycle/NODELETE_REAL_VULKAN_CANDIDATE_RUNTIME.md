# Clean NODELETE candidate — real Vulkan retained-PFN proof

## Candidate

Owned fork branch: `ci/nodelete-guest-thunk-policy-20260814`.

Source-only policy commit: `38db7b14...`.

The candidate changes only the generic guest-thunk build helper:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

There are no FEX core lifetime changes in this candidate.

A later branch commit adds only the hosted validation workflow; the tested workflow head is `3d5f90ad8faa4b5f77ba03c3faa7fd09f5e3e653`.

## Hosted real-Vulkan test

Run `31772712092`, job `94681742236`, artifact `9208739672` completed successfully on hosted ARM64.

The workflow:

1. validates native ARM64 Lavapipe with `vulkaninfo --summary`;
2. builds the real FEX runtime and real `vulkan-host-64` thunk;
3. builds the real generated x86-64 `libvulkan-guest.so` from the candidate source policy;
4. verifies the guest wrapper still has `SONAME libvulkan.so.1` and now carries `FLAGS_1: NODELETE`;
5. creates an amd64 rootfs and an x86 lifecycle probe;
6. obtains a dynamic Vulkan PFN through `vkGetInstanceProcAddr(NULL, "vkEnumerateInstanceVersion")`;
7. calls that PFN, closes the Vulkan guest handle with ordinary `dlclose()`, then calls the exact same retained PFN again;
8. reopens `libvulkan.so.1` and checks the guest `vkGetInstanceProcAddr` address remains stable.

The host side uses the actual ARM64 Lavapipe Vulkan driver through FEX's real Vulkan host thunk.

## Result

Before close:

```text
BEFORE_CLOSE gipa=0x7ffff7da2710 pfn=0xffff81456e20 result=0 version=4206831
MAP 0x7ffff7da2710 7ffff7d9e000-7ffff7da3000 r-xp ... /usr/lib/x86_64-linux-gnu/libvulkan.so.1
```

After ordinary `dlclose()` the generated guest wrapper remains executable-mapped:

```text
AFTER_DLCLOSE
MAP 0x7ffff7da2710 7ffff7d9e000-7ffff7da3000 r-xp ... /usr/lib/x86_64-linux-gnu/libvulkan.so.1
```

The exact same retained dynamic PFN still reaches the real host Vulkan implementation and returns the identical version successfully:

```text
AFTER_CLOSE_CALL pfn=0xffff81456e20 result=0 version=4206831
```

Reopening the guest Vulkan wrapper returns the same guest `vkGetInstanceProcAddr` address:

```text
REOPEN gipa_old=0x7ffff7da2710 gipa_new=0x7ffff7da2710
REAL_NODELETE_VULKAN_PFN_OK
```

The probe exits 0.

## Meaning

This is the product-sized H→T validation for the NODELETE containment candidate:

- real generated FEX Vulkan guest wrapper;
- real FEX Vulkan host thunk;
- real ARM64 Vulkan driver;
- dynamic native PFN bridged through `LinkAddressToFunction`;
- ordinary guest-side `dlclose()`;
- same retained PFN called successfully afterward;
- zero FEX core lifetime machinery.

Together with the synthetic full-pair NODELETE run, which directly preserves both retained H→T and host→guest callback directions after `dlclose()`, this closes the causal path from the source policy to a real Vulkan dynamic-entrypoint workload.

The remaining policy gates are build coverage rather than H→T mechanism uncertainty: the full 64-bit generated guest-thunk set and a representative real 32-bit guest thunk.

All code changes and CI work described here are on owned fork/investigation surfaces. No upstream FEX interaction occurred.
