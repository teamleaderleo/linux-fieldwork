# Exact FEX-2608 — real generated Vulkan PFN lifetime runtime

Date: 2026-08-14

## Scope

This run repeats the real generated-Vulkan PFN lifetime candidate on the exact FEX source revision used by the original Apple M5 investigation:

```text
e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

Owned-FEX carrier branch: `ci/vulkan-pfn-lifetime-fex2608-20260814`.

Carrier commit: `f04c97fe5750de9e1f7082fb73ab47ba4209e8d6`.

Workflow run: `31774236382`.

Artifact: `vulkan-pfn-lifetime-fex2608-31774236382`.

Artifact digest:

```text
sha256:993c9e507934bebdbea30ef156aa6602dc93b34cd9257cc1e45cbad6803058a6
```

No upstream FEX interaction was made.

## Matrix

```text
hold=0
close=139
reload=0
```

`hold` keeps an extra guest Vulkan DSO reference and proves the dynamic PFN remains valid while the old wrapper generation is still mapped.

`close` final-closes the wrapper and then calls the stale PFN. The research candidate keeps the native H value as a synthetic revoked entry, so the stale use still fails rather than being silently rebound or decoded as ordinary guest bytes.

`reload` final-closes generation 1, reserves all former guest Vulkan mappings to force generation 2 to move, reloads Vulkan, reacquires the dynamic PFN through real `vkGetInstanceProcAddr`, and calls it successfully.

## Real Vulkan transition

Generation 1:

```text
H  = 0x7ffff76c80f4
T1 = 0x7ffff7ea4400
gipa1 = 0x7ffff7ea22b0
```

Before close:

```text
PROBE return where=before-close result=0 version=0x403113
```

Final generation-1 retirement records:

```text
DIAG_MULTI_DROP H=0x7ffff76c80f4 T=0x7ffff7ea4400 ...
DIAG_MULTI_RETIRE H=0x7ffff76c80f4 OLD=0x7ffff7ea4400 NEW=0
DIAG_MT_SHARED H=0x7ffff76c80f4 erased=1
DIAG_MT_THREAD H=0x7ffff76c80f4 ...
DIAG_REVOKED_H_INSTALL H=0x7ffff76c80f4
DIAG_LOCKED_RETIRE H=0x7ffff76c80f4 ...
```

The old guest Vulkan mappings are then reserved before reopen.

Generation 2 moves:

```text
gipa2 = 0x7ffff76712b0
T2    = 0x7ffff7673400
H     = 0x7ffff76c80f4
same-pfn=1
```

The candidate reactivates the stable native H against T2:

```text
DIAG_REVOKED_H_ACTIVATE H=0x7ffff76c80f4 T=0x7ffff7673400 ...
DIAG_MULTI_ACTIVE H=0x7ffff76c80f4 T=0x7ffff7673400
```

The reacquired real Vulkan PFN then succeeds:

```text
PROBE call where=after-reload-new-pfn pfn=0x7ffff76c80f4
PROBE return where=after-reload-new-pfn result=0 version=0x403113
```

## Meaning

The real generated-Vulkan H→T generation-handoff result is not specific to the later reviewed source snapshot. The same candidate behavior executes successfully on exact FEX-2608, the revision used in the original M5 debugging session.

Together with [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md), this establishes:

- the stock moved-generation failure on a real generated Vulkan dynamic PFN;
- successful explicit H retirement/revocation/rebind on current reviewed source;
- the same successful real-Vulkan candidate behavior on exact FEX-2608.

This does **not** make the candidate a complete physical-unload repair. [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md) proves a thread that already selected old-generation host code can outlive cache/definition retirement and fault after physical unmap. A complete reclamation design still needs execution draining, hazard/lease semantics, a process-resident executable bridge, or an equivalent rule.

The original Apple M5 teardown also still lacks its immediate terminal H/R11 capture. The hosted real-Vulkan result proves the generic mechanism and its repair behavior without rewriting that historical evidence boundary.

All implementation code in this experiment is diagnostic/research code in owned repositories. FEX contribution policy requires any upstream implementation to be independently derived and written by a human.