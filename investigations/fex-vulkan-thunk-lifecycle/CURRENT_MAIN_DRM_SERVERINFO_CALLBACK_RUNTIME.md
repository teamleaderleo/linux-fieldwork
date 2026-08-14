# Current-main persistent DRM server-info callback escape

## Scope

This checkpoint tests a callback-bearing libdrm structure that native libdrm retains across calls.

Exact FEX product source: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

Owned-FEX carrier branch: `ci/agent-b-drm-serverinfo-callback-f3ab-20260814`.

Carrier lineage:

```text
02f058b ci: run persistent DRM server-info callback discriminator
42e9c5b ci: add persistent DRM server-info callback probe
f3ab82a Merge pull request #5823 from Sonicadvance1/202
```

Before execution, the workflow verified that `ThunkLibs`, `FEXCore`, and `Source` were unchanged relative to exact `f3ab82...`.

Workflow run: `31776944561`.
Job: `94694259622`.
Artifact: `9210303458`, `agent-b-drm-serverinfo-callback-31776944561`.
Artifact digest: `sha256:0353fd5abc6f35bcf878b6d90e406339b238192be7a16a6a2f3b9baefccfe2e1`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Workflow: https://redirect.github.com/teamleaderleo/FEX/actions/runs/31776944561

The runner used libdrm `2.4.125-1ubuntu0.1~24.04.2`.

## Discriminator

The probe resolves `drmSetServerInfo`, `drmOpen`, and `drmAvailable` from `libdrm.so.2`.

It first requires:

```text
drmAvailable() == 0
```

so the later `drmOpen()` path deterministically attempts the registered `load_module` callback rather than opening an already-available DRM device.

The probe then:

1. creates a stack `drmServerInfo`;
2. sets only `load_module` to the probe callback;
3. calls `drmSetServerInfo(&info)` and returns from that registration call;
4. later calls `drmOpen("fex-intentionally-missing-drm-driver", NULL)`;
5. expects libdrm to invoke the previously registered `load_module` callback exactly once and then return `-1`.

The x86 callback entry begins with the same deterministic `e9 00 00 00 00` cross-ISA discriminator used by the Vulkan and DRM-event probes.

## Native ARM64 control

The hosted native environment satisfies the precondition and proves the callback is retained across calls:

```text
DRM_SERVER_PRE available=0 callback=<arm64 callback>
MARK set-info-enter
MARK set-info-return count=0
MARK open-enter
DRM_SERVER_CALLBACK count=1 name=fex-intentionally-missing-drm-driver
MARK open-return fd=-1 callbacks=1
```

Native exit:

```text
0
```

The important boundary is that `drmSetServerInfo()` has already returned before native libdrm later invokes the callback during `drmOpen()`.

## Exact-current FEX result

Exact pristine FEX reaches the same registration and later-use boundary:

```text
DRM_SERVER_PRE available=0 callback=0x563f68a84460
MARK set-info-enter
MARK set-info-return count=0
MARK open-enter
```

It then terminates with SIGILL:

```text
native=0
fex=132
```

There is no `DRM_SERVER_CALLBACK` body marker and no `MARK open-return`.

## Source match

At exact `f3ab82...`, the DRM thunk interface explicitly acknowledges but does not convert this callback-bearing structure:

```cpp
// TODO: Convert vtable
template<>
struct fex_gen_type<drmServerInfo> : fexgen::assume_compatible_data_layout {};
```

and `drmSetServerInfo` is a generic generated thunk:

```cpp
template<>
struct fex_gen_config<drmSetServerInfo> {};
```

Exact source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libdrm/libdrm_interface.cpp

The result is therefore consistent with the 64-bit struct layout being forwarded while the embedded x86 callback pointer remains unconverted. Native ARM libdrm stores and later calls that raw guest address.

## Conclusion

Current FEX has a second demonstrated non-Vulkan cross-ISA DRM callback defect, this time across a **persistent registration boundary**:

```text
native ARM64: register -> later callback once -> drmOpen returns -1
exact-current FEX: register returns -> later callback dispatch SIGILL 132
```

This is distinct from the synchronous `drmHandleEvent` finding. Together they show that the callback problem includes both:

- callback-bearing structs consumed synchronously; and
- callback-bearing structs retained by the native host library and invoked later.

## Lifetime implication

This persistent case is directly relevant to any future callback-conversion design.

A correct `drmSetServerInfo` bridge cannot put converted callback state in temporary stack storage or in wrapper executable code that may disappear while native libdrm still retains the registration. The converted callback descriptor/trampoline needs an ownership lifetime at least as long as the native registration, with explicit replacement/retirement if the API allows it.

This does **not** prove that blanket NODELETE is the only valid lifetime policy. It does show why selective residency decisions cannot be based solely on whether a handwritten `Guest.cpp` has static variables: the native API itself can retain callback-bearing state whose eventual bridge may depend on guest-wrapper unpackers.

## Repair direction

The synchronous `drmHandleEvent` path is the cleaner first callback-conversion target because its converted context can be scoped to one call.

`drmSetServerInfo` should be treated separately as a retained-callback ownership problem: conversion plus stable descriptor/trampoline lifetime and replacement semantics.

No upstream interaction was performed. All mutation and CI execution stayed in owned repositories/forks; upstream FEX remained read-only.