# Real generated Vulkan — split resident bridge runtime

Date: 2026-08-14

## Result

The preferred split resident bridge architecture now works on FEX's **real generated Vulkan guest wrapper** under stock FEX core.

The experiment keeps `libvulkan-guest.so` physically unloadable and adds a small guest companion DSO:

```text
libvulkan.so.1                     ordinary unloadable wrapper
  DT_NEEDED -> libfex-vulkan-bridge.so
  RUNPATH   -> $ORIGIN

libfex-vulkan-bridge.so            DF_1_NODELETE resident bridge
  generated signature-specific CallHostFunction adapters
  fixed Vulkan/X11 callback unpackers
```

The wrapper uses resident bridge addresses for dynamic native Vulkan PFNs instead of addresses compiled into `libvulkan-guest.so`.

No FEX core lifetime/retirement patch is applied.

Reviewed stock source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier commit: `3a701fbac78aea15dc6ee92babc6393b33c090ef`.

Workflow run: `31776450982`.

Artifact: `real-vulkan-split-resident-31776450982`.

Artifact digest:

```text
sha256:00a4b9267e13fe66c00924936cec1d72e006b06484f4c14bca6de23255fa5730
```

No upstream FEX interaction was made.

## Build identity

Resident bridge dynamic section includes:

```text
SONAME:  libfex-vulkan-bridge.so
FLAGS_1: NODELETE
```

The generated Vulkan wrapper remains:

```text
SONAME: libvulkan.so.1
NEEDED: libfex-vulkan-bridge.so
RUNPATH: $ORIGIN:...
```

The wrapper itself does **not** carry NODELETE.

## Runtime matrix

The real retained Vulkan PFN probe runs against stock FEX:

```text
hold=0
close=0
reload=0
```

This differs intentionally from the retirement/revocation candidate. Here the old H remains callable after logical wrapper close because its executable adapter is process-resident and generation-neutral.

## Generation 1

The dynamic Vulkan PFN is registered to the resident invoker:

```text
H = 0x7ffff76c80f4
resident invoker = 0x7ffff7e7bcc0

Linking address 0x7ffff76c80f4 to resident host invoker 0x7ffff7e7bcc0
```

The guest Vulkan wrapper itself occupies five mappings around:

```text
0x7ffff7e92000-0x7ffff7ec1000
```

The real Vulkan call works before close:

```text
PROBE call where=before-close pfn=0x7ffff76c80f4 maps=16
PROBE return where=before-close result=0 version=0x403113 maps=16
```

## Physical wrapper unload with retained PFN still callable

After final guest `dlclose(libvulkan.so.1)`:

```text
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
```

The five tracked `libvulkan.so.1` mappings from generation 1 have disappeared. The resident invoker address is outside that old wrapper range.

The probe then calls the **same old PFN** before any wrapper reload:

```text
PROBE about-to-call-stale-pfn=0x7ffff76c80f4
PROBE call where=after-real-close pfn=0x7ffff76c80f4 maps=11
PROBE return where=after-real-close result=0 version=0x403113 maps=11
PROBE stale call unexpectedly returned
```

The final probe line says "unexpectedly" only because the original probe was written to expose the old stale-wrapper failure. Under the split architecture this successful return is the expected result.

Therefore:

> the actual generated Vulkan wrapper is physically gone, while FEX's retained dynamic PFN remains valid because H targets executable glue owned by the resident bridge rather than by the wrapper generation.

## Forced moved wrapper reload

The probe reserves every old wrapper mapping before reopen:

```text
PROBE reserved-old-generation-ranges=5
```

Generation 2 is therefore forced to a different wrapper/GIPA base:

```text
old GIPA = 0x7ffff7eb6ee0
new GIPA = 0x7ffff7685ee0
old PFN  = 0x7ffff76c80f4
new PFN  = 0x7ffff76c80f4
same-pfn = 1
```

Registration again selects the same resident adapter:

```text
Linking address 0x7ffff76c80f4 to resident host invoker 0x7ffff7e7bcc0
```

The generation-2 PFN succeeds:

```text
PROBE call where=after-reload-new-pfn pfn=0x7ffff76c80f4 maps=16
PROBE return where=after-reload-new-pfn result=0 version=0x403113 maps=16
```

Final reload exit is `0`.

## Comparison to stock unsplit Vulkan

The byte-identical-thunk stock/candidate A/B in `REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md` established that ordinary generated Vulkan wrappers fail changed-base reload under stock FEX:

```text
unsplit stock reload = 139
```

The split generated wrapper under the same reviewed stock FEX core produces:

```text
split stock reload = 0
```

Unlike the runtime retirement candidate, the split design does not need to invalidate/recompile/rebind H when only the wrapper generation changes: the native H already points to generation-neutral resident adapter code.

## Relationship to the selected-before-unmap race

The FEX-integrated synthetic split fixture already reran the exact post-selection barrier from the wrapper-owned negative control:

```text
worker selects resident Tbridge -> HostCodeBridge
wrapper physically unmaps
worker resumes the same already-selected host code
returns correctly
```

See `FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`.

This real generated-Vulkan result now closes the separate integration question: the same executable-ownership split can be generated for Vulkan and fixes the real H→T lifetime path under stock FEX.

## Current implementation boundary

This is still research code, not a generalized thunk-generator design.

The Vulkan-only transformer currently:

- extracts generated `MAKE_CALLBACK_THUNK` signature glue into a resident companion DSO;
- extracts Vulkan internal API names and builds resident `GetCallerForHostFunction` adapter addresses;
- changes `MakeGuestCallable` to select resident adapter addresses;
- moves fixed X11 callback unpacker addresses into the resident bridge;
- links the ordinary Vulkan guest wrapper against the bridge with `$ORIGIN` lookup;
- marks only the bridge `NODELETE`.

The next gate is the real retained Vulkan/X11 callback path after wrapper physical unload. After that, the design can be generalized centrally in thunkgen/GuestLibs rather than remaining Vulkan-specific.

## Policy question intentionally left open

This prototype chooses safety by allowing a previously advertised native PFN H to remain callable after logical wrapper close, because its generic adapter is resident and the native host thunk/library remains process-live in current FEX.

A production policy could instead layer ACTIVE/REVOKED owner state on top of the resident adapter if API semantics require stale H rejection. That policy no longer has to make executable wrapper reclamation depend on revoking an already-selected wrapper-owned target.

All source changes are diagnostic/research code on owned surfaces. Any upstream implementation must be independently derived and written by a human in compliance with FEX policy.