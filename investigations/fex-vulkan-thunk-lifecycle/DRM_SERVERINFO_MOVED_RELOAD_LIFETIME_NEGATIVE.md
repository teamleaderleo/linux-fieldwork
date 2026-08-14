# DRM retained callback: forced moved-wrapper reload lifetime negative

Date: 2026-08-14

## Result

The already-converted `drmServerInfo::load_module` callback fails after the ordinary guest DRM thunk physically unloads and is forced to reload at a different address. The failure occurs even though the application callback target itself remains valid in the main guest executable.

This isolates the remaining stale executable dependency to FEX-owned callback bridge state: the retained host trampoline still references a generation-1 guest `CallbackUnpack<int(const char*)>::Unpack` address from the unloaded wrapper.

Exact FEX product source:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

Owned-FEX carrier:

```text
branch: ci/agent-b-drm-serverinfo-bridge-20260814
head:   5a9b5b7b76f8ada2fc5fd3e1f40a3a9a71cf6cb3
run:    31779376939
job:    94701592337
artifact: agent-b-drm-serverinfo-moved-reload-31779376939
artifact id: 9211177387
sha256: 6039243e7f8970218eb6ac8e0a2a0aff2323cb1d1408988936ef9b1ee0fcc66a
```

## Preconditions

The same two-stage callback conversion already passes while the wrapper remains loaded:

```text
native_precondition=0
converted_loaded_reference=0
```

The moved-reload build explicitly verifies that the guest DRM wrapper does **not** carry `DF_1_NODELETE`.

## Forced moved-reload receipt

Generation 1 registers the converted callback once:

```text
GEN1 wrapper=/home/runner/work/FEX/FEX/rootfs-amd64/usr/lib/x86_64-linux-gnu/libdrm.so.2 set=0x7ffff7ebc890 open=0x7ffff7eba480 callback=0x5636584a0a10 ranges=5
MARK set-info-enter
MARK set-info-return count=0
```

The ordinary guest wrapper then physically unloads:

```text
MARK close1-enter
MARK close1-return old_set_mapped=0
```

All five exact generation-1 wrapper mappings are reserved with `PROT_NONE | MAP_FIXED_NOREPLACE`:

```text
RESERVED 0x7ffff7eb7000-0x7ffff7eb9000
RESERVED 0x7ffff7eb9000-0x7ffff7ebd000
RESERVED 0x7ffff7ebd000-0x7ffff7ebf000
RESERVED 0x7ffff7ebf000-0x7ffff7ec0000
RESERVED 0x7ffff7ec0000-0x7ffff7ec1000
```

Generation 2 is therefore forced elsewhere:

```text
GEN2 set=0x7ffff7e6b890 open=0x7ffff7e69480 moved=1
```

The probe deliberately does **not** call generation-2 `drmSetServerInfo`; native libdrm must use the callback registration retained from generation 1:

```text
MARK open2-enter retained-registration-only
```

The process then exits 139 before the application callback body and before `drmOpen` returns:

```text
moved_reload=139
OUTCOME=retained_callback_failed_after_physical_moved_reload
```

There is no `DRM_SERVER_CALLBACK count=1` and no `MARK open2-return`.

## Interpretation

This closes an important gap between callback conversion and callback lifetime.

The `drmSetServerInfo` diagnostic uses the correct two-stage FEX callback protocol:

1. guest wrapper allocates the host trampoline using `AllocateHostTrampolineForGuestFunction`;
2. host wrapper finalizes it using `FinalizeHostTrampolineForGuestFunction`;
3. host thunk keeps a process-lived copy of `drmServerInfo` because native libdrm retains that pointer.

That is enough while the guest wrapper remains mapped, and the real callback is delivered successfully in the loaded-wrapper control.

However, the host trampoline also stores the guest `CallbackUnpack<int(const char*)>::Unpack` address supplied by the generation-1 guest wrapper. The application callback target is not the object being unloaded: it remains in the probe executable. After generation-1 wrapper mappings are removed and protected, the retained native callback path faults before the application callback body.

This is therefore a concrete non-Vulkan instance of the same ownership rule established by the generated Vulkan split-bridge work: **FEX-created escaped executable adapters/unpackers must not remain owned by an unloadable wrapper generation.**

## Repair direction

Whole-wrapper `DF_1_NODELETE` would contain this class by keeping the generation-1 unpacker mapped, but it deliberately prevents physical wrapper reclamation.

The unload-preserving repair is narrower: move the fixed FEX guest callback unpacker for the `int(const char*)` signature into a process-resident per-library DRM bridge sidecar while leaving the ordinary DRM wrapper unloadable. The host-side `drmServerInfo` storage and trampoline finalization can remain as in the passing conversion diagnostic.

The existing thunkgen explicit-function-type mechanism is sufficient to generate the resident callback signature without introducing fake API exports.

The next A/B is the **same** forced moved-reload probe with only the FEX-owned `load_module` guest unpacker moved into a resident DRM bridge DSO. Success requires generation 1 to unmap, generation 2 to move, no re-registration, and the retained callback to reach the original application target once and return normally.

## Scope

This receipt is specific to the exercised `drmServerInfo::load_module` callback. It does not claim conversion or lifetime safety for the other `drmServerInfo` callbacks, especially the separate `debug_print` calling surface.

No upstream FEX repository was modified or contacted. All diagnostic code ran only on owned research surfaces and is not an upstream contribution.
