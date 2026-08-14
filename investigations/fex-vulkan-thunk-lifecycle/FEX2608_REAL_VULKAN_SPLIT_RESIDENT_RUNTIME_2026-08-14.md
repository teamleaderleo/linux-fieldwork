# Exact FEX-2608 — real Vulkan split resident bridge runtime

Date: 2026-08-14

## Result

The real generated-Vulkan split resident bridge architecture also passes on the exact FEX source revision used in the original Apple M5 investigation:

```text
e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

No FEX core lifetime/retirement patch is applied. The generated Vulkan wrapper is changed so that executable signature glue whose addresses escape wrapper lifetime lives in a small `NODELETE` companion DSO while `libvulkan.so.1` remains physically unloadable.

Owned-FEX branch: `ci/vulkan-pfn-lifetime-fex2608-20260814`.

Carrier commit: `503a3bab7d4ab856e063186a4b205ba5d05ddf4d`.

Workflow run: `31777023718`.

Artifact: `real-vulkan-split-fex2608-31777023718`.

Artifact digest:

```text
sha256:e87349859cb97b5679ee33ecf5dc0651d1484718fac43e8404283f9f6dfaf07a
```

No upstream FEX interaction was made.

## Matrix

```text
hold=0
close=0
reload=0
```

## Generation 1

The real dynamic Vulkan PFN is linked to the resident bridge adapter:

```text
H = 0x7ffff76c80f4
resident invoker = 0x7ffff7e7bcc0

Linking address 0x7ffff76c80f4 to resident host invoker 0x7ffff7e7bcc0
```

The guest wrapper containing GIPA has exactly five tracked mappings:

```text
0x7ffff7e92000-0x7ffff7e9e000
0x7ffff7e9e000-0x7ffff7eb8000
0x7ffff7eb8000-0x7ffff7ebf000
0x7ffff7ebf000-0x7ffff7ec0000
0x7ffff7ec0000-0x7ffff7ec1000
```

The PFN works before final close:

```text
PROBE return where=before-close result=0 version=0x403113 maps=16
```

## Wrapper physically unloads while H remains callable

After final guest `dlclose(libvulkan.so.1)`:

```text
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
```

The tracked wrapper mappings are gone. The resident bridge remains outside the retired wrapper range.

The same old PFN then succeeds before any wrapper reload:

```text
PROBE call where=after-real-close pfn=0x7ffff76c80f4 maps=11
PROBE return where=after-real-close result=0 version=0x403113 maps=11
```

This is the expected split-bridge behavior even though the original unsplit probe labels the return as "unexpected".

## Forced moved reload

All five former wrapper ranges are reserved:

```text
PROBE reserved-old-generation-ranges=5
```

Generation 2 therefore moves:

```text
old GIPA = 0x7ffff7eb6ee0
new GIPA = 0x7ffff7685ee0
old PFN  = 0x7ffff76c80f4
new PFN  = 0x7ffff76c80f4
same-pfn = 1
```

The same resident adapter remains the target:

```text
Linking address 0x7ffff76c80f4 to resident host invoker 0x7ffff7e7bcc0
```

The generation-2 real Vulkan call succeeds:

```text
PROBE return where=after-reload-new-pfn result=0 version=0x403113 maps=16
```

Final reload exit is `0`.

## Meaning

This removes revision interpolation from the split architecture's real Vulkan PFN proof.

The exact FEX-2608 codebase used for the original M5 debugging session can run the generated split Vulkan wrapper under stock FEX core with:

- physical `libvulkan-guest.so` wrapper unload;
- a process-resident signature bridge;
- retained real native PFN calls after wrapper close;
- forced moved wrapper reload;
- stable native H and stable resident adapter across generations.

Together with `REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md` and `FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`, this makes the split resident bridge the strongest currently demonstrated long-term architecture for the lifetime defect.

The remaining generated-Vulkan bridge-direction gate is retained host→guest X11 callbacks after exact wrapper physical unload.

All source changes are diagnostic/research code on owned surfaces. Any upstream implementation must be independently derived and written by a human in compliance with FEX policy.