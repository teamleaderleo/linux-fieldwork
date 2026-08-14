# FEX split resident bridge — selected-before-wrapper-unmap race

Date: 2026-08-14

## Result

The split resident bridge architecture closes the exact selected-before-unmap race that defeats retirement-only physical reclamation.

This experiment reuses the same proven post-selection barrier family from `TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`, but changes the ownership of the selected guest executable target:

```text
old negative control:
  H -> T1 inside unloadable wrapper DSO

split experiment:
  H -> Tbridge inside NODELETE resident bridge DSO
  unloadable wrapper owns registration/state but not Tbridge
```

FEX core product behavior is stock apart from the diagnostic barrier. No H retirement/rebind patch is applied.

Reviewed source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier commit: `4672a1d27e7690bec753b5ca9dfbf58d70fab136`.

Workflow run: `31775790905`.

Artifact: `split-resident-inflight-race-31775790905`.

Artifact digest:

```text
sha256:c83ed4b046a5a8adbeaca71191a188eff54dc6ef515c4bf09aaa74843f6fe1be
```

No upstream FEX interaction was made.

## Forced sequence

The wrapper loads and registers native H to the resident bridge adapter:

```text
H       = 0x7ffff7d80860
Tbridge = 0x7ffff7d7c150
wrapper probe address = 0x7ffff7da2220
```

A worker calls H. The ARM64 `ExitFunctionLink` barrier pauses only after Tbridge has resolved to a host-code pointer and after the lookup/code-invalidation guard has been released:

```text
DIAG_INFLIGHT_SELECTED guest=0x7ffff7d7c150 host=0x80006afc8cf4
split inflight selected          bridge=0x00007ffff7d7c150
```

While the worker owns that already-selected host-code pointer, the main thread final-closes the unloadable wrapper.

The wrapper is confirmed non-executable/unmapped, while the selected bridge target remains resident:

```text
split inflight wrapper unmapped before resume; bridge resident
```

Only then is the worker released:

```text
DIAG_INFLIGHT_RESUME guest=0x7ffff7d7c150 host=0x80006afc8cf4
```

Unlike the wrapper-owned-T1 negative control, the worker returns normally:

```text
split inflight worker returned   rv=23 want=23
```

The process continues.

The former wrapper span is reserved and a fresh wrapper generation is forced to a different guest address:

```text
split inflight reload wrapper    old=0x00007ffff7da2220 new=0x00007ffff7d47220 DIFFERENT
split inflight reload bridge     old=0x00007ffff7d7c150 new=0x00007ffff7d7c150 SAME
```

The fresh generation also works:

```text
split inflight fresh generation rv=35 want=35
SPLIT_INFLIGHT_RESULT selected-resident-bridge-survived-wrapper-unmap
```

Final exit:

```text
0
```

## Direct comparison to the retirement-only negative control

`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md` proves:

```text
worker selects wrapper-owned T1 -> HostCode1
wrapper/T1 is physically unmapped
worker resumes already-selected HostCode1
exit 139
```

That test also proved all-thread H cache retirement cannot revoke the already-selected transfer.

This split experiment proves:

```text
worker selects resident Tbridge -> HostCodeBridge
wrapper is physically unmapped
Tbridge remains mapped
worker resumes the same already-selected HostCodeBridge
returns correctly
```

The barrier location and selection semantics are the same class. The distinguishing change is executable ownership.

Therefore:

> moving escaped/selected bridge executable code out of the unloadable wrapper removes the proven reclamation race without requiring FEX to revoke an already-selected host-code pointer.

## Architecture implication

The split resident bridge is now the strongest demonstrated long-term design family.

It has three layers of evidence:

1. standalone loader model on x86-64 and AArch64, including repeated wrapper cycles;
2. stock-FEX H→T and host→guest callback integration with wrapper physical unload across five forced generations;
3. the exact selected-before-wrapper-unmap race that previously produced exit 139 now returns correctly.

This is stronger than a target cell alone because the final executable adapter itself is resident; there is no last load of a wrapper-owned T that can race wrapper reclamation.

It is also more semantically precise than marking every complete wrapper `NODELETE`: wrapper-specific code/state can still be reclaimed and reinitialized, while only the bridge glue whose addresses escape into process-owned FEX/host state remains resident.

## What remains

The successful fixture manually splits the bridge. A production FEX design still needs generator/build integration.

The likely resident units are already visible in current thunk generation:

- signature-specific `CallHostFunction<...>` adapters used by `GetCallerForHostFunction`;
- fixed `CallbackUnpack<signature>::Unpack` functions used in host→guest trampolines;
- the generated callback-thunk/signature SHA as identity for deduplication/compatibility.

Next gates:

1. generated Vulkan-specific split bridge prototype under stock FEX;
2. real `vkGetInstanceProcAddr` moved-reload PFN test with `libvulkan-guest.so` physically unloading while its resident bridge stays mapped;
3. real Vulkan/X11 callback test with resident unpackers and external X11 targets;
4. then generalize the generator/CMake split across thunk libraries.

This result does not by itself define whether stale H should remain callable after wrapper logical unload. The fixture chooses safe residency. A product policy may layer ACTIVE/REVOKED owner state on top of the resident bridge without making wrapper reclamation depend on revoking already-selected executable code.

All source changes are diagnostic/research code in owned repositories. Any upstream implementation must be independently derived and written by a human in compliance with FEX policy.