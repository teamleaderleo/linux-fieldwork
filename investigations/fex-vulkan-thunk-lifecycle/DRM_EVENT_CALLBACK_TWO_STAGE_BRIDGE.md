# DRM event callback: two-stage bridge diagnostic

Date: 2026-08-14

## Result

A focused owned-fork diagnostic repairs the current-main `drmHandleEvent` cross-ISA callback failure by using FEX's existing two-stage guest-to-host callback trampoline protocol.

Exact FEX product source:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

Owned-FEX carrier:

```text
branch: ci/agent-b-drm-event-callback-bridge-20260814
head:   beb2dfc914f2fbef5687030d428a72209bb7fca6
run:    31778632586
artifact: agent-b-drm-event-callback-bridge-31778632586
artifact id: 9210907824
sha256: 707d14c5f08bd635add18f999d9000612810e05b8e564d9d6a4c91874fa842f5
```

## Runtime matrix

```text
native=0
pristine_reference=132
guest_only_reference=139
candidate=0
```

Candidate stderr reaches the actual guest callback and returns from libdrm:

```text
DRM_PROBE callback=0x558ccdb81450 handle=0x7ffff7ebc880 version=4 event_size=32
MARK handle-enter
DRM_CALLBACK count=1 fd=4 sequence=33 tv=11.22 user=0x12345678
MARK handle-return rc=0 callbacks=1
```

This is callback delivery, not crash suppression.

## Why the first guest-only bridge failed

The first diagnostic copied `drmEventContext` in the guest wrapper and replaced its callback fields with `AllocateHostTrampolineForGuestFunction(...)`. It built, but changed the pristine SIGILL into SIGSEGV 139 before the callback body.

That is expected from FEX's trampoline protocol. Guest-side `AllocateHostTrampolineForGuestFunction` creates a partially initialized host trampoline containing the guest target and guest unpacker, while the native-signature host packer is initially null. Normal generated callback parameters are finalized on the host with `FinalizeHostTrampolineForGuestFunction` before native code can invoke them.

`drmEventContext` is currently marked only `assume_compatible_data_layout`, so thunkgen does not know that its nested fields are callbacks and therefore does not perform that finalization automatically.

Wayland already uses the same two-sided pattern for nested listener callback tables: guest code allocates the host trampolines, and its custom host implementation finalizes each callback with the correct native signature before calling the host library.

## Diagnostic repair shape

The passing diagnostic changes only three product files at runtime in the owned fork:

- `ThunkLibs/libdrm/libdrm_interface.cpp`: mark `drmHandleEvent` as custom guest + custom host.
- `ThunkLibs/libdrm/Guest.cpp`: copy the caller context and allocate partial host trampolines for the version-active callback fields.
- `ThunkLibs/libdrm/Host.cpp`: finalize those callback trampolines with their exact field types, then call native `drmHandleEvent`.

The current probe exercises the vblank callback. The diagnostic also finalizes the version-active page-flip, page-flip2, and sequence callback fields, but those additional event kinds were not runtime-exercised in this receipt.

## Scope

This establishes a concrete conversion mechanism for the synchronous DRM callback defect already retained in `DRM_EVENT_CALLBACK_CURRENT_MAIN.md`.

It does **not** resolve retained callback lifetime after the ordinary guest DRM wrapper physically unloads. A host trampoline stores a FEX guest `CallbackUnpack<signature>::Unpack` address; if that unpacker remains wrapper-owned while native code retains the trampoline, wrapper unload can still invalidate FEX-owned executable state. The generated resident-bridge work therefore remains relevant for persistent DRM callbacks.

It also does not cover `drmServerInfo`'s other callback fields or make this diagnostic upstream-submittable FEX code.

No upstream FEX repository was modified or contacted.
