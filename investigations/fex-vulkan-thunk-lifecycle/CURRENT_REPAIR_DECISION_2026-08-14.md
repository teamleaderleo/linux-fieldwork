# Current repair decision — FEX guest-thunk lifetime

Date: 2026-08-14

## Decision summary

The unload investigation has advanced beyond a stale-CustomIR hypothesis.

The current evidence supports three separate statements:

1. **A real generated-Vulkan dynamic-PFN lifetime defect is proven.** A stock/candidate A/B with byte-identical generated Vulkan thunks changes forced moved reload from stock exit `139` to candidate exit `0` by changing only FEX runtime lifetime handling. See [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).
2. **Exact retirement/revocation is necessary but not sufficient for physical unload.** A worker that already selected old-generation host code can resume that selection after handler retirement, shared/per-thread cache invalidation, and physical unmap, then fault. See [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md).
3. **Keeping the executable guest thunk resident is the only currently demonstrated repair family that trivially closes the in-flight reclamation race.** The generic `NODELETE` candidate has real generated-Vulkan coverage for both dynamic PFNs and retained Vulkan/X11 callbacks after ordinary `dlclose()`. See [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md) and [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md).

Therefore the current lock-clean/revoked-H implementation is a **research proof of required lifetime mechanics and successful generation rebinding**, not yet a complete physical-unload product repair.

## What is now proven on the H→T path

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

## Required mechanics for any unload-capable repair

### 1. Explicit owner lifetime

FEX-retained bridges that embed unloadable guest executable addresses need an owner identity tied to a guest mapping/load generation, not an unqualified process-lifetime pointer.

Raw target range matching is sufficient for diagnostics. A production owner token can use or extend FEX's existing mapped-resource/load identity.

### 2. Synthetic H state must survive retirement

A native host PFN previously advertised to the guest must not silently become an ordinary guest RIP after owner retirement.

Minimum state:

```text
UNKNOWN -> ACTIVE(H,T,owner,signature) -> REVOKED(H,signature) -> ACTIVE(H,T2,...)
```

A stale H call should hit a controlled synthetic rejection/fault path. The revoked-H runtime proof demonstrates this behavior.

### 3. Future lookup state must be retired across every thread

Runtime A/B proves current-thread-only invalidation is insufficient. Retirement of a baked H→T block must remove:

- the CustomIR definition/current target claim;
- shared compiled/direct-link state for H;
- H from every emulation thread's hot lookup cache.

The coherent lock order must follow the existing invalidation direction rather than calling the old CustomIR remover under an inverted lock order.

### 4. Multi-owner H claims must not be discarded

Two live guest owners can claim the same native H. Keeping only the first claim loses the second owner when the first unloads.

A same-signature runtime fixture proves retaining compatible claims and promoting a surviving claim works. Generic promotion needs a compatibility identity. FEX's existing generated thunk/signature hash is the preferred source rather than inventing a separate ABI token. See [`THUNK_SIGNATURE_IDENTITY.md`](./THUNK_SIGNATURE_IDENTITY.md).

### 5. Host→guest callbacks require independent revocation

FEX host trampolines can retain guest unpacker and target addresses. This is a separate lifetime class from dynamic PFNs.

The preferred representation is now:

```text
escaped immutable host trampoline
    -> process-lived FEX descriptor
         atomic state: LIVE / REVOKED
         GuestUnpacker
         GuestTarget
```

Retirement atomically changes descriptor state and removes the cache key. The escaped executable trampoline bytes remain immutable. Same-address ABA and moved reload both passed in the descriptor runtime matrix. See [`TWENTY_SEVENTH_PASS_CALLBACK_DESCRIPTOR.md`](./TWENTY_SEVENTH_PASS_CALLBACK_DESCRIPTOR.md).

### 6. `munmap` retirement must be transactional

An invalid/failed `munmap` can leave guest code mapped. Eagerly retiring bridges before an unvalidated `munmap` incorrectly kills a still-live owner.

The failed-munmap A/B proves the implementation needs prevalidation, rollback, or a two-phase retirement transaction. See [`TWENTY_THIRD_PASS_FAILED_MUNMAP.md`](./TWENTY_THIRD_PASS_FAILED_MUNMAP.md).

## The execution-lifetime blocker

All of the mechanics above govern **future dispatch**. They do not revoke a host-code pointer already selected by another emulation thread.

The forced in-flight experiment establishes this exact sequence:

```text
worker selects old guest T1 -> old host code
worker leaves lookup/invalidation guard
worker pauses
teardown retires H definition + shared cache + every thread cache
teardown physically unmaps T1 owner
worker resumes already-selected host code
SIGSEGV
```

The pin control returns correctly. The forced-unmap case exits `139` after resume.

Therefore:

> physical guest-wrapper unmap is not safe merely because no future H lookup can select the old generation.

FEX's existing thread pause API is not an execution drain: it preserves interrupted execution and later restores it. See [`TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md`](./TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md).

## Full-reclamation design families still viable

### A. Execution lease / hazard / grace period

Entering generation-dependent bridge execution publishes ownership of that generation. Retirement blocks new acquisitions and waits until all already-acquired executions have left before physical unmap.

This is semantically complete but nontrivial because current dynamic-PFN bridge execution uses tail-transfer behavior. A first shared-counter call/return prototype did not produce a usable runtime result, so this family still needs a correct implementation experiment.

### B. Stable process-lived final-transfer bridge

Keep the selected host-side bridge code process-lived and make it consult stable revocable state at the last possible transition into guest-generation code. To be race-safe, this still needs either an atomic protocol equivalent to a hazard/lease or a target whose executable code itself is process-lived.

A target cell alone is **not** sufficient: another thread can load old T before retirement and branch after unmap. See [`TARGET_CELL_RETIREMENT_RUNTIME.md`](./TARGET_CELL_RETIREMENT_RUNTIME.md).

### C. Process-resident guest bridge runtime

Move signature-specific generic `CallHostFunction` adapters and their required special thunk glue out of unloadable library wrapper DSOs into a process-resident bridge runtime.

Then FEX process-owned H dispatch no longer targets executable code owned by `libvulkan-guest.so`. The library-specific wrapper can unload/reset while the executable adapter survives.

A standalone split-runtime loader model already passed on hosted x86-64 and AArch64, including 1,000 wrapper cycles. FEX integration remains unimplemented. See [`SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md`](./SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md).

### D. Keep generated guest thunk wrappers resident

Mark shared generated guest thunk DSOs `NODELETE`, or otherwise pin them for process lifetime.

This is the smallest currently demonstrated product-sized containment and removes the reclamation race entirely because the guest executable generation is never reclaimed.

Real Vulkan evidence already covers:

- retained dynamic Vulkan PFN after ordinary `dlclose()`;
- retained Vulkan/X11 host→guest callbacks after ordinary `dlclose()`;
- wrapper remains mapped and executable;
- real host Vulkan calls continue to work.

Costs are policy/compatibility costs rather than execution safety uncertainty: wrapper constructors/static/TLS state do not receive a fresh physical generation and executable/data footprint remains resident.

## Current ranking

For a near-term repair experiment against the original Vulkan workload:

1. **`NODELETE` / resident generated guest thunk** — strongest current containment; real Vulkan coverage exists in both bridge directions and it avoids the proven in-flight unmap race.
2. **Split process-resident bridge runtime** — most attractive general design if ordinary wrapper unload/reset semantics are important; needs FEX integration proof.
3. **Full owner-generation + execution lease/hazard** — strongest full-reclamation semantics; largest runtime synchronization change and still lacks a working FEX prototype.
4. **Exact retirement + revoked H without execution draining** — required diagnostic mechanics and a successful generation-rebind proof, but incomplete as a physical-unload repair.
5. **Target cell without execution ownership** — useful generation-neutral dispatch mechanism, insufficient for unmap safety.

## Relationship to the Apple M5 `vulkaninfo` failure

The original M5 run proves:

- enumeration succeeds after the independent debug-report callback-routing correction;
- final teardown exits 139;
- saved guest instruction fetch lies in the old `libvulkan-guest.so` range after it is unmapped;
- disabling guest `dlclose()` changes the run to exit 0;
- bogus preload does not;
- pinning only `libvulkan-guest.so` changes the run to exit 0 for llvmpipe and Venus.

The hosted generated-Vulkan A/B independently proves the dynamic-PFN H→T lifetime mechanism and stock moved-reload failure. It strongly supports the same class as the original M5 teardown cause.

The remaining workload-specific uncertainty is narrow: the original M5 terminal transfer did not record the immediate H/R11 or first post-unload synthetic-entry hit. Do not rewrite that historical receipt as if that exact edge was captured.

## Submission boundary

All source changes described here are diagnostic/research code in owned repositories and forks. FEX's policy prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human.

No upstream FEX interaction was made.