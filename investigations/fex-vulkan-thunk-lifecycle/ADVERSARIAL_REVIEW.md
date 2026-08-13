# Adversarial review — FEX Vulkan guest-thunk unload

## Scope

This review attacks the second finding in this investigation: the teardown SIGSEGV that appears after the separate Vulkan callback-routing SIGILL has been avoided.

Internal context:

- [linux-fieldwork #669](https://github.com/teamleaderleo/linux-fieldwork/pull/669)
- [linux-fieldwork #672](https://github.com/teamleaderleo/linux-fieldwork/issues/672)
- executed FEX revision: `FEX-2608` / `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- current-main source review used for comparison: `71afe476751deac24adabd1adb575fd2337b6e0a`

FEX upstream remains read-only. This file records source review, competing explanations, and local/owned-repository experiment design. It is investigation evidence, not contribution code.

## Bottom line

The broad hypothesis **“FEX retains thunk execution state after `libvulkan-guest.so` unload”** survives review, but it is too broad to serve as the immediate-cause diagnosis.

The strongest current immediate-cause hypothesis is narrower:

> A dynamically returned native Vulkan PFN remains registered as a FEX CustomIR entry whose target is a guest `CallHostFunction` body inside `libvulkan-guest.so`; the guest DSO unloads, the registration survives, and a later call through that native PFN dispatches to the old guest target.

That hypothesis is strongly supported by FEX source and history, but the decisive runtime edge is still missing. The existing crash proves the dead destination and the unload dependency. It does not yet prove that the final transition into the dead destination came through `CustomIRHandlers`.

The clean proof is a four-event trace:

```text
REGISTER host_pfn=H -> guest_target=T
UNMAP    libvulkan-guest range containing T
CUSTOMIR HIT guest_rip=H -> guest_target=T, target unmapped
FAULT     guest RIP T
```

A crash at `T` with no post-unload CustomIR hit at `H` would directly disprove stale CustomIR as the immediate cause and redirect the investigation toward a stale guest pointer, stale callback trampoline, or another late teardown edge.

## Existing evidence that must be preserved

After the callback-routing diagnostic change, x86-64 `vulkaninfo --summary` completes enumeration and then exits `139` during teardown. The same failure occurs with llvmpipe, removing Venus/virtio-gpu from the minimum failure path.

At the terminal fault, FEX records an x86 instruction-fetch page fault. The saved guest RIP is `0x7ffff7cd21f0`. At crash time that address is unmapped. Treating `0x7ffff7c87000` as the former `libvulkan-guest.so` base yields offset `0x4b1f0`, which resolves into a generated `CallHostFunction<...>` body from `ThunkLibs/include/common/Guest.h`.

The unload controls remain strong:

| Variant | Result |
| --- | --- |
| normal post-callback-fix run | enumeration succeeds, exit 139 |
| guest `dlclose()` replaced by no-op | exit 0 |
| bogus/nonexistent preload | exit 139 |
| only `libvulkan-guest.so` pinned | exit 0 |
| pinned guest thunk with Venus enabled | exit 0; Venus enumerated |

These controls prove that retaining the Vulkan guest thunk rescues the failing run. They do not identify which retained reference would otherwise target it after unload.

## Strongest evidence against stale CustomIR as immediate cause

### 1. The fault identifies a destination, not the dispatch mechanism

The old `CallHostFunction` address can be reached through more than one failure class:

- a stale CustomIR host-PFN registration;
- a stale direct guest function pointer;
- stale translated guest code or a lookup-cache entry;
- a stale host-to-guest trampoline or callback helper that later branches into guest thunk code;
- Vulkan teardown code retaining a guest-side address longer than the guest loader keeps the DSO mapped.

Pinning `libvulkan-guest.so` repairs all of those classes because the old address remains executable. Therefore the pinning control localizes lifetime, not ownership.

### 2. FEX has a second independent stale thunk-state class

In `Source/Tools/LinuxEmulation/Thunks.cpp`, FEX caches host-callable trampolines in `GuestcallToHostTrampoline`, keyed by `{GuestUnpacker, GuestTarget}`. Each trampoline embeds `GuestUnpacker` and `GuestTarget` addresses. The cache has no visible DSO lifetime key or unload erasure.

FEX-2608 Vulkan guest initialization creates host-to-guest trampolines for X11-related functions from `OnInit()` using callback unpackers instantiated in the Vulkan guest DSO. Therefore a `libvulkan-guest.so` unload can also leave a host trampoline containing guest addresses from the old image.

This is a real generic lifetime hazard independent of CustomIR.

Its fit to the observed crash is weaker because the recorded dead RIP resolves to `CallHostFunction`, which is the dynamic host-PFN caller path. A stale callback trampoline would more naturally first target a `CallbackUnpack` body. That distinction should be measured directly.

### 3. Ordinary invalidation has not yet been exhaustively demonstrated in the reproducer

FEX's guest `munmap` path is designed to invalidate translated guest code over the unmapped range when SMC checking is enabled. However, #669 did not retain a trace proving the exact ranges invalidated for every `libvulkan-guest.so` mapping, nor an explicit cache/SMC experiment matrix.

Until those controls are executed, ordinary JIT/lookup invalidation remains a live alternative even though the source makes it less likely.

## Strongest evidence supporting stale CustomIR

### 1. Vulkan dynamic PFNs are wired exactly through CustomIR

At FEX-2608, `ThunkLibs/libvulkan/Guest.cpp` implements dynamic Vulkan function pointers as follows:

1. guest `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr` invokes the host thunk;
2. the returned value is a native host Vulkan function pointer;
3. `MakeGuestCallable()` finds the matching guest `CallHostFunction` invoker in `HostPtrInvokers`;
4. `LinkAddressToFunction(host_pfn, guest_invoker)` registers the mapping with FEX;
5. the native host pointer itself is returned to guest code.

Source: `https://redirect.github.com/FEX-Emu/FEX/blob/e869aa644a16e4332cdc15c1ea0b4d13d482385d/ThunkLibs/libvulkan/Guest.cpp`.

This means the application-visible PFN is normally the host address. The hidden guest `CallHostFunction` target lives in FEX's registration state. The observed dead RIP resolving to `CallHostFunction` is therefore a strong fingerprint for the dynamic-PFN machinery.

### 2. `AddThunkTrampolineIRHandler` stores host-address -> guest-thunk-address state

On the FEXCore side, `LinkAddressToGuestFunction` calls `AddThunkTrampolineIRHandler(original_callee, target_addr)`. That function creates a CustomIR entry keyed by the host function address and captures the guest thunk entrypoint. When FEX later sees the host address as guest RIP, the generated CustomIR exits to the guest thunk target.

FEX-2608 checks `CustomIRHandlers` before normal guest decoding.

Current implementation/history:

- `https://redirect.github.com/FEX-Emu/FEX/pull/1770` introduced generic CustomIR entrypoints and explicitly paired `AddCustomIREntrypoint` with `RemoveCustomIREntrypoint`.
- `https://redirect.github.com/FEX-Emu/FEX/pull/1760` introduced guest-callable host function pointers for APIs including `vkGetDeviceProcAddr` and `glXGetProcAddress`; its design notes explicitly considered unregistering host pointers on `dlclose`.
- `https://redirect.github.com/FEX-Emu/FEX/commit/8b14bd4e87e5b91a018be1030178d63e351a1e80` fixed `RemoveCustomIREntrypoint` in 2025 and described it as `Unused` in the commit message.
- current-main code search still finds the remover implementation but no thunk-library unload owner calling it.

That history is unusually aligned with the observed failure: the mechanism has a removal operation, the dynamic-PFN feature identified `dlclose` cleanup as a design concern, and the remover later remained unused.

### 3. A changed guest base creates a specific stale-registration collision

`AddThunkTrampolineIRHandler` associates one host address with one guest target. FEX also has an explicit warning path for a host address already linked to a different guest thunk target.

If a native Vulkan PFN remains stable across guest DSO reload while `libvulkan-guest.so` moves to a different base, a fresh lookup will naturally attempt:

```text
same host PFN H -> new guest invoker T2
```

while the old registration still contains:

```text
H -> old guest invoker T1
```

That is a highly discriminating prediction of the stale-CustomIR theory.

## Competing explanations

### A. Ordinary guest-loader stale pointer

A guest component may retain a direct address into `libvulkan-guest.so` after `dlclose`.

Evidence for: this naturally produces an instruction-fetch fault in the old DSO range and is repaired by pinning.

Evidence against: dynamic Vulkan PFNs exposed by FEX are native host addresses; the `CallHostFunction` guest address is hidden behind the FEX registration. A direct stale guest pointer to that hidden wrapper needs a concrete provenance.

Discriminator: record the branch/caller immediately before the dead guest RIP. A post-unload CustomIR hit strongly rejects this alternative. No CustomIR hit plus a normal guest branch/call to the old address supports it.

### B. Stale host-to-guest callback trampoline

FEX's generic callback trampoline cache can retain guest unpacker/target addresses across guest DSO unload.

Evidence for: source-level lifetime omission exists; Vulkan `OnInit()` allocates such trampolines.

Evidence against: expected first guest destination is `CallbackUnpack`, while the observed RIP resolves to `CallHostFunction`.

Discriminator: locally remove Vulkan's `Vulkan_SetGuestX*` registration while retaining dynamic PFN mapping. If the crash and `CallHostFunction` fingerprint survive unchanged, callback trampolines are effectively eliminated from this reproducer.

### C. Ordinary JIT / lookup-cache stale block

Translated code for the guest thunk may survive `munmap`, or a lookup cache may still select it.

Evidence for: any emulator can fail at this boundary; the current record lacks exact per-range invalidation logs.

Evidence against: FEX's `GuestMunmap` path explicitly invalidates guest code ranges under normal SMC modes. Persistent code caching is disabled by default in FEX-2608, and the L2 lookup cache defaults disabled.

Discriminator: explicit SMC/cache matrix plus exact invalidation logging. If `mtrack`/`full` clear the entire old DSO range and a later CustomIR hit still jumps back into it, ordinary JIT invalidation is eliminated.

### D. Code-cache relocation bug

A serialized block may contain a guest-address dependency that is relocated incorrectly across DSO bases.

Evidence for: FEX has substantial relocation machinery and historical fixes in this area.

Evidence against: FEX-2608 `EnableCodeCachingWIP` defaults false. The existing reproducer therefore does not naturally point at persistent code caching.

Discriminator: reproduce with code caching explicitly disabled and a fresh cache directory, then enable code caching plus validation and repeat at a forced changed base.

### E. Vulkan-specific teardown behavior

The Vulkan loader/application may invoke a cached PFN during final teardown after the guest thunk DSO has been released.

This can coexist with stale CustomIR: Vulkan-specific ordering can explain **why an old PFN is consumed**, while CustomIR explains **why consuming that PFN reaches unmapped guest code**.

Discriminator: identify the exact late PFN and caller, then reproduce the same lifetime pattern in another thunk library.

### F. Generic thunk-library lifetime bug

This is strongly supported as a class even before another reproducer exists. The dynamic function-pointer registration mechanism is shared by other thunk libraries, and the host-to-guest callback trampoline cache is generic.

A useful historical precedent is xcb:

- `https://redirect.github.com/FEX-Emu/FEX/issues/2369` records a thunk teardown problem caused by library-lifetime cleanup assumptions.
- `https://redirect.github.com/FEX-Emu/FEX/pull/2583` replaced destructor-dependent xcb cleanup with explicit resource lifetime. Review discussion there asks about hooking `dlclose` for generic cleanup; the response records that FEX had lost control of the unload after thunk FD redirection and had no good workaround at that point.

That precedent does not prove the current Vulkan mechanism, but it makes generic thunk-lifetime ownership a credible defect family.

## Discriminating experiment plan

### Experiment 1 — direct CustomIR causal trace

Instrument a local FEX-2608 tree at:

- `AddThunkTrampolineIRHandler` / `AddCustomIREntrypoint`;
- `GuestMunmap`;
- the `CustomIRHandlers.find(GuestRIP)` hit in `GenerateIR`;
- guest fault reporting.

For each thunk CustomIR entry retain:

```text
host entrypoint
captured guest target
creator
symbol/library label where available
registration sequence number
```

At `GuestMunmap`, report every registration whose guest target lies in the unmapped range.

At CustomIR dispatch, report whether the saved guest target is currently mapped/executable.

Results:

| Result | Interpretation |
| --- | --- |
| `REGISTER -> UNMAP target -> CUSTOMIR HIT -> dead target` | stale CustomIR immediate cause established |
| dead target reached with no post-unload CustomIR hit | stale CustomIR immediate cause disproved |
| CustomIR hit points to a live/new target | investigate ordinary guest pointer/JIT path |

### Experiment 2 — forced changed-base reload

Build a minimal x86-64 harness that repeatedly:

1. `dlopen("libvulkan.so.1")`;
2. obtains one known function through `vkGetInstanceProcAddr`;
3. calls it;
4. records guest thunk mappings and the native PFN;
5. `dlclose`s Vulkan;
6. reserves the former guest-thunk range with `MAP_FIXED_NOREPLACE`;
7. reloads Vulkan at a different base;
8. reacquires the same PFN and calls it.

Record:

```text
old guest base / new guest base
old guest invoker / new guest invoker
old native PFN / new native PFN
CustomIR contents before unload / after unload / after reload
```

Critical outcomes:

- same native PFN, moved guest invoker, old `H -> T1` registration retained, second call reaches `T1`: stale CustomIR essentially proved;
- fresh reacquired PFN works at the new base and registration updates to `T2`: major evidence against the leading theory;
- only same-base reuse works: address reuse is masking a lifetime bug;
- only code-cache-on breaks: code-cache relocation class rises sharply.

### Experiment 3 — native PFN stability

Log native `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr` results across unload/reload.

- stable host PFN means a new guest DSO naturally collides with an old CustomIR key;
- changed host PFN means a fresh lookup gets a new key, so the failing teardown must involve an old PFN retained somewhere.

This also helps identify the late caller.

### Experiment 4 — remove callbacks, keep dynamic PFNs

Locally disable the three Vulkan `OnInit()` host-to-guest X11 trampoline registrations while leaving `MakeGuestCallable` and `LinkAddressToFunction` untouched.

Expected interpretation:

- unchanged teardown crash at a dead `CallHostFunction`: callback-trampoline class strongly eliminated;
- crash disappears: inspect X11 callback trampoline lifetime first.

### Experiment 5 — remove dynamic PFN usage, keep callbacks

Use a minimal Vulkan load/use/unload harness that avoids dynamically returned PFNs after initialization while leaving callback trampoline setup intact, or locally route a known tested API directly so the dynamic PFN registration is absent.

- clean unload/reload with callbacks still present: dynamic-PFN state becomes dominant;
- crash persists with no dynamic PFN registration: CustomIR dynamic-PFN theory fails for that reproducer.

### Experiment 6 — exact `GuestMunmap` invalidation coverage

Log:

```text
munmap request
aligned actual range
resource / guest DSO mapping
InvalidateCodeBuffersCodeRange range
InvalidateThreadCachedCodeRange range for every thread
lookup entries removed
```

Compare against every executable `PT_LOAD` range from the guest Vulkan thunk.

Run at least:

```text
FEX_SMCCHECKS=mtrack
FEX_SMCCHECKS=full
FEX_SMCCHECKS=none
```

A failure invariant under `mtrack` and `full`, with complete old-image invalidation demonstrated, materially weakens ordinary stale translated code. A failure only under `none` points toward normal invalidation behavior instead.

### Experiment 7 — code-cache controls

Explicit cache-off run:

```text
FEX_ENABLECODECACHINGWIP=0
FEX_ENABLELAZYCODECACHINGWIP=0
FEX_DISABLEL2CACHE=1
```

Use a fresh/empty cache location as an additional receipt.

Then deliberately enable code caching and validation and repeat the changed-base run.

If the same post-unload CustomIR hit occurs with persistent caching off and on, code-cache relocation ceases to be a useful primary explanation.

### Experiment 8 — repeated unload/reload and address reuse

Run tens or hundreds of load/PFN-call/unload cycles while recording bases and PFNs.

Split results by:

- exact same guest base reused;
- partially overlapping base;
- changed base;
- same native PFN;
- changed native PFN.

A bug that disappears under same-base reuse and reappears under changed-base reload is classic evidence of a stale address registration.

### Experiment 9 — identify the exact late PFN

Record symbol name together with each dynamic PFN registration in `MakeGuestCallable`.

At the first post-unload CustomIR hit capture:

```text
host PFN
Vulkan symbol name
guest caller RIP
saved guest target
unload sequence number
backtrace / call-ret information available at that point
```

This closes the narrative gap between “Vulkan is unloading” and “this specific cached function pointer was invoked after the guest thunk disappeared.”

### Experiment 10 — generic thunk counterexample with libGL

Current FEX libGL uses the same `indirect_guest_calls` mechanism for functions returned by `glXGetProcAddress`.

Source: `https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libGL/libGL_interface.cpp`.

Build an x86 harness that:

1. loads the thunked GL library;
2. obtains a safe known function through `glXGetProcAddress`;
3. calls it;
4. unloads;
5. blocks the old guest DSO range;
6. reloads at a new base;
7. reacquires and calls the PFN.

If a stable native GL PFN remains mapped to the old guest invoker, the defect is generic dynamic-function-pointer thunk lifetime with no Vulkan teardown dependency.

libcuda is another candidate using the same generator class:

`https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libcuda/libcuda_interface.cpp`.

## What the existing experiments already eliminate

### Eliminated or strongly reduced

- **Venus-specific behavior:** llvmpipe reproduces exit 139.
- **native `vkDestroyDebugReportCallbackEXT` as the terminal fault:** instrumented native destroy returns before the final crash.
- **generic `LD_PRELOAD` warning effects:** bogus preload preserves exit 139 while real no-op `dlclose` changes the result.
- **an arbitrary unrelated DSO being the essential resident object:** pinning only `libvulkan-guest.so` repairs the run.
- **the original SIGILL and final SIGSEGV being a single failure:** the callback-routing change removes the first failure and exposes a later teardown fault after enumeration completes.

### Still open

- CustomIR versus ordinary stale guest pointer;
- CustomIR versus host-to-guest callback trampoline lifetime;
- complete ordinary JIT/lookup invalidation coverage;
- address-reuse masking;
- native Vulkan PFN stability;
- exact late Vulkan PFN/caller;
- generic reproduction outside Vulkan.

## Relevant FEX history

### Dynamic function-pointer thunking

`https://redirect.github.com/FEX-Emu/FEX/pull/1760`

This introduced generic support for calling host function pointers from guest code, explicitly naming Vulkan and GL use cases. Its design notes include unregistering host pointers on `dlclose` as a considered concern.

### CustomIR entrypoints

`https://redirect.github.com/FEX-Emu/FEX/pull/1770`

This introduced generic CustomIR entrypoints with both add and remove operations. Dynamic host-PFN thunking later uses this mechanism to intercept the native pointer value and jump into the generated guest caller.

### Unused remover fix

`https://redirect.github.com/FEX-Emu/FEX/commit/8b14bd4e87e5b91a018be1030178d63e351a1e80`

The 2025 commit message explicitly says `RemoveCustomIREntrypoint` was unused while fixing its invalidation behavior. FEX-2608 includes the fixed remover, but source review found no thunk unload path invoking it.

### Prior thunk unload/lifetime failure

- `https://redirect.github.com/FEX-Emu/FEX/issues/2369`
- `https://redirect.github.com/FEX-Emu/FEX/pull/2583`

xcb previously hit a teardown/lifetime problem because required cleanup could not rely on DSO destructor behavior. The eventual fix tied callback-thread lifetime to live xcb connections. Review discussion explicitly raised generic `dlclose` cleanup and documented the difficulty of regaining control after thunk-library FD redirection.

### Code-cache relocation history

FEX has active and historical work around code-cache relocation correctness, including recent fixes and validation machinery. That makes relocation a legitimate control category, but FEX-2608 persistent code caching defaults off, so it currently fits the observed failure less well than the thunk-lifetime mechanisms.

## Vulkan-specific versus generic

Current classification:

- **observed reproducer:** Vulkan-specific;
- **suspected dynamic-PFN lifetime mechanism:** generic;
- **host-to-guest callback lifetime hazard:** generic;
- **proven cross-library reproducer:** absent so far.

Vulkan is especially likely to expose the issue because runtime PFNs from `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr` are normal API usage and may be cached until teardown. A generic lifetime omission can therefore first present as a Vulkan teardown crash.

The libGL changed-base reload experiment is the preferred counterexample before describing the defect itself as generic in any human-facing upstream report.

## Confidence

Current confidence after adversarial review:

| Claim | Confidence |
| --- | ---: |
| guest Vulkan thunk unload is causally necessary for this observed crash | 97% |
| some FEX/thunk state survives the unload and can refer to guest-thunk addresses | 95% |
| stale dynamic-PFN CustomIR is the immediate dispatch mechanism | 80% |
| underlying lifetime defect class is generic across thunk libraries | 75% |
| persistent code-cache relocation is the primary cause | <10% |

These numbers are investigation judgments, not statistical measurements.

## Exact remaining gap

The single largest missing fact is:

> No retained runtime trace yet shows a native host Vulkan PFN hitting `CustomIRHandlers` after `libvulkan-guest.so` has been unmapped and that handler selecting the dead `CallHostFunction` target.

The next local experiment should target that gap before attempting a source fix. A changed-base reload with a freshly reacquired PFN is the strongest independent attack on the theory.

If both tests succeed in the predicted direction — post-unload CustomIR hit plus stable host PFN/new guest target collision — the alternatives above are reduced as follows:

- ordinary guest-loader stale pointer: eliminated as the immediate dispatch edge;
- host-to-guest callback trampoline: eliminated for the observed `CallHostFunction` fault;
- ordinary JIT / lookup-cache failure: eliminated if old guest code ranges were fully invalidated first;
- code-cache relocation: eliminated if reproduced with persistent caching explicitly disabled;
- Vulkan-specific teardown: retained only as the trigger that consumes the stale PFN;
- generic thunk-library lifetime: strengthened, then proven only after a second thunked library reproduces the same changed-base behavior.

## Upstream boundary

FEX upstream actions for this investigation remain read-only: zero issues, comments, PRs, reactions, reviews, pushes, discussions, or other mutations.

Experimental instrumentation and competing local fixes belong in local trees or owned repositories. Any eventual FEX contribution code must be independently produced by a human in compliance with FEX's contribution policy.