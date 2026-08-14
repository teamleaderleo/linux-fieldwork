# DRM retained callback: resident unpacker survives forced moved wrapper reload

Date: 2026-08-14

## Result

A minimal per-library resident DRM bridge sidecar fixes the exact previously demonstrated moved-reload lifetime failure for the converted `drmServerInfo::load_module` callback while keeping the ordinary guest DRM wrapper physically unloadable.

The only FEX-owned executable callback component moved out of the ordinary wrapper is the fixed guest unpacker for:

```cpp
int(const char*)
```

The application callback target remains in the guest executable, the host-side retained `drmServerInfo` copy remains process-lived as in the earlier passing conversion diagnostic, and generation 2 deliberately does **not** re-register server info.

Exact FEX product base:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

Owned-FEX carrier:

```text
branch: ci/agent-b-drm-serverinfo-bridge-20260814
head:   d446528f1a423cf7413f1891eb81eb9ba9df295f
run:    31780014470
job:    94703526184
artifact: agent-b-drm-resident-unpacker-31780014470
artifact id: 9211415341
sha256: 024436a3142d05a7232f75f79eac4064f03248dead8a07243f7c1affad4d4e6c
```

## A/B

The immediately preceding wrapper-owned-unpacker run used the same callback conversion and same forced moved-reload fixture, but retained `CallbackUnpack<int(const char*)>::Unpack` inside generation 1. It produced:

```text
wrapper-owned unpacker after moved reload = 139
```

The resident-unpacker candidate produces:

```text
native_precondition=0
wrapper_owned_unpacker_reference=139
resident_unpacker=0
OUTCOME=retained_callback_survived_moved_reload_via_resident_unpacker
```

## Binary ownership checks

The ordinary DRM wrapper is still unloadable. Its dynamic section has no `DF_1_NODELETE`, but it has an explicit dependency on the bridge:

```text
NEEDED Shared library: [libfex-drm-bridge.so]
SONAME Library soname: [libdrm.so.2]
```

The bridge alone carries:

```text
SONAME Library soname: [libfex-drm-bridge.so]
FLAGS_1 Flags: NODELETE
```

So this result is not whole-wrapper pinning in disguise.

## Forced moved-reload receipt

Generation 1 registers the converted callback once:

```text
GEN1 wrapper=/home/runner/work/FEX/FEX/rootfs-amd64/usr/lib/x86_64-linux-gnu/libdrm.so.2 set=0x7ffff7ebc8b0 open=0x7ffff7eba4a0 callback=0x55fbd2c5ca10 ranges=5
MARK set-info-enter
MARK set-info-return count=0
```

The ordinary wrapper then physically unmaps:

```text
MARK close1-enter
MARK close1-return old_set_mapped=0
```

The probe reserves every exact generation-1 wrapper mapping:

```text
RESERVED 0x7ffff7eb7000-0x7ffff7eb9000
RESERVED 0x7ffff7eb9000-0x7ffff7ebd000
RESERVED 0x7ffff7ebd000-0x7ffff7ebf000
RESERVED 0x7ffff7ebf000-0x7ffff7ec0000
RESERVED 0x7ffff7ec0000-0x7ffff7ec1000
```

Generation 2 therefore moves:

```text
GEN2 set=0x7ffff7e6b8b0 open=0x7ffff7e694a0 moved=1
```

The critical negative control is preserved: generation 2 does **not** call `drmSetServerInfo`. Native libdrm must use the generation-1 retained registration:

```text
MARK open2-enter retained-registration-only
DRM_SERVER_CALLBACK count=1 name=fex-intentionally-missing-drm-driver
MARK open2-return fd=-1 callbacks=1
```

The process exits 0.

## Diagnostic implementation shape

The research-only runtime patch first applies the already-proven two-stage callback conversion:

1. guest wrapper copies `drmServerInfo` and allocates a host trampoline;
2. host wrapper copies the structure into process-lived host-thunk storage;
3. host wrapper finalizes the trampoline with the exact native callback type;
4. native libdrm retains the host-side structure pointer.

The lifetime change is then deliberately narrow:

- add `libfex-drm-bridge.so` as a tiny 64-bit guest sidecar;
- use explicit thunkgen function-type registration for `int(const char*)`;
- instantiate `CallbackUnpack<int(const char*)>::Unpack` in the sidecar;
- return that resident unpacker address to the ordinary DRM wrapper;
- pass the resident unpacker plus the unchanged application callback target to `AllocateHostTrampolineForGuestFunction`;
- mark only the sidecar NODELETE;
- link the ordinary DRM wrapper against the sidecar.

The normal DRM wrapper remains reclaimable and can move between generations.

## Why this matters beyond DRM

This is a non-Vulkan confirmation of the resident-bridge ownership rule using a different API shape.

The full derived Vulkan bridge can automatically migrate ordinary thunkgen-emitted indirect signatures and generated callback parameters. `drmServerInfo::load_module` is different: the callable pointer is hidden inside a structure currently declared `assume_compatible_data_layout`, so thunkgen does not recognize it as a callback parameter at all. It therefore requires library-specific conversion/finalization metadata or a handwritten custom wrapper today.

Despite that difference, the lifetime solution is the same:

> FEX-created executable adapters/unpackers whose addresses escape into persistent host/native state must be owned by process-lived bridge code, not by an unloadable ordinary wrapper generation.

This receipt therefore validates the per-library resident bridge architecture for a **nested retained callback**, not only dynamic Vulkan PFNs or handwritten X11 helpers.

## Generator implication

The next implementation-quality question is not whether the sidecar architecture works; this run answers that positively. The useful generator improvement is how to describe callback-bearing fields inside ABI-compatible structures so thunkgen can automate the same two-stage conversion and redirect the generated guest unpacker into the per-library resident bridge.

A reasonable metadata direction would need to express, per structure field:

- that the field is a guest callback pointer rather than inert layout-compatible data;
- the exact callback signature used for host finalization;
- whether the containing structure is copied only for one synchronous call or retained by native code beyond the call;
- any lifetime/ownership rule for the host-side replacement structure.

The current derived bridge machinery can then supply the resident unpacker by type once the nested field is exposed to generation.

## Scope

This receipt covers only the exercised `drmServerInfo::load_module` callback and only the fixed `int(const char*)` unpacker sidecar. It does not claim conversion or lifetime safety for the remaining `drmServerInfo` callbacks, especially `debug_print`, which needs a separate ABI review.

This does not make the research patch upstream-submittable FEX code. All code and CI ran only on owned repositories/forks. No upstream FEX repository was modified or contacted.
