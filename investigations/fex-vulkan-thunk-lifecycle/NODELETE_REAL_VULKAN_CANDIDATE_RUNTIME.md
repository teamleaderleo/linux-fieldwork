# Clean NODELETE candidate — real Vulkan retained-PFN proof

## Candidate

Owned fork branch: `ci/nodelete-guest-thunk-policy-20260814`.

The candidate changes only the generic guest-thunk build helper:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

There are no FEX core lifetime changes in this candidate.

The branch also carries hosted validation workflows. The latest repeated-lifetime stress head is `ef096e4e1fe06f624e04267561266e86391462d0`.

## First hosted real-Vulkan test

Run `31772712092`, job `94681742236`, artifact `9208784724` completed successfully on hosted ARM64.

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

### First-run result

Before close:

```text
BEFORE_CLOSE gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 result=0 version=4206867
MAP 0x7ffff7ea22b0 7ffff7e82000-7ffff7eae000 r-xp ... /usr/lib/x86_64-linux-gnu/libvulkan.so.1
```

After ordinary `dlclose()` the generated guest wrapper remains executable-mapped:

```text
AFTER_DLCLOSE
MAP 0x7ffff7ea22b0 7ffff7e82000-7ffff7eae000 r-xp ... /usr/lib/x86_64-linux-gnu/libvulkan.so.1
```

The exact same retained dynamic PFN still reaches the real host Vulkan implementation and returns the identical version successfully:

```text
AFTER_CLOSE_CALL pfn=0x7ffff76c80f4 result=0 version=4206867
```

Reopening the guest Vulkan wrapper returns the same guest `vkGetInstanceProcAddr` address, and the probe exits 0.

## 256-cycle close/reopen stress

A stronger follow-up run `31775336527`, job `94689504538`, artifact `9209731372`, head `ef096e4e1fe06f624e04267561266e86391462d0` completed successfully on hosted ARM64.

It uses the same real components:

- generated x86-64 Vulkan guest thunk with `DF_1_NODELETE`;
- FEX runtime and Vulkan host thunk from the owned candidate branch;
- ARM64 Lavapipe Vulkan implementation;
- an x86 lifecycle probe executed by FEX.

After the first ordinary `dlclose()`, the probe calls the original retained `vkEnumerateInstanceVersion` PFN successfully. It then performs **256 logical close/reopen cycles**. Every cycle:

1. `dlopen("libvulkan.so.1")`;
2. reacquire `vkGetInstanceProcAddr`;
3. reacquire `vkEnumerateInstanceVersion` through GIPA;
4. require the reopened GIPA address to equal the original GIPA address;
5. require the freshly reacquired native PFN to equal the original PFN;
6. call the fresh PFN and require the same successful Vulkan version;
7. `dlclose()` the handle;
8. call the original retained PFN again after close and require the same result.

Every 32 cycles it also verifies the original guest wrapper address is still present in `/proc/self/maps`.

The stable identities throughout the run are:

```text
gipa = 0x7ffff7ea22b0
pfn  = 0x7ffff76c80f4
version = 4206867
```

Periodic receipts include:

```text
STRESS_PROGRESS cycle=0   gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=32  gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=64  gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=96  gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=128 gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=160 gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=192 gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_PROGRESS cycle=224 gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
STRESS_CYCLES=256
REAL_NODELETE_VULKAN_PFN_STRESS_OK
```

`pfn.exit` is `0`. No `GIPA_DRIFT`, `PFN_DRIFT`, `REOPEN_CALL_FAIL`, `RETAINED_CALL_FAIL`, or `UNMAPPED` marker appears.

The stderr contains 257 `Linking address` lines: the initial dynamic PFN acquisition plus one fresh acquisition per cycle. Every logged registration attempt uses the same native PFN and the same guest invoker:

```text
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7ea4400
```

This is significant because repeated fresh `vkGetInstanceProcAddr` acquisition does not create a new guest thunk generation or redirect target under NODELETE. The bridge identity remains stable instead of exercising FEX's first-wins duplicate-key behavior against a relocated guest helper.

## Meaning

This is now more than a one-close product-sized H→T validation. The NODELETE candidate has survived repeated logical loader handle churn while preserving:

- the generated guest wrapper mapping;
- the guest GIPA entrypoint identity;
- the native host PFN identity;
- the guest `CallHostFunction` invoker identity reported by FEX;
- successful real Vulkan calls both on a freshly reacquired PFN and on the original retained PFN after every close.

Together with the real Vulkan host→guest X11 callback NODELETE run, this provides product-sized execution evidence for both bridge directions that were identified as unload-sensitive.

The stress result also matches the source-level lifetime-alignment argument: current FEX host thunk/native-library loading is already process-resident, and NODELETE prevents the guest bridge generation alone from cycling underneath that longer-lived host state.

This result does not prove that every external application is indifferent to physical guest-wrapper unload, nor does it measure transitive RSS/PSS. Those are policy-risk questions rather than remaining uncertainty about whether NODELETE preserves the demonstrated Vulkan bridges.

All code changes and CI work described here are on owned fork/investigation surfaces. No upstream FEX interaction occurred.
