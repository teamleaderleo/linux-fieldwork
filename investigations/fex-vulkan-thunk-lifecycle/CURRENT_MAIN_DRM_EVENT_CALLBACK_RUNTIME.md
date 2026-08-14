# Current-main DRM event callback cross-ISA escape

## Scope

This checkpoint tests a non-Vulkan callback-bearing thunk path on exact current FEX product source.

FEX product source: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

Owned-FEX carrier branch: `ci/agent-b-drm-event-callback-f3ab-20260814`.

Successful carrier lineage:

```text
44f819d ci: add OpenGL configure dependency for DRM lane
3488498 ci: run DRM event callback discriminator on ARM64
e7c0e9f ci: add pipe-fed DRM event callback probe
f3ab82a Merge pull request #5823 from Sonicadvance1/202
```

Before execution, the workflow verified that `ThunkLibs`, `FEXCore`, and `Source` were unchanged relative to exact `f3ab82...`.

Workflow run: `31776289267`.
Job: `94692283543`.
Artifact: `9210056297`, `agent-b-drm-event-callback-31776289267`.
Artifact digest: `sha256:aeb6d9df04c89ac55e4c1f9d83cf1c565e8a6c2861608b1208eac9306bd03cde`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Workflow: https://redirect.github.com/teamleaderleo/FEX/actions/runs/31776289267

The runner used libdrm `2.4.125-1ubuntu0.1~24.04.2`.

## Why this probe needs no GPU

`drmHandleEvent()` consumes already-encoded DRM event records from the supplied file descriptor and dispatches callbacks from `drmEventContext`.

The probe therefore uses a normal pipe rather than a DRM device:

1. write one complete `drm_event_vblank` record to the pipe;
2. set `drmEventContext.version = DRM_EVENT_CONTEXT_VERSION`;
3. set `vblank_handler` to the probe callback;
4. call `drmHandleEvent(read_fd, &context)`.

The event contains deterministic values:

```text
type=DRM_EVENT_VBLANK
length=32
user_data=0x12345678
tv_sec=11
tv_usec=22
sequence=33
```

The x86 callback entry starts with the same cross-ISA discriminator used by the Vulkan probes: bytes `e9 00 00 00 00`. This is a harmless x86 jump to the callback body but presents an illegal first AArch64 instruction if native ARM code branches directly to the x86 guest callback address.

## Native ARM64 control

Native libdrm dispatches exactly one callback and returns normally:

```text
DRM_PROBE callback=<arm64 callback> handle=<drmHandleEvent> version=4 event_size=32
MARK handle-enter
DRM_CALLBACK count=1 fd=3 sequence=33 tv=11.22 user=0x12345678
MARK handle-return rc=0 callbacks=1
```

Native exit:

```text
0
```

This establishes that the pipe event is complete and that no kernel DRM device is required for the discriminator.

## Exact-current FEX result

Pristine exact-current FEX reaches the same dispatch boundary:

```text
DRM_PROBE callback=0x5572e76fb450 handle=0x7ffff7ebc0c0 version=4 event_size=32
MARK handle-enter
```

It then terminates with SIGILL:

```text
native=0
fex=132
```

There is no `DRM_CALLBACK` body marker and no `MARK handle-return`.

## Source match

At exact `f3ab82...`, the 64-bit DRM thunk declares both callback-bearing structures layout-compatible rather than callback-aware:

```cpp
// TODO: Convert vtable
template<>
struct fex_gen_type<drmServerInfo> : fexgen::assume_compatible_data_layout {};
template<>
struct fex_gen_type<drmEventContext> : fexgen::assume_compatible_data_layout {};
```

`drmHandleEvent` itself is a generic generated thunk:

```cpp
template<>
struct fex_gen_config<drmHandleEvent> {};
```

Exact source:
https://redirect.github.com/FEX-Emu/FEX/blob/f3ab82a73fb48271ee12a882c98bc5d823a2b4d1/ThunkLibs/libdrm/libdrm_interface.cpp

So on a 64-bit x86 guest / ARM64 host pair, the event-context layout is forwarded without converting the guest callback pointer to a host-callable trampoline. Native libdrm subsequently branches to the raw x86 callback address.

## Conclusion

Current FEX has a demonstrated **non-Vulkan cross-ISA callback-conversion defect** in the 64-bit `drmHandleEvent` path:

```text
native ARM64: callback delivered once, return 0
exact-current FEX: SIGILL 132 at callback dispatch
```

This defect is independent of:

- Vulkan proc-address routing;
- Vulkan `pNext` handling;
- X11 thunk initialization;
- `VkAllocationCallbacks`;
- guest-thunk `dlclose()` / NODELETE lifetime behavior.

It broadens the callback audit rule: callback-bearing structs marked `assume_compatible_data_layout` must be reviewed for embedded function pointers even when their ordinary C data layout is ABI-compatible.

## Lifetime-policy boundary

This result by itself does **not** prove that selective versus blanket NODELETE is correct or incorrect.

`drmHandleEvent` invokes the callback synchronously while the guest wrapper is still loaded. A correct callback conversion could therefore use a wrapper-resident generated callback unpacker without requiring process-lifetime residency for this specific call.

However, the same DRM interface also marks `drmServerInfo` layout-compatible despite the explicit `TODO: Convert vtable`, and exposes `drmSetServerInfo` generically. That persistent callback-bearing path deserves a separate lifetime-aware probe.

## Next discriminator

The highest-value DRM follow-up is to test one callback-aware `drmHandleEvent` diagnostic using FEX's existing `AllocateHostTrampolineForGuestFunction` / `CallbackUnpack` mechanism. A successful native-equivalent callback delivery would prove repair direction without suppressing API semantics.

A second follow-up should test `drmSetServerInfo` because native libdrm retains that callback-bearing structure across calls, making it relevant to both callback conversion and guest-wrapper lifetime.

No upstream interaction was performed. All mutation and CI execution stayed in owned repositories/forks; upstream FEX remained read-only.