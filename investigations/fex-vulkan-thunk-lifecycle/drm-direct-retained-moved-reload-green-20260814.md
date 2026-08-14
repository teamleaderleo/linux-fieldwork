# DRM direct retained callback moved reload — GREEN — 2026-08-14

## Exact source and gate

Clean source base:

`c348a19d91219d4df6cdaa86839607565e001fa2`

Diagnostic branch:

`diagnostic/drm-direct-resident-callback-member-20260814`

Retained workflow carrier head:

`1d27b3c73e28f8dd3a14f895c3eb4194e79cbd75`

Workflow:

`.github/workflows/drm-direct-retained-moved-reload.yml`

Run:

`31798437804`

Job:

`94760598719` (`retained`)

Result:

`success`

Probe exit:

`0`

Artifact:

- name: `drm-direct-retained-moved-reload-31798437804`
- ID: `9218393020`
- SHA-256: `8486d55a5329543ebb73d72d9d059622a8677f5e3ec182c28cd047343a9c5e14`

This run applies the same direct DRM source candidate that passed build/role/ELF/immediate-callback run `31798196251`, then adds runtime-only unpacker observability plus a tiny native libdrm retention test double.

## Direct resident unpacker ownership

Generation 1:

```text
GEN1 handle=0x7ffff7eb9180 unpacker=0x7ffff7eaf210
MAP 0x7ffff7eaf210 7ffff7eaf000-7ffff7eb0000 r-xp ... /rootfs-drm-retained/usr/lib/x86_64-linux-gnu/libfex-drm-bridge.so
```

The runtime-only `FEXDRMDiagVBlankUnpacker` getter therefore places the generated vblank callback unpacker inside the resident companion executable mapping.

The direct bridge role receipt remains exactly three unpacker-only signatures and zero caller signatures:

```text
index=0 caller=0 unpacker=1 hash=0d6be1284d30cf3423bdc235dfe0a0664c1455f019f9c36ec90548960076e2dc void (int, unsigned int, unsigned int, unsigned int, unsigned int, void *)
index=1 caller=0 unpacker=1 hash=716d5ac8035bbe770a43d44c4736033c9f2e18bfe3f83527f1bd46cf1e73552d void (int, unsigned long, unsigned long, unsigned long)
index=2 caller=0 unpacker=1 hash=15faee5a1a2e831f6a79ab3295240b6a8b99f85f0d850f98e8c1d75cc3b5ad02 void (int, unsigned int, unsigned int, unsigned int, void *)
```

## Generation-1 registration and first callback

The native arm64 test double implements only the two libdrm functions used by the proof:

- `drmHandleEvent` saves the converted host callback trampoline and invokes it once;
- `drmAvailable` later invokes the same saved trampoline without accepting or registering another callback.

Generation 1 receipt:

```text
HOST_DRM_SAVE trampoline=0x7ffff7eaa000
DRM_RETAINED_CALLBACK count=1 fd=5 seq=41 tv=42.43 user=0x11112222
```

The saved address is the native host-callable trampoline created from generation 1's `drmEventContext::vblank_handler` conversion.

## Physical wrapper unload

Generation-1 wrapper mappings:

```text
OLD_DRM_RANGE 7ffff7eb3000-7ffff7eb6000
OLD_DRM_RANGE 7ffff7eb6000-7ffff7eba000
OLD_DRM_RANGE 7ffff7eba000-7ffff7ebc000
OLD_DRM_RANGE 7ffff7ebc000-7ffff7ebd000
OLD_DRM_RANGE 7ffff7ebd000-7ffff7ebe000
```

After `dlclose`:

```text
UNMAPPED 0x7ffff7eb9180
```

The resident vblank unpacker remained mapped in `libfex-drm-bridge.so` after wrapper close.

## Forced moved reload

All five retired wrapper ranges were reserved with `MAP_FIXED_NOREPLACE`:

```text
RESERVED_DRM 7ffff7eb3000-7ffff7eb6000
RESERVED_DRM 7ffff7eb6000-7ffff7eba000
RESERVED_DRM 7ffff7eba000-7ffff7ebc000
RESERVED_DRM 7ffff7ebc000-7ffff7ebd000
RESERVED_DRM 7ffff7ebd000-7ffff7ebe000
```

Generation 2 moved:

```text
GEN2 handle_old=0x7ffff7eb9180 handle_new=0x7ffff7e6b180 moved=1 callbacks_before_trigger=1
```

The generation-2 probe deliberately does not call `drmHandleEvent`; therefore it does not re-register or replace the saved callback trampoline.

## Retained generation-1 host trampoline after reload

`drmAvailable` on generation 2 only asks the native test double to trigger the already-saved generation-1 trampoline:

```text
HOST_DRM_TRIGGER trampoline=0x7ffff7eaa000
DRM_RETAINED_CALLBACK count=2 fd=77 seq=51 tv=52.53 user=0x33334444
AFTER_RELOAD_TRIGGER rc=1 callbacks=2
```

The saved host trampoline address is identical before and after reload. The second callback reaches guest successfully after the generation-1 wrapper was unmapped and generation 2 moved.

The resident unpacker remained mapped afterward:

```text
MAP 0x7ffff7eaf210 7ffff7eaf000-7ffff7eb0000 r-xp ... /rootfs-drm-retained/usr/lib/x86_64-linux-gnu/libfex-drm-bridge.so
```

Final gate markers:

```text
DRM_RETAINED_MOVED_RELOAD_OK
DRM_RETAINED_RUNTIME_OK
```

## ELF boundary in the lifetime run

The lifetime build independently preserved the intended ownership boundary:

- wrapper SONAME `libdrm.so.2`;
- wrapper `NEEDED libfex-drm-bridge.so`;
- wrapper RUNPATH contains `$ORIGIN`;
- wrapper has no NODELETE;
- companion SONAME `libfex-drm-bridge.so`;
- companion carries `FLAGS_1 NODELETE`.

## Promotion decision

DRM now has both required independent gates from the direct callback_member implementation:

1. build / exact three unpacker-only roles / ELF / real pipe-fed callback execution: run `31798196251`;
2. generation-1 host-retained callback after physical unload + reserved old ranges + moved generation 2 + zero re-registration: run `31798437804`.

The validated DRM source delta is ready for a clean source-only tranche on top of `c348a19d91219d4df6cdaa86839607565e001fa2`. Runtime-only observability, fake native libdrm, probe code, scripts, and workflows stay off the clean integration branch.
