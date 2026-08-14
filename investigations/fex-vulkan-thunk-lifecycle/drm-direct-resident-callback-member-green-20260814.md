# DRM direct callback_member resident bridge — GREEN — 2026-08-14

## Source under test

Clean source base:

`c348a19d91219d4df6cdaa86839607565e001fa2`

Diagnostic branch:

`diagnostic/drm-direct-resident-callback-member-20260814`

Direct workflow carrier head:

`24361ca9c5554aa2984a9eeb617edbd1fc16f49f`

The source transform is `LinuxFieldwork/apply_drm_direct_resident_callback_member_bridge.py` and changes the product workspace only by:

- annotating all four callback-bearing `drmEventContext` members with `fexgen::callback_member`;
- including direct DRM bridge accessors in the guest wrapper;
- routing generated callback-member allocation through `FEXAllocateResidentHostTrampolineForGuestFunction`;
- adding `ThunkLibs/libdrm_bridge/Guest.cpp` with direct thunkgen bridge output;
- wiring `libfex-drm-bridge.so` through the common per-library helper.

## Direct build / role / ELF / execution gate

Run:

`31798196251`

Job:

`94759850681` (`drm-direct`)

Result:

`success`

Artifact:

- name: `drm-direct-resident-callback-31798196251`
- ID: `9218310037`
- SHA-256: `c470a5bc2682cfde59edf0360f7db27c8f453d152cdbe10c30ebbbcd3b8ef6df`

The exact clean-source provenance gate passed against `c348a19d91219d4df6cdaa86839607565e001fa2` before the transform.

A native pipe-fed `drmHandleEvent` control passed first.

The transformed product then built:

- FEX
- FEXServer
- `drm-host-64`
- `drm-guest`
- `drm_bridge-guest`

## Direct generator role receipt

The direct generated DRM bridge has exactly three bridge signatures, all unpacker-only:

```text
FEX_BRIDGE_ROLE index=0 caller=0 unpacker=1 hash=0d6be1284d30cf3423bdc235dfe0a0664c1455f019f9c36ec90548960076e2dc void (int, unsigned int, unsigned int, unsigned int, unsigned int, void *)
FEX_BRIDGE_ROLE index=1 caller=0 unpacker=1 hash=716d5ac8035bbe770a43d44c4736033c9f2e18bfe3f83527f1bd46cf1e73552d void (int, unsigned long, unsigned long, unsigned long)
FEX_BRIDGE_ROLE index=2 caller=0 unpacker=1 hash=15faee5a1a2e831f6a79ab3295240b6a8b99f85f0d850f98e8c1d75cc3b5ad02 void (int, unsigned int, unsigned int, unsigned int, void *)
```

There are zero caller roles.

This independently confirms the older prototype observation that the four callback-bearing `drmEventContext` fields deduplicate to three canonical callback signatures.

The normal generated guest output contains the nested callback conversion:

```text
1238:    fex_callback_copy_1.vblank_handler = AllocateHostTrampolineForGuestFunction(a_1->vblank_handler);
```

The direct accessor output contains `FEXAllocateResidentHostTrampolineForGuestFunction`, and the wrapper macro remap makes that generated nested conversion allocate with the resident direct unpacker.

## ELF ownership receipt

`guest/libdrm-guest.so`:

- `NEEDED libfex-drm-bridge.so`;
- RUNPATH contains `$ORIGIN`;
- no NODELETE flag.

`guest/libfex-drm-bridge.so`:

- SONAME `libfex-drm-bridge.so`;
- `FLAGS_1 NODELETE`.

Build size receipt:

```text
   text   data bss   dec   hex filename
  28585    664   8 29257  7249 guest/libdrm-guest.so
   1992    472   8  2472   9a8 guest/libfex-drm-bridge.so
```

The process-resident DRM companion is about 2.4 KiB by `size` accounting in this direct candidate.

## Real callback execution

The amd64 guest pipe-fed callback probe ran under FEX through the direct resident candidate and exited 0:

```text
DRM_PROBE callback=0x55c13d227450 handle=0x7ffff7ebc180 version=4 event_size=32
MARK handle-enter
DRM_CALLBACK count=1 fd=4 sequence=33 tv=11.22 user=0x12345678
MARK handle-return rc=0 callbacks=1
```

Gate markers:

```text
DRM_DIRECT_BUILD_ELF_OK
DRM_DIRECT_CALLBACK_OK
```

This establishes direct-generator callback_member conversion, direct unpacker-only resident ownership, common-helper packaging, and real callback execution from the clean GL-tranche-2 source base.

## Remaining lifetime proof

This direct run invokes `drmHandleEvent` synchronously while the wrapper is loaded. The separate retained moved-reload workflow must still prove that a native host-retained generation-1 trampoline can call the resident DRM unpacker after the wrapper physically unloads, old wrapper ranges are reserved, generation 2 moves, and generation 2 does not re-register the callback.

That separate workflow is `.github/workflows/drm-direct-retained-moved-reload.yml`, introduced on diagnostic commit `1d27b3c73e28f8dd3a14f895c3eb4194e79cbd75`.
