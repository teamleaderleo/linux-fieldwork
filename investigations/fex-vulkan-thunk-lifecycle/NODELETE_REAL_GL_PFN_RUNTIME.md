# NODELETE real GL dynamic-PFN runtime

Date: 2026-08-14

## Result

The generic guest-thunk NODELETE policy now has a second real dynamic-PFN API family beyond Vulkan.

Owned FEX branch: `diagnostic/nodelete-real-gl-pfn-20260814`.

Carrier commit: `bbb829dd59b95d7341bc5d1fbaa8eb95f80ba1de`.

Hosted ARM64 run: `31775994522`.

Artifact: `nodelete-real-gl-pfn-31775994522`.

Artifact digest:

```text
sha256:2d6451b51659948fd34fc799a94ae9ead4d341f93659954bcf20594b27c87724
```

The run builds:

- the real FEX runtime;
- the real generated x86-64 `libGL-guest.so`;
- the real FEX GL host thunk;
- the generic `DF_1_NODELETE` guest-wrapper policy.

The resulting guest wrapper preserves `SONAME libGL.so.1` and carries:

```text
FLAGS_1: NODELETE
```

## Probe

The x86 probe executes through FEX and does:

1. `dlopen("libGL.so.1")`;
2. resolve guest `glXGetProcAddress`;
3. ask for `glGetError`;
4. call the returned dynamic PFN;
5. `dlclose(libGL.so.1)` normally;
6. verify the guest GL wrapper mapping still exists;
7. call the original retained PFN after close;
8. perform 256 logical reopen/call/close cycles;
9. require both `glXGetProcAddress` and `glGetError` PFN identity to remain stable;
10. call the retained original PFN after every close.

`glGetError` is useful here because it does not require creating a GLX context; it still exercises FEX's real `glXGetProcAddress` -> `LinkAddressToFunction` dynamic-PFN path.

## Exact runtime receipt

Initial addresses:

```text
BEFORE_CLOSE get=0x7ffff7bb8250 pfn=0x7ffff73bd680 value=0
```

The executable guest wrapper mapping containing `glXGetProcAddress` is:

```text
7ffff7b3c000-7ffff7bcb000 r-xp ... /usr/lib/x86_64-linux-gnu/libGL.so.1
```

After ordinary `dlclose()` that mapping is still present and the exact retained PFN still works:

```text
AFTER_CLOSE_CALL pfn=0x7ffff73bd680 value=0
```

Every periodic check through the 256-cycle loop shows the same identities:

```text
get=0x7ffff7bb8250
pfn=0x7ffff73bd680
value=0
```

Final markers:

```text
STRESS_CYCLES=256
REAL_NODELETE_GL_PFN_STRESS_OK
exit=0
```

No `GIPA`/PFN-style drift occurred in the GL equivalent path.

## Meaning

This eliminates the strongest Vulkan-specific interpretation of the NODELETE success.

GL uses the same generic mechanism as Vulkan:

```text
native host function pointer H
    -> guest CallHostFunction invoker T
    -> LinkAddressToFunction(H, T)
```

The real GL result therefore demonstrates that process-resident guest wrapper code protects a second real dynamic-PFN thunk family across ordinary guest `dlclose()` and repeated logical reopen.

Combined with the Vulkan result, current runtime evidence now covers:

- Vulkan `vkGetInstanceProcAddr` dynamic PFNs;
- GL `glXGetProcAddress` dynamic PFNs;
- Vulkan/X11 host-to-guest callbacks.

That supports treating the lifetime issue as a generic FEX thunk-bridge concern rather than a Vulkan-only teardown quirk.

## Limits

This does not prove CUDA behavior because a real CUDA host driver was not exercised.

It also does not prove that every guest thunk should be resident for policy reasons; it proves that the shared dynamic-PFN mechanism used by at least Vulkan and GL is compatible with and protected by the NODELETE lifetime model.

All code and CI work described here is confined to owned repositories/forks. No upstream FEX interaction occurred.
