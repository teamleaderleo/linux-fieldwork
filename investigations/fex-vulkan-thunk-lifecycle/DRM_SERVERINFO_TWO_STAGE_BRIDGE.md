# DRM server-info persistent callback: two-stage bridge diagnostic

Date: 2026-08-14

## Result

A focused owned-fork diagnostic repairs the exact-current-main `drmServerInfo::load_module` cross-ISA callback failure while preserving the callback across the separate registration and later-use calls.

Exact FEX product source:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

Owned-FEX carrier:

```text
branch: ci/agent-b-drm-serverinfo-bridge-20260814
head:   e0d693af36e5e44660193f24babb16487ddee155
run:    31778944710
artifact: agent-b-drm-serverinfo-bridge-31778944710
artifact id: 9211020735
sha256: 1a5a8d0a21dea25470279d05b5359dc43d3b8d5c4f74784a767675274331b5c7
```

## Runtime matrix

```text
native=0
pristine_reference=132
candidate=0
```

Candidate stderr proves the registration returns before the callback and that native libdrm later enters the real guest callback through the converted trampoline:

```text
DRM_SERVER_PRE available=0 callback=0x559566a76460
MARK set-info-enter
MARK set-info-return count=0
MARK open-enter
DRM_SERVER_CALLBACK count=1 name=fex-intentionally-missing-drm-driver
MARK open-return fd=-1 callbacks=1
```

This is callback delivery, not nulling or crash suppression.

## Diagnostic repair shape

The research-only diagnostic changes three product files at workflow runtime:

- `ThunkLibs/libdrm/libdrm_interface.cpp`: mark `drmSetServerInfo` as custom guest + custom host.
- `ThunkLibs/libdrm/Guest.cpp`: copy the caller's `drmServerInfo`, replace only `load_module` with a partial host trampoline from `AllocateHostTrampolineForGuestFunction`, and pass the copy to the host thunk.
- `ThunkLibs/libdrm/Host.cpp`: copy that structure into process-lived host-thunk storage, finalize `load_module` with `FinalizeHostTrampolineForGuestFunction`, then give native libdrm the persistent host-side copy.

The host-side copy is required because native libdrm retains the server-info pointer after `drmSetServerInfo` returns.

## Scope and next lifetime boundary

This receipt converts only the exercised `load_module` field. It does not claim that other `drmServerInfo` callbacks are converted; in particular, `debug_print` has a different/variadic-style calling surface that needs its own ABI review.

The ordinary guest DRM wrapper remains loaded throughout this passing run. The host trampoline contains a guest `CallbackUnpack<int(const char*)>::Unpack` address supplied by the guest wrapper. Therefore this result establishes callback conversion but does **not** yet establish safe callback use after physical guest-wrapper unload.

The next discriminator is to register once, physically unload the ordinary DRM guest wrapper, avoid re-registering server info, then trigger the later `drmOpen` callback. Whole-wrapper NODELETE should contain that case, while the unload-preserving resident-bridge architecture should keep the fixed FEX callback unpacker resident independently of wrapper state.

This is a non-Vulkan instance of the same escaped-FEX-executable ownership question now proven for Vulkan dynamic PFNs and X11 callback helpers.

No upstream FEX repository was modified or contacted. This code is research-only on owned surfaces and is not an upstream contribution.
