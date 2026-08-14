# NODELETE guest-thunk policy edge cases

## Current conclusion

The build-time `DF_1_NODELETE` containment remains a strong near-term lifetime fix for generated guest thunk DSOs. Additional probes show that glibc keeps a NODELETE object fully initialized across `dlclose()`/reopen, real Vulkan guest static state remains usable after close, and the total mapped ELF load-segment cost of every current 64-bit shared guest thunk is modest.

The main concrete policy caveat found so far is glibc `dlmopen(LM_ID_NEWLM)`: NODELETE prevents disposable loader namespaces from being reclaimed, so repeated namespace creation can exhaust glibc's finite namespace slots.

## Real Vulkan static state survives `dlclose()`

Owned-FEX branch `ci/nodelete-vulkan-static-state-20260814`, commit `c3ccaaad5f682e64959e784fcda9fca0f21af6bf`, hosted ARM64 run `31774608843`, job `94687353318`, artifact `9209462909` completed successfully.

The probe uses the real FEX runtime, real Vulkan host thunk, generated NODELETE Vulkan guest wrapper, and ARM64 Lavapipe. It deliberately performs a *new* `vkGetInstanceProcAddr` lookup through the retained guest `vkGetInstanceProcAddr` after ordinary `dlclose()`. This exercises the Vulkan guest wrapper's C++ static proc-address state instead of merely calling a PFN acquired before close.

Trace:

```text
BEFORE_CLOSE gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4 version=4206867
AFTER_DLCLOSE_QUERY_BEGIN
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7ea4400
AFTER_DLCLOSE_QUERY gipa=0x7ffff7ea22b0 pfn_old=0x7ffff76c80f4 pfn_new=0x7ffff76c80f4
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7ea4400
AFTER_REOPEN_QUERY gipa_old=0x7ffff7ea22b0 gipa_new=0x7ffff7ea22b0 pfn=0x7ffff76c80f4
VERSIONS 4206867 4206867 4206867
REAL_NODELETE_VULKAN_STATIC_STATE_OK
```

The wrapper is therefore a live resident object after close, including its proc-address map/state, rather than resident executable text paired with destroyed C++ globals.

## Native glibc NODELETE contract

Owned-FEX branch `ci/agent-q-nodelete-glibc-contract-20260814`, commit `c43bb487d168cf32056f2463d30657bbe60eb437`, run `31774785164`, job `94687873350` completed successfully.

A tiny native ARM64 DSO with constructor/destructor counters was linked with `-z nodelete`. The test showed:

```text
FIRST_LOAD init=1 fini=0
AFTER_DLCLOSE_RETAINED_FN init=1 fini=0
RTLD_NOLOAD handle=<non-null>
AFTER_NOLOAD init=1 fini=0
GLOBAL_PROMOTION default_fn=<same function>
AFTER_GLOBAL_PROMOTION init=1 fini=0
AFTER_FINAL_DLCLOSE init=1 fini=0
NODELETE_GLIBC_CONTRACT_OK
```

After process termination the destructor log contained exactly one line:

```text
fini init=1 fini=1
```

So on the tested glibc loader:

- the constructor runs once;
- intermediate `dlclose()` calls do not run the destructor;
- retained code/data remain live;
- `RTLD_NOLOAD` still finds the object after close;
- a later `RTLD_GLOBAL` open can promote symbol visibility;
- the destructor runs once at process exit.

## Historical FEX unload-control precedent

Merged upstream PR `FEX-Emu/FEX#2583` ("Thunks: Make xcb's callback more robust") is directly relevant to lifetime policy.

The PR removed guest-thunk destructor-driven callback-thread cleanup and moved cleanup onto explicit XCB connection refcounting. Its rationale states that destructors were not reliably called when the shared library was removed. During review, a maintainer asked whether FEX could hook `dlclose()` for manual cleanup. Sonicadvance1 replied that once FEX had redirected the FD used to load the thunk library, FEX lost control of that point and no good workaround had been found.

This is useful historical context for NODELETE: the build-time ELF lifetime flag is enforced by the guest loader after the FD redirection and therefore does not require FEX to recover the `dlclose()` interception point that prior thunk work found unavailable.

The dormant `ThunkLibs/libfex_malloc_loader/Guest.cpp` also contains an explicit `RTLD_NODELETE` guest-side `dlopen`, so process-lifetime guest thunk loading has prior conceptual precedent in the tree.

## Resident wrapper mapping cost

Owned-FEX branch `ci/agent-p-nodelete-footprint-20260814`, commit `07c47237181f3182060bcac255b80ab3290281a2`, hosted ARM64 run `31774993278`, artifact `9209558628` built every current 64-bit shared guest thunk and summed page-rounded PT_LOAD `p_memsz` values.

```text
asound           mapped≈ 260 KiB
vulkan           mapped≈ 300 KiB
drm              mapped≈  36 KiB
wayland-client   mapped≈  40 KiB
VDSO             mapped≈   4 KiB
GL               mapped≈ 956 KiB
EGL              mapped≈  16 KiB
cuda             mapped≈ 188 KiB
--------------------------------
ALL_SHARED_64     mapped≈1.76 MiB
```

The ELF files total about 10.11 MiB on disk in the RelWithDebInfo build, but much of that is file/debug payload outside loadable segments. The page-rounded PT_LOAD total is the more relevant wrapper-mapping estimate.

This is an upper bound only for the generated wrapper ELF mappings if all eight are loaded in one process. Dynamic allocations and dependencies have their own costs, while an application that uses only a subset pins only that subset.

## `dlmopen` namespace caveat

Owned-FEX branch `ci/agent-r-nodelete-dlmopen-20260814`, commit `fc0617083cb13410c1f436d171c8c81fe3dd8142`, run `31775029885`, job `94688589204` compared repeated glibc `dlmopen(LM_ID_NEWLM)` / `dlclose()` cycles for a normal DSO and an otherwise identical NODELETE DSO.

The normal DSO recycled namespaces for all 40 iterations:

```text
COMPLETE path=/tmp/libns-normal.so count=40
```

The NODELETE DSO pinned each new namespace and failed on the sixteenth attempted copy (iteration 15):

```text
FAIL path=/tmp/libns-nodelete.so iteration=15 error=/tmp/libns-nodelete.so: no more namespaces available for dlmopen(): Invalid argument
RESULT normal=40 nodelete=15
```

This is a real semantic cost of a static NODELETE flag. Software that repeatedly creates disposable glibc loader namespaces containing a thunk wrapper can exhaust the finite namespace pool.

No `dlmopen` usage was found in the current FEX source tree or FEX issue search, so the relevance to existing FEX workloads is currently unclear. A real FEX/Vulkan A/B namespace probe is running separately to determine whether thunk loading through `dlmopen` is functional today and whether the native namespace behavior carries through FEX.

## Policy implications

The new evidence supports three useful statements for patch discussion:

1. **Ordinary glibc `dlopen`/`dlclose` semantics are clean under NODELETE for the thunk use case.** State remains initialized, reopen/NOLOAD behavior works, and destructors defer to process exit.
2. **The resident wrapper cost is small for the current thunk set.** Even pinning every current 64-bit shared wrapper is about 1.76 MiB of page-rounded load segments before dynamic allocations.
3. **`dlmopen` is the concrete global-policy caveat.** If namespace recycling is considered supported/important, a base-namespace-only runtime promotion or more selective lifetime policy may be preferable to unconditional `DF_1_NODELETE` on every copy.

The unload-preserving target-cell/retirement design remains the route that can preserve physical unload and namespace reclamation, at substantially greater runtime complexity.

All source/CI changes described here are on owned fork and investigation surfaces. No upstream FEX changes or comments were made during this investigation.
