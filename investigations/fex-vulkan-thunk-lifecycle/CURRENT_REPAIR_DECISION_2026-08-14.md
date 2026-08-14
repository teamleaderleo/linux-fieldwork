# Current repair decision — FEX guest-thunk lifetime

Date: 2026-08-14

## Decision summary

The unload investigation has advanced beyond a stale-CustomIR hypothesis and now distinguishes **generation rebinding** from **physical executable reclamation**.

The current evidence supports five separate statements:

1. **A real generated-Vulkan dynamic-PFN lifetime defect is proven.** A stock/candidate A/B with byte-identical generated Vulkan thunks changes forced moved reload from stock exit `139` to candidate exit `0` by changing only FEX runtime lifetime handling. See [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).
2. **Exact retirement/revocation fixes stale future dispatch and generation rebinding, but not physical reclamation by itself.** A worker that already selected old-generation host code can resume after handler/cache retirement and physical unmap, then fault. See [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md).
3. **Whole-wrapper residency (`NODELETE`) is the smallest fully demonstrated containment, and its runtime evidence is now generic beyond Vulkan.** Real generated-Vulkan tests cover retained dynamic PFNs and Vulkan/X11 callbacks after ordinary `dlclose()`. A real generated-GL test independently carries `glXGetProcAddress("glGetError")` through 256 close/reopen cycles with stable guest and native PFN addresses and successful post-close calls. See [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md), [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md), and [`NODELETE_REAL_GL_PFN_RUNTIME.md`](./NODELETE_REAL_GL_PFN_RUNTIME.md).
4. **NODELETE keeps one initialized Vulkan guest generation rather than rerunning guest construction against persistent host state.** A 256-cycle churn run records `VULKAN_ONINIT_COUNT=1` while the same native H and guest invoker T are repeatedly reacquired. See [`NODELETE_VULKAN_CONSTRUCTOR_CHURN_RUNTIME.md`](./NODELETE_VULKAN_CONSTRUCTOR_CHURN_RUNTIME.md).
5. **A split process-resident bridge is now the strongest demonstrated long-term architecture.** Under stock FEX, the unloadable wrapper can physically disappear while only escaped bridge glue remains resident; retained H and callback paths continue to work across repeated wrapper generations, and the exact selected-before-wrapper-unmap race that previously exited `139` now returns correctly. See [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md) and [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

Therefore the lock-clean/revoked-H implementation remains a **research proof of required lifetime mechanics and successful generation rebinding**, while whole-wrapper NODELETE is the best-supported near-term containment and the split bridge is the preferred architecture for preserving physical wrapper unload without the proven reclamation race.

## What is proven on the H→T path

For a native host PFN `H` and guest thunk invoker `T`:

```text
H is stable across guest-wrapper generations
T belongs to the current guest-wrapper mapping generation
```

The real Vulkan A/B uses `vkGetInstanceProcAddr(NULL, "vkEnumerateInstanceVersion")` through FEX's generated Vulkan guest/host thunks.

Observed:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

Generation 2 reuses the same native PFN while the guest Vulkan wrapper and guest invoker move. Stock accepts the second registration but the newly reacquired PFN still crashes. The candidate retires old H execution state, leaves H synthetically revoked, then reactivates H against the new guest invoker and the real Vulkan call returns successfully.

The generated Vulkan guest and host thunk hashes are identical across the stock/candidate phases. The discriminator is in FEX runtime state, not generated thunk code.

The same candidate behavior also passes on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`; see [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md).

The real GL NODELETE stress adds a second product dynamic-PFN family. Through FEX's generated GL guest/host thunks:

```text
guest glXGetProcAddress = 0x7ffff7bb8250
native glGetError PFN  = 0x7ffff73bd680
```

remain stable across 256 logical close/reopen cycles, and the original PFN remains callable after every `dlclose()`.

This does not replace the Vulkan moved-reload stock/candidate A/B; it shows that the process-residency containment matches the generic H→T mechanism outside Vulkan.

## Required mechanics for an owner-aware retirement design

These remain useful even if the final architecture uses resident bridge glue.

### 1. Explicit owner lifetime

Any FEX-retained guest executable address that can still belong to an unloadable generation needs mapping/load ownership rather than process-lifetime pointer semantics.

Raw target range matching is sufficient for diagnostics. A production owner token can use or extend FEX's existing mapped-resource/load identity.

### 2. Synthetic H state must survive retirement

A native host PFN previously advertised to the guest must not silently become an ordinary guest RIP after owner retirement.

A useful state model is:

```text
UNKNOWN -> ACTIVE(H,T,owner,signature) -> REVOKED(H,signature) -> ACTIVE(H,T2,...)
```

A stale H call should take a controlled synthetic rejection/fault path rather than decode native ARM bytes as x86. The revoked-H runtime proof demonstrates this.

### 3. Future lookup state must be retired across every thread when T changes

For baked H→T blocks, current-thread-only invalidation is insufficient. Retirement must remove:

- the CustomIR definition/current target claim;
- shared compiled/direct-link state for H;
- H from every live emulation thread's hot lookup cache.

The coherent lock order must follow the existing invalidation direction rather than call the old CustomIR remover under an inverted lock order.

### 4. Multi-owner H claims must not be discarded

Two live guest owners can claim the same native H. Keeping only the first claim loses the second owner when the first unloads.

A same-signature runtime fixture proves retaining compatible claims and promoting a surviving claim works. FEX's existing generated thunk/signature hash is the preferred compatibility identity. See [`THUNK_SIGNATURE_IDENTITY.md`](./THUNK_SIGNATURE_IDENTITY.md).

### 5. Host→guest callbacks require independent lifetime handling if their guest addresses can unload

The preferred revocable representation is:

```text
escaped immutable host trampoline
    -> process-lived FEX descriptor
         atomic state: LIVE / REVOKED
         GuestUnpacker
         GuestTarget
```

Moved reload and same-address ABA pass, and this descriptor representation coexists with the real generated-Vulkan PFN candidate. See [`REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md`](./REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md).

A split resident bridge can remove the fixed `GuestUnpacker` from wrapper lifetime entirely when the actual guest callback target belongs elsewhere, as in Vulkan's X11 setup.

### 6. `munmap` retirement must be transactional if retirement is used

An invalid/failed `munmap` can leave guest code mapped. Eager pre-unmap retirement incorrectly kills a still-live owner.

The failed-munmap A/B proves a reclamation implementation needs prevalidation, rollback, or a two-phase transaction. See [`TWENTY_THIRD_PASS_FAILED_MUNMAP.md`](./TWENTY_THIRD_PASS_FAILED_MUNMAP.md).

## The proven execution-lifetime blocker

Future lookup cleanup cannot revoke a host-code pointer already selected by another emulation thread.

The forced negative control establishes:

```text
worker selects wrapper-owned T1 -> old host code
worker leaves lookup/invalidation guard
worker pauses
teardown retires H definition + shared cache + every thread cache
teardown physically unmaps T1 owner
worker resumes already-selected host code
SIGSEGV / exit 139
```

FEX's existing thread pause API is not an execution drain; it preserves interrupted execution and later restores it. See [`TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md`](./TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md).

## Split resident bridge closes that exact race

The stock-FEX split experiment changes executable ownership rather than trying to revoke already-selected host code.

The wrapper registers:

```text
H -> Tbridge
```

where `Tbridge` lives in a `NODELETE` bridge DSO and wrapper-specific state remains in an unloadable DSO.

The exact post-selection barrier then forces:

```text
worker selects Tbridge -> HostCodeBridge
worker pauses after selection guard is released
main final-closes wrapper
wrapper mapping is confirmed gone
Tbridge remains executable
worker resumes the already-selected HostCodeBridge
worker returns the correct value
```

Observed:

```text
DIAG_INFLIGHT_SELECTED guest=0x7ffff7d7c150 host=0x80006afc8cf4
split inflight wrapper unmapped before resume; bridge resident
DIAG_INFLIGHT_RESUME guest=0x7ffff7d7c150 host=0x80006afc8cf4
split inflight worker returned   rv=23 want=23
split inflight reload wrapper    ... DIFFERENT
split inflight reload bridge     ... SAME
SPLIT_INFLIGHT_RESULT selected-resident-bridge-survived-wrapper-unmap
exit=0
```

This directly distinguishes the split design from retirement-only reclamation:

> moving escaped/selected executable bridge glue out of the unloadable wrapper removes the proven reclamation race without requiring cache invalidation to revoke an already-selected host-code pointer.

## Whole-wrapper NODELETE evidence and remaining policy risk

### Runtime coverage

The whole-wrapper candidate now has product-sized runtime evidence in three important lanes:

1. real Vulkan dynamic PFN, including 256 close/reopen cycles;
2. real GL dynamic PFN, including 256 close/reopen cycles;
3. real Vulkan/X11 host→guest callback execution after close.

The Vulkan constructor churn also proves that the guest wrapper is not repeatedly reinitialized while host state persists:

```text
VULKAN_ONINIT_COUNT=1
STRESS_CYCLES=256
```

### Build coverage

The generic linker policy builds every current 64-bit shared guest thunk, representative real 32-bit Wayland, the unusual VDSO target, and the alternate lld guest-thunk mode.

### Direct wrapper footprint

The eight current 64-bit wrapper DSOs sum to:

```text
FILE_BYTES_TOTAL=10598320
PT_LOAD_MEMSZ_TOTAL=1771423
PT_LOAD_MIB_TOTAL=1.689
```

See [`NODELETE_BUILD_MATRIX.md`](./NODELETE_BUILD_MATRIX.md).

This is only wrapper ELF loadable memory. It does not include dirty RSS/PSS or dependency closure. A stock-vs-NODELETE process-level retained-memory A/B is now the highest-value remaining cost test.

### Semantic caveats

NODELETE deliberately changes physical unload semantics. Static NODELETE also pins disposable `dlmopen()` namespace copies. The real FEX/Vulkan namespace test did not show an earlier practical failure than stock because both variants hit glibc static-TLS limits first; base-namespace-only runtime promotion is a proven fallback if namespace recycling becomes a real requirement. See [`NODELETE_NAMESPACE_AND_RUNTIME_PROMOTION.md`](./NODELETE_NAMESPACE_AND_RUNTIME_PROMOTION.md).

No current guest-thunk source audit has found an explicit product wrapper contract requiring constructor/destructor/TLS reset on logical close/reopen. That remains a compatibility claim, not a theorem about future thunks or every application.

## Current design families

### A. Split process-resident guest bridge — preferred long-term architecture

Move signature-specific generic `CallHostFunction` adapters and fixed callback unpackers whose addresses escape wrapper lifetime into a resident guest bridge DSO. Keep library-specific wrapper code/state unloadable.

Evidence now includes:

- standalone loader model on x86-64 and AArch64, including 1,000 wrapper cycles;
- stock-FEX H→T and host→guest callback integration across five forced wrapper generations;
- wrapper physically unmapped while retained H and callback remain valid;
- exact selected-before-wrapper-unmap race returns correctly.

See [`SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md`](./SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md), [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md), and [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

Remaining work is generator/CMake integration and then real generated-Vulkan validation.

### B. Keep complete generated guest thunk wrappers resident — preferred near-term containment

Mark generated guest thunk DSOs `NODELETE`, or otherwise pin them for process lifetime.

This is the smallest demonstrated product-sized containment and also avoids the race because wrapper executable state is never reclaimed.

Real runtime evidence now covers Vulkan dynamic PFNs, GL dynamic PFNs, and retained Vulkan/X11 callbacks. Constructor churn shows one Vulkan guest generation survives 256 logical close/reopen cycles. Build coverage is green across current shared thunk modes, including representative 32-bit and special VDSO/lld cases.

The remaining objection is broader residency: wrapper-specific static/data state and dependency/RSS footprint remain process-long.

### C. Full owner-generation + execution lease/hazard

For true reclamation when executable adapters remain generation-owned, bridge execution must acquire generation ownership and unload must prevent new acquisitions then drain old ones before physical unmap.

This is semantically complete but is the largest runtime synchronization change. The first simple active-counter/call-return prototype did not yield a usable FEX result.

### D. Exact retirement + revoked H without execution draining

Proven necessary mechanics for generation handoff and controlled stale-state behavior, but incomplete as a physical-unload repair when selected executable code is still wrapper-owned.

### E. Target cell without resident executable ownership

Useful for generation-neutral dispatch and rebind, but insufficient for reclamation: another thread can load old T from the cell just before retirement and branch after unmap. See [`TARGET_CELL_RETIREMENT_RUNTIME.md`](./TARGET_CELL_RETIREMENT_RUNTIME.md).

## Current ranking

Two rankings are useful because containment and long-term architecture optimize different things.

### Near-term containment

1. **Whole-wrapper `NODELETE` / pinning** — smallest proven lever; real runtime evidence now spans Vulkan and GL dynamic PFNs plus the Vulkan callback direction.
2. **Split resident bridge** — stronger physical-unload semantics, but generator/build integration is not yet complete.
3. **Owner-generation + execution lease/hazard** — complete in principle, largest runtime change.

### Long-term architecture

1. **Split process-resident bridge** — closes the proven in-flight race while preserving wrapper physical unload/reset semantics.
2. **Owner-generation + execution lease/hazard** — strongest if every bridge byte must be reclaimable, but more synchronization-heavy.
3. **Whole-wrapper `NODELETE`** — robust containment with broader permanent state residency.

## Relationship to the Apple M5 `vulkaninfo` failure

The original M5 run proves:

- enumeration succeeds after the independent debug-report callback-routing correction;
- final teardown exits 139;
- saved guest instruction fetch lies in the old `libvulkan-guest.so` range after it is unmapped;
- disabling guest `dlclose()` changes the run to exit 0;
- bogus preload does not;
- pinning only `libvulkan-guest.so` changes the run to exit 0 for llvmpipe and Venus.

The hosted generated-Vulkan stock/candidate A/B independently proves the dynamic-PFN H→T lifetime mechanism and stock moved-reload failure. It strongly supports the same class as the original M5 teardown cause.

The remaining workload-specific uncertainty is narrow: the original M5 terminal transfer did not record the immediate H/R11 or first post-unload synthetic-entry hit. Do not rewrite that historical receipt as if that exact edge was captured.

## Submission boundary

All source changes described here are diagnostic/research code in owned repositories and forks. FEX's policy prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human.

No upstream FEX interaction was made.