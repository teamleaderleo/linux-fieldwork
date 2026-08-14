# GL split resident bridge genericity — 2026-08-14

## Result

The split-resident guest-bridge architecture now generalizes beyond Vulkan in **both cross-ISA lifetime directions**.

For generated GL under stock FEX core, a corrected resident companion allows `libGL.so.1` to physically unload while preserving:

- dynamic native PFNs returned by `glXGetProcAddress`;
- generated guest host-call adapters;
- GL's process-retained GuestMalloc callback **target and unpacker**;
- fixed X11 callback unpackers;
- moved wrapper reload with stable native PFNs;
- final retained calls after the reloaded wrapper closes again.

The GL experiments also establish an important generic ownership rule:

> after generated dynamic adapters move into a resident companion, the unloadable wrapper must relinquish its own adapter registry/references rather than keeping a parallel wrapper-local adapter table alive.

## Stock physical-unload controls

### Simple dynamic-PFN path

Workflow:

```text
.github/workflows/gl-stock-unload-control-arm64.yml
run: 31781712676
job: 94708702816
artifact: 9212047049
artifact digest: sha256:9f0a406138603261b959e157b64dfcc3895a16ef1a44c16fe93cddd63280e5a9
```

Trace:

```text
BEFORE_CLOSE get=0x7ffff7bb8250 H=0x7ffff73bd680 error=0
MAP_LOOKUP get -> /usr/lib/x86_64-linux-gnu/libGL.so.1
UNMAPPED 0x7ffff7bb8250
AFTER_CLOSE wrapper_mapped=0
exit=0
```

So ordinary generated `libGL.so.1` is physically reclaimable.

### Matched GLX array-return path

A second stock control pins guest `libX11.so.6`, calls real generated `glXGetFBConfigs`, then closes `libGL.so.1`.

```text
workflow: .github/workflows/gl-stock-glx-unload-control-arm64.yml
run: 31782483832
job: 94711061960
artifact: 9212326370
artifact digest: sha256:629a0cd9406f1ac6d79655529c7f73e750075eb30ad635b451ed2418c7763254
```

Trace:

```text
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
BEFORE_CLOSE configs=<guest allocation> count=240
UNMAPPED glXGetProcAddress
AFTER_CLOSE wrapper_mapped=0
```

Therefore the later split-wrapper retention failures were not ordinary GLX loader behavior.

## Negative design controls

### Crude v2: full generated guest output copied resident

The first GL companion copied the complete generated GL guest `.inl` into a NODELETE DSO.

The retained `glGetError` PFN stayed callable after logical close, but the wrapper did not physically unload:

```text
RETAINED_AFTER_CLOSE error=0
RESERVE_FAIL ... errno=17 File exists
exit=72
```

This is a negative control: moving too much generated wrapper machinery resident defeats the intended wrapper-reclamation semantics.

### Minimal v3: resident adapters, but wrapper-local adapter registry retained

The next candidate narrowed the companion to:

- generated signature-specific adapters;
- resident symbol→adapter lookup;
- resident fixed callback unpackers;
- resident GL malloc callback target + unpacker.

The bridge had no static dependency on `libGL.so.1`. Nevertheless a PFN-only test still retained the wrapper after `dlclose()`:

```text
GL_SPLIT_LINK name=glGetError H=0x7ffff73bd680 T=0x7ffff7e90c50
GEN1 ... error=0
T -> libfex-GL-bridge.so
old libGL ranges captured
post-dlclose glXGetProcAddress still -> libGL.so.1
exit=10
```

Run:

```text
31783185895
artifact: 9212566570
artifact digest: sha256:b6e371b0a0d5856716fe8d04dde2478cd3c799f08fb302086a3c21df6e4e668a
```

The key remaining difference from the successful Vulkan split was that GL still kept its original wrapper-local `HostPtrInvokers` map, which referenced wrapper-local `GetCallerForHostFunction(...)` adapters even though the resident companion had become authoritative.

## GNU-unique hypothesis falsified

A stock/v3/v4/bridge ELF symbol audit found:

```text
libGL-stock.so      UNIQUE=0
libGL-v3.so         UNIQUE=0
libGL-v4.so         UNIQUE=0
libfex-GL-bridge.so UNIQUE=0
```

No exported `fexcallback_` or `fexthunks_invoke_callback` symbols were present in the final ELFs either.

```text
workflow: .github/workflows/gl-split-v3-symbol-audit.yml
run: 31783564642
artifact: 9212655694
artifact digest: sha256:8bd5ee0eca6b3c7d5699bf3adff729f1ccb343ebdd6bc84c995c82beb8ff63f1
```

So the v3 retention regression is not explained by `STB_GNU_UNIQUE` lifetime semantics.

## v4 ownership correction

The successful v4 cut keeps the minimal companion and makes the wrapper relinquish duplicate ownership:

1. remove wrapper-local `HostPtrInvokers` and its references to wrapper-local generated adapters;
2. remove the now-unused wrapper-local `malloc_wrapper` target;
3. make the resident companion the sole generated adapter lookup used by `glXGetProcAddress`;
4. keep GL's process-retained malloc callback target + unpacker resident;
5. keep fixed X11 unpackers resident while the actual X11 target remains with its own DSO.

Conceptually:

```text
native GL PFN H
    -> resident companion lookup
    -> resident generated adapter T
    -> LinkAddressToFunction(H, T)

host GL retained GuestMalloc trampoline
    -> resident malloc unpacker
    -> resident malloc target
```

Unknown host functions without a generated resident adapter are rejected rather than falling back to wrapper-local adapter state.

## v4 dynamic-PFN runtime — PASS

Workflow:

```text
.github/workflows/gl-split-resident-v4-pfn-arm64.yml
run: 31783476072
job: 94714086455
artifact: 9212669469
artifact digest: sha256:c8f27cf2a9b593fa1f5785a86c2e65c653de43a465fc188b738998ca8452fdb0
```

Trace:

```text
GL_SPLIT_LINK name=glGetError H=0x7ffff73bd680 T=0x7ffff7bcfc50
GEN1 get=0x7ffff7e64210 H=0x7ffff73bd680 T=0x7ffff7bcfc50 error=0
T -> libfex-GL-bridge.so
old libGL ranges captured
UNMAPPED old glXGetProcAddress
T still -> libfex-GL-bridge.so
AFTER_CLOSE retained_error=0
all five old libGL ranges reserved successfully
GL_SPLIT_LINK name=glGetError H=0x7ffff73bd680 T=0x7ffff7bcfc50
GEN2 get_old=0x7ffff7e64210 get_new=0x7ffff7073210 moved=1
H_old=0x7ffff73bd680 H_new=0x7ffff73bd680 same_H=1 error=0
exit=0
```

This proves dynamic-PFN genericity beyond Vulkan.

## v4 full GLX + GuestMalloc callback runtime — PASS

Workflow:

```text
.github/workflows/gl-split-resident-v4-runtime-arm64.yml
run: 31783837210
job: 94715195260
artifact: 9212810392
artifact digest: sha256:f909f5f2f91d0d46a92a6f89264f90d8775154903ac8b53b36dc283042c50dc1
```

The test pins guest X11 independently so the experiment isolates GL-wrapper lifetime. It then obtains real generated PFNs for:

```text
glGetError
glXGetFBConfigs
```

Before close:

```text
GL_SPLIT_LINK name=glGetError H=0x7ffff73bd680 T=0x7ffff7bcfc50
GL_SPLIT_LINK name=glXGetFBConfigs H=0x7ffff76c5970 T=0x7ffff7bce1e0
GEN1 ...
GUEST_XSYNC display=0x12345000 discard=0
GUEST_XDISPLAYSTRING display=0x12345000
GL_BRIDGE_MALLOC size=1920
BEFORE_CLOSE_CONFIGS ... count=240
```

The old wrapper mappings are captured, then final `dlclose(libGL.so.1)` physically removes the wrapper:

```text
UNMAPPED old glXGetProcAddress
resident glGetError adapter still -> libfex-GL-bridge.so
AFTER_CLOSE_BEGIN
```

After physical wrapper unload, the **retained old `glXGetFBConfigs` PFN** still performs fresh guest callbacks and the process-retained malloc trampoline executes the resident callback target:

```text
GUEST_XSYNC display=0x12346000 discard=0
GUEST_XDISPLAYSTRING display=0x12346000
GL_BRIDGE_MALLOC size=1920
AFTER_CLOSE_CONFIGS ... count=240
```

All five old wrapper mapping ranges are then successfully occupied with `PROT_NONE`, forcing a moved generation.

Generation 2:

```text
GEN2 get_old=0x7ffff7e5f210 get_new=0x7fffe94a3210 moved=1
Herr_old=0x7ffff73bd680 Herr_new=0x7ffff73bd680 same_H=1
Hcfg_old=0x7ffff76c5970 Hcfg_new=0x7ffff76c5970 same_cfg_H=1
```

The reloaded PFNs again execute fresh X11 callbacks and resident GuestMalloc:

```text
GUEST_XSYNC display=0x12347000 discard=0
GUEST_XDISPLAYSTRING display=0x12347000
GL_BRIDGE_MALLOC size=1920
RELOAD_CONFIGS ... count=240
```

After generation 2 closes, the originally retained `glXGetFBConfigs` PFN still works once more:

```text
GUEST_XSYNC display=0x12348000 discard=0
GUEST_XDISPLAYSTRING display=0x12348000
GL_BRIDGE_MALLOC size=1920
FINAL_RETAINED_CONFIGS ... count=240
exit=0
```

This is direct real generated-GL evidence for both lifetime directions:

- native dynamic PFN → resident guest adapter;
- process-retained host callback trampoline → resident guest malloc unpacker/target.

## Generic design invariant learned from GL

Vulkan already removed its wrapper-local dynamic adapter map when the companion became authoritative. GL made the consequence observable because the intermediate v3 left that old map in place.

The cross-library rule is therefore:

> moving escaped executable bridge code resident is not enough if the unloadable wrapper continues to own a parallel registry/reference graph for the old adapter bodies.

A production generator/build design should make ownership singular: resident bridge adapters are the authoritative generated adapters for dynamic host function pointers, and the unloadable wrapper should not maintain a second address table pointing at wrapper-local copies.

## Relationship to Vulkan

The architecture is now product-sized across two different generated thunk libraries:

```text
unloadable library-specific wrapper
    -> process-resident companion owns executable glue that can escape wrapper lifetime
```

Vulkan evidence covers:

- real dynamic PFNs;
- real Vulkan/X11 retained host→guest callbacks;
- exact FEX-2608;
- selected-before-wrapper-unmap race;
- actual distro `vulkaninfo --summary` compatibility.

GL independently covers:

- real `glXGetProcAddress` dynamic PFNs;
- stock physical wrapper unload;
- forced moved wrapper reload;
- real GLX array-return path;
- process-retained GuestMalloc callback target + unpacker after wrapper unload;
- retained X11 callback execution with X11 lifetime held independently.

## Boundary

All source changes and CI work are diagnostic/research code on owned repository surfaces. No upstream FEX interaction was made. Any upstream implementation must be independently derived and written by a human in compliance with FEX contribution policy.
