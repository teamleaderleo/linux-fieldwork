# FEX Vulkan callback routing and guest-thunk lifetime

## Current status

This investigation has two independent findings.

### Finding A — dynamic debug-report callback routing

FEX already has a custom `vkCreateDebugReportCallbackEXT` host implementation that suppresses an unsafe guest callback before entering native Vulkan. Dynamic `vkGetInstanceProcAddr()` lookup does not select that custom implementation on the reviewed revisions.

On the original Apple M5 / FEX-2608 environment, adding the missing diagnostic custom lookup removes the observed SIGILL and lets x86-64 `vulkaninfo` enumerate Vulkan devices.

The same routing defect was independently reproduced on hosted ARM64 using reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a`; the pristine dynamic GIPA route signals before the debug-report fire returns, while the diagnostic custom route returns normally. See [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md).

### Finding B — guest-thunk lifetime across unload/reload

The second finding is no longer only a stale-CustomIR hypothesis.

A stock/candidate A/B reproduces the lifetime defect with FEX's **real generated Vulkan guest/host thunks** and a real dynamic Vulkan PFN obtained through:

```text
vkGetInstanceProcAddr(NULL, "vkEnumerateInstanceVersion")
```

The generated Vulkan thunk binaries are byte-identical across the A/B; only the FEX runtime changes.

Observed moved-generation matrix:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

The guest Vulkan wrapper is forced to reload at a different guest base. The native Vulkan PFN remains stable while the guest `CallHostFunction` invoker moves. Stock FEX accepts generation-2 registration but the newly reacquired generation-2 PFN still crashes. The research retirement/revocation candidate reactivates the same native PFN against generation-2 guest code and the Vulkan call succeeds.

Canonical receipt: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).

The same real generated-Vulkan candidate behavior passes on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`, the source revision used by the original M5 investigation. See [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md).

## Rebind success is not a complete physical-unload fix

Exact retirement/revocation fixes stale **future dispatch** and generation rebinding, but physical unmap has a second concurrency problem.

A forced runtime race proves a worker can:

```text
select old wrapper-owned T1 -> old host code
leave the lookup/invalidation guard
pause
```

while teardown then:

```text
retires the CustomIR definition
removes shared H state
invalidates H in every live emulation thread cache
unmaps the owner containing T1
```

When the worker resumes its already-selected host-code pointer, it faults into the retired generation. The pin control returns correctly.

Therefore all-thread cache retirement is **necessary but not sufficient** for safe physical guest-thunk reclamation. See [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md).

FEX's existing thread pause API is not an execution drain; it preserves interrupted execution and later restores it. See [`TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md`](./TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md).

## Split resident bridge closes that exact race

The strongest new result moves only the executable bridge glue whose addresses escape wrapper lifetime into a small process-resident guest DSO, while wrapper-specific code/state remains unloadable.

Under **stock FEX core**:

```text
unloadable wrapper DSO
    registration + wrapper-specific state
    DT_NEEDED -> resident bridge DSO

resident bridge DSO (NODELETE)
    CallHost-style H adapter
    fixed callback unpacker

main guest / other guest library
    actual callback target
```

Across five forced wrapper generations:

- the wrapper physically disappears after `dlclose()`;
- the resident bridge remains executable;
- retained H calls work before any wrapper reload;
- retained host→guest callbacks work before any wrapper reload;
- the wrapper reloads at a new address with fresh wrapper state;
- the resident adapter address stays identical.

See [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

More importantly, the exact selected-before-unmap barrier was rerun against the split design:

```text
DIAG_INFLIGHT_SELECTED guest=<resident bridge> host=<selected host code>
wrapper unmapped before resume; bridge resident
DIAG_INFLIGHT_RESUME guest=<same resident bridge> host=<same selected host code>
worker returned rv=23 want=23
wrapper reload DIFFERENT
bridge reload SAME
exit=0
```

The wrapper-owned-T1 version of this race exits `139`; the resident-bridge version returns correctly. See [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

This makes executable ownership, rather than cache invalidation alone, the key distinction for safe wrapper reclamation.

## Current repair decision

The detailed ranking is in [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md).

Two rankings are useful.

### Near-term containment

1. **Keep complete generated guest thunk wrappers resident (`NODELETE` / pinning).** Smallest proven lever on real generated Vulkan. Dynamic PFNs and retained Vulkan/X11 callbacks continue to work after ordinary `dlclose()`. Build coverage is green across the current shared thunk modes. See [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md), [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md), and [`NODELETE_BUILD_MATRIX.md`](./NODELETE_BUILD_MATRIX.md).
2. **Split process-resident bridge.** Stronger unload/reset semantics, but generator/CMake integration is still being built.
3. **Owner-generation + execution lease/hazard.** Complete in principle, largest runtime synchronization change.

### Preferred long-term architecture

1. **Split process-resident bridge runtime.** Now proven inside stock FEX and against the selected-before-wrapper-unmap race while preserving wrapper physical unload/reset.
2. **Full owner-generation + execution lease/hazard.** Needed only if even resident bridge glue must eventually be reclaimable or policy requires generation-specific execution ownership.
3. **Whole-wrapper `NODELETE`.** Robust containment with broader permanent wrapper state residency.

Exact retirement + revoked H remains a proven generation-rebind mechanism and useful cleanup primitive, but is incomplete as a physical-unload repair when the selected executable adapter is wrapper-owned. A target cell alone is also insufficient because a thread can load old T immediately before retirement and branch after unmap. See [`TARGET_CELL_RETIREMENT_RUNTIME.md`](./TARGET_CELL_RETIREMENT_RUNTIME.md).

## Required lifetime properties established

Any generic unload-capable solution must account for the relevant subset of these:

- **Executable ownership:** any guest executable address that may escape wrapper lifetime into FEX/host state must either remain resident or participate in an execution-lifetime protocol.
- **Owner identity:** generation-owned guest addresses need mapping/load ownership rather than process-lifetime pointer semantics.
- **Synthetic native key state:** if H is retired rather than made generation-neutral, it should remain distinguishable as `ACTIVE` or `REVOKED`; it must not fall through to ordinary x86 decoding of a native ARM address.
- **All-thread future-dispatch invalidation:** baked H→T runtime mappings must be removed from shared state and every live emulation thread cache when T changes.
- **Already-selected execution:** future lookup invalidation cannot revoke a host-code pointer already selected outside the invalidation critical section.
- **Multi-owner claims:** multiple live guest owners can claim one native H. Compatible claims must be retained rather than discarded. FEX's generated thunk/signature hash is the preferred compatibility identity; see [`THUNK_SIGNATURE_IDENTITY.md`](./THUNK_SIGNATURE_IDENTITY.md).
- **Host→guest callbacks:** fixed unpackers/targets that escape wrapper lifetime need resident ownership or revocable descriptor semantics.
- **Transactional unmap:** if retirement is tied to `munmap`, it cannot be irreversibly committed before a `munmap` that may fail. See [`TWENTY_THIRD_PASS_FAILED_MUNMAP.md`](./TWENTY_THIRD_PASS_FAILED_MUNMAP.md).

## Preferred callback representation when callback state remains revocable

The older diagnostic callback tombstone mutated embedded trampoline fields. A safer prototype keeps the escaped host trampoline immutable and points it at a process-lived FEX descriptor:

```text
host trampoline
    -> callback descriptor
         state = LIVE / REVOKED
         GuestUnpacker
         GuestTarget
```

Moved reload and same-address ABA controls pass, and this descriptor design coexists with the real generated-Vulkan PFN lifetime candidate. See [`REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md`](./REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md).

A split bridge can eliminate the wrapper-lifetime dependency for fixed unpackers entirely when the actual guest callback target belongs to another owner, as Vulkan's X11 targets do.

## Original Apple M5 evidence

The original target environment was:

```text
Host: Apple M5 MacBook Air, arm64, Darwin 25.6.0
Lima: 2.2.0
krunkit: 1.3.2
Guest: Fedora 44 aarch64
Kernel: 6.19.10-300.fc44.aarch64
Mesa: 25.3.6
FEX: FEX-2608 / e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

After the independent callback-routing diagnostic correction, x86-64 `vulkaninfo --summary` completes enumeration and then exits 139 during teardown. The stable guest fault is an x86 instruction-fetch page fault whose saved guest RIP lies in the former `libvulkan-guest.so` image after that image is unmapped.

Controls:

```text
normal teardown                         -> 139
bogus preload                           -> 139
guest dlclose overridden to no-op       -> 0
only libvulkan-guest.so pinned          -> 0
pinned Venus run                         -> 0
```

The pinned Venus control enumerates `Virtio-GPU Venus (Apple M5)` and llvmpipe.

The remaining M5-specific uncertainty is narrow: that historical trace did not capture the immediate terminal native H/R11 or first post-unload synthetic-entry hit. Do not rewrite the original receipt as if that exact edge was captured. The hosted generated-Vulkan A/B independently proves the dynamic-PFN lifetime mechanism and stock moved-reload failure.

Detailed original receipts remain in [`EVIDENCE.md`](./EVIDENCE.md) and [`TEARDOWN_CHRONOLOGY.md`](./TEARDOWN_CHRONOLOGY.md).

## Source-level bridge classes

Two lifetime classes are central.

### Dynamic native PFN → guest invoker

`ThunkLibs/libvulkan/Guest.cpp` obtains native Vulkan PFNs and registers them through `LinkAddressToFunction`. Current generated wrappers target a `CallHostFunction<...>` body compiled into the guest Vulkan thunk DSO.

The defect appears when stable native H outlives the wrapper generation that owns T.

The split design changes this to target a process-resident signature adapter instead of wrapper-owned code.

### Host → guest callback trampoline

`MakeHostTrampolineForGuestFunction` exposes a host-callable trampoline whose callback path needs a guest unpacker and target.

Current Vulkan setup uses fixed `CallbackUnpack<signature>::Unpack` code in the wrapper plus X11 targets outside it. The split design moves the fixed unpacker into resident bridge code while leaving the X11 target with its real owner.

## Canonical current receipts

- Callback-routing reproduction on reviewed source: [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md)
- Original M5 evidence matrix: [`EVIDENCE.md`](./EVIDENCE.md)
- Teardown chronology: [`TEARDOWN_CHRONOLOGY.md`](./TEARDOWN_CHRONOLOGY.md)
- Real generated-Vulkan stock/candidate PFN A/B: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md)
- Exact FEX-2608 real-Vulkan candidate: [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md)
- Real Vulkan callback descriptor + PFN integration: [`REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md`](./REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md)
- In-flight wrapper-owned selected-execution negative control: [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md)
- FEX split resident bridge runtime: [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md)
- Split resident selected-before-unmap race: [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md)
- Current repair decision: [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md)
- NODELETE real Vulkan PFN: [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md)
- NODELETE real Vulkan X11 callback: [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md)
- Standalone split bridge model: [`SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md`](./SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md)

## Contribution and contact boundary

All FEX source changes in this investigation are diagnostic/research code on local trees or owned forks. FEX currently prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human in compliance with that policy.

No upstream FEX issue, PR, comment, review, reaction, push, discussion, or other mutation has been made by this investigation.

When an external FEX GitHub reference is necessary, use the redirect form, for example:

```text
https://redirect.github.com/FEX-Emu/FEX/commit/e869aa644a16e4332cdc15c1ea0b4d13d482385d
```
