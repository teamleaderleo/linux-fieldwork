# GL split resident bridge genericity — 2026-08-14

## Summary

The split-resident guest-bridge architecture generalizes beyond Vulkan for dynamic function-pointer thunks, but the GL experiments exposed an important ownership rule:

> after generated dynamic adapters move into a resident companion, the unloadable wrapper must stop owning/referencing its original adapter registry.

A minimal GL companion that moved adapters resident but left the wrapper's original `HostPtrInvokers` map intact caused `libGL.so.1` to remain mapped after `dlclose()`. Removing that wrapper-local adapter table restored physical unload while preserving the retained native PFN across wrapper generations.

This is a stronger genericity result than whole-wrapper pinning because stock GL is independently proven to physically unload in the same hosted environment.

## Stock controls

### Stock generated GL unloads

Owned fork workflow:

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

So the ordinary generated GL wrapper is physically reclaimable.

### Stock GL still unloads after the GLX array-return path

A matched control pins guest `libX11.so.6`, calls `glXGetFBConfigs`, then closes `libGL.so.1`.

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

Therefore a later split-wrapper retention result cannot be explained away as normal GLX loader behavior.

## Negative controls: over-broad / incomplete companion cuts

### Crude v2 — full generated guest output copied resident

The first GL split companion included the complete generated GL guest `.inl` in a NODELETE bridge DSO.

The retained `glGetError` PFN remained callable after logical close, but the wrapper did not physically unload. Forced reservation of its old ranges failed because the mappings still existed.

Representative result:

```text
RETAINED_AFTER_CLOSE error=0
RESERVE_FAIL ... errno=17 File exists
exit=72
```

This is retained as a negative design control: keeping too much generated wrapper machinery resident defeats the intended physical-unload semantics.

### Minimal v3 — signature adapters resident, but wrapper adapter map retained

The next candidate narrowed the companion to:

- generated signature-specific adapters;
- a resident `FEXGLBridgeLookup` table;
- resident fixed callback unpackers;
- a resident GL malloc callback target + unpacker.

The bridge had no static dependency on `libGL.so.1` and its DT_NEEDED set was only C++ runtime/libc.

A PFN-only runtime still failed the physical-unload assertion:

```text
GL_SPLIT_LINK name=glGetError H=0x7ffff73bd680 T=0x7ffff7e90c50
GEN1 ... error=0
T -> libfex-GL-bridge.so
old libGL ranges captured
post-dlclose glXGetProcAddress still -> libGL.so.1
exit=10
```

Run identity:

```text
run: 31783185895
artifact: 9212566570
artifact digest: sha256:b6e371b0a0d5856716fe8d04dde2478cd3c799f08fb302086a3c21df6e4e668a
```

The GLX full-runtime v3 likewise retained the wrapper after `glXGetFBConfigs`; matched stock GLX disproves GLX itself as the cause.

## ELF audit: GNU unique hypothesis falsified

A stock/v3/v4/bridge symbol audit found:

```text
libGL-stock.so      UNIQUE=0
libGL-v3.so         UNIQUE=0
libGL-v4.so         UNIQUE=0
libfex-GL-bridge.so UNIQUE=0
```

No exported `fexcallback_` or `fexthunks_invoke_callback` symbols were present in the final ELFs either.

Therefore the wrapper-retention regression is not explained by `STB_GNU_UNIQUE` process-lifetime semantics.

Audit workflow:

```text
.github/workflows/gl-split-v3-symbol-audit.yml
run: 31783564642
artifact: 9212655694
artifact digest: sha256:8bd5ee0eca6b3c7d5699bf3adff729f1ccb343ebdd6bc84c995c82beb8ff63f1
```

## v4: companion becomes sole dynamic-adapter owner — PASS

The v4 discriminator keeps the minimal resident companion and makes two ownership corrections in the unloadable wrapper:

1. remove the wrapper-local `HostPtrInvokers` map that referenced wrapper-local `GetCallerForHostFunction(...)` adapters;
2. remove the now-unused wrapper-local `malloc_wrapper` callback target, since GL's process-retained GuestMalloc target + unpacker live in the companion.

The wrapper's `glXGetProcAddress` now behaves conceptually as:

```text
native H from host glXGetProcAddress
    -> resident bridge symbol lookup
    -> resident generated adapter T
    -> LinkAddressToFunction(H, T)
```

Unknown host functions without a generated resident adapter are rejected rather than falling back to a wrapper-local adapter table.

### Real PFN-only runtime result

Owned fork workflow:

```text
.github/workflows/gl-split-resident-v4-pfn-arm64.yml
run: 31783476072
job: 94714086455
artifact: 9212669469
artifact digest: sha256:c8f27cf2a9b593fa1f5785a86c2e65c653de43a465fc188b738998ca8452fdb0
```

Exact trace:

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
REAL_GL_SPLIT_V3_PFN_OK
exit=0
```

The success marker retains the older v3 string because the v4 workflow deliberately reuses the same probe binary; the workflow's own final assertion emits `REAL_GL_SPLIT_V4_PFN_OK`.

### Meaning

This proves the resident-companion architecture for a second real generated thunk library's dynamic PFN path:

- stock wrapper physically unloads;
- native `H = glGetError` remains stable;
- resident adapter `T` remains stable;
- old wrapper mappings disappear;
- the retained native PFN remains callable after physical wrapper unload;
- old wrapper ranges can be occupied to force a moved generation;
- the wrapper reloads at a different guest address;
- newly reacquired `glGetError` has the same native H;
- the real call succeeds after reload and again through the retained H.

The key generic design invariant is stronger than merely moving adapters resident:

> the unloadable wrapper must relinquish its own dynamic-adapter ownership/registry when the resident companion becomes authoritative.

## Callback direction status

GL has a stricter callback ownership case than Vulkan:

- Vulkan's fixed X11 unpackers were wrapper-owned, while the actual X11 guest targets belonged to another DSO.
- GL additionally stores a `GuestMalloc` callback whose **target and unpacker** were both originally wrapper-owned.

The minimal GL companion now places that malloc target + unpacker resident as well as the X11 unpackers.

A full v4 runtime gate is running separately to test a retained `glXGetFBConfigs` PFN after physical wrapper unload. That path forces host GL's `RelocateArrayToGuestHeap` to execute the process-retained GuestMalloc trampoline. Guest X11 is pinned independently in that test so X11 DSO ownership does not confound GL-wrapper lifetime.

Do not claim full GL callback-direction success from the PFN-only result above until that full gate is retained.

## Relationship to Vulkan

The GL v4 result independently supports the same architecture already proven much more deeply on Vulkan:

```text
unloadable library-specific wrapper
    -> resident companion owns escaped generic executable glue
```

GL adds a useful caution that Vulkan's first split happened to satisfy already: when the companion becomes authoritative, stale wrapper-local registries that continue referencing old adapter bodies should be removed rather than left as unused parallel ownership state.

## Boundary

All source changes and CI work are diagnostic/research code on owned repository surfaces. No upstream FEX interaction was made. Any upstream implementation must be independently derived and written by a human in compliance with FEX contribution policy.
