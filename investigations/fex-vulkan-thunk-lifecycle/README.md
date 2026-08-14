# FEX Vulkan callback routing and guest-thunk lifetime

## Current status

This investigation has two independent findings.

### Finding A — dynamic debug-report callback routing

FEX already has a custom `vkCreateDebugReportCallbackEXT` host implementation that suppresses an unsafe guest callback before entering native Vulkan. Dynamic `vkGetInstanceProcAddr()` lookup does not select that custom implementation on the reviewed revisions.

On the original Apple M5 / FEX-2608 environment, adding the missing diagnostic custom lookup removes the observed SIGILL and lets x86-64 `vulkaninfo` enumerate Vulkan devices.

The same routing defect was independently reproduced on hosted ARM64 using reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a`; the pristine dynamic GIPA route signals before the debug-report fire returns, while the diagnostic custom route returns normally. See [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md).

### Finding B — guest-thunk lifetime across unload/reload

A stock/candidate A/B reproduces the lifetime defect with FEX's **real generated Vulkan guest/host thunks** and a real dynamic Vulkan PFN obtained through:

```text
vkGetInstanceProcAddr(NULL, "vkEnumerateInstanceVersion")
```

The generated Vulkan thunk binaries are byte-identical across the A/B; only FEX runtime lifetime handling changes.

Observed moved-generation matrix:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

The guest Vulkan wrapper is forced to reload at a different guest base. The native Vulkan PFN remains stable while the guest `CallHostFunction` invoker moves. Stock FEX accepts generation-2 registration but the newly reacquired generation-2 PFN still crashes. Explicit retirement/revocation/rebind makes the generation-2 call succeed.

Canonical receipt: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).

The same rebind behavior passes on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`: [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md).

## Retirement/rebind does not solve physical reclamation by itself

Exact retirement/revocation fixes stale **future dispatch** and generation rebinding, but a forced runtime race proves another thread can already own selected wrapper-generation code:

```text
worker selects wrapper-owned T1 -> HostCode1
worker leaves lookup/invalidation guard
worker pauses
main retires definition/shared/all-thread H caches
main physically unmaps T1 owner
worker resumes already-selected HostCode1
exit 139
```

Therefore all-thread cache retirement is necessary but not sufficient for safe physical wrapper reclamation. See [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md).

FEX's existing thread pause API is not an execution drain; it preserves interrupted execution and later restores it. See [`TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md`](./TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md).

## Preferred long-term architecture — generated split resident bridge

The strongest design moves only executable bridge glue whose addresses escape wrapper lifetime into a small process-resident guest companion DSO, while wrapper-specific code/state remains physically unloadable.

```text
unloadable wrapper DSO
    constructors / mutable state / public wrappers
    registration referencing resident addresses
    DT_NEEDED -> resident bridge

resident bridge DSO (NODELETE)
    signature-specific CallHostFunction adapters
    fixed CallbackUnpack functions
```

This is now proven at every important boundary.

### Stock-FEX synthetic split

Across five forced wrapper generations:

- wrapper mappings disappear after `dlclose()`;
- bridge remains executable;
- retained H calls work before wrapper reload;
- retained host→guest callbacks work before wrapper reload;
- wrapper reloads at a different address with fresh state;
- bridge adapter address remains identical.

See [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

### Exact selected-before-unmap race

The same post-selection barrier that exits `139` with wrapper-owned T1 returns correctly when the selected adapter is resident:

```text
DIAG_INFLIGHT_SELECTED guest=<resident bridge> host=<selected host code>
wrapper unmapped before resume; bridge resident
DIAG_INFLIGHT_RESUME guest=<same resident bridge> host=<same selected host code>
worker returned rv=23 want=23
wrapper reload DIFFERENT
bridge reload SAME
exit=0
```

See [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md).

### Real generated Vulkan dynamic PFN

A Vulkan-specific generated companion `libfex-vulkan-bridge.so` is marked `NODELETE`; `libvulkan.so.1` itself remains ordinary unloadable code.

Under stock reviewed FEX core:

```text
hold=0
close=0
reload=0
```

After final wrapper close, the exact five tracked guest-wrapper mappings disappear, yet the old native PFN still returns a real Vulkan result through the resident signature adapter. Forced wrapper reload moves GIPA/wrapper generation while native H and the resident adapter remain stable, and the real Vulkan call succeeds again.

See [`REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md).

The same generated split passes on exact FEX-2608 under stock core: [`FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md).

### Real generated Vulkan/X11 callback direction

The generated companion also owns Vulkan's fixed X11 callback unpackers.

The corrected exact-path runtime proves:

```text
MAPS_BEFORE exact_wrapper=5 bridge=5
... real Vulkan Xlib PFN invokes guest X11 callbacks ...
MAPS_AFTER exact_wrapper=0 bridge=5
AFTER_DLCLOSE_BEGIN_CALLBACK_TEST
GUEST_XSYNC display=0x12346000
GUEST_XDISPLAYSTRING display=0x12346000
AFTER_CLOSE_XLIB result=0
REAL_SPLIT_VULKAN_X11_CALLBACK_OK
```

The actual guest Vulkan wrapper is physically gone before the retained Vulkan Xlib PFN drives fresh guest callbacks.

See [`REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md).

## Current repair decision

Detailed current ranking: [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md).

### Near-term containment

1. **Whole-wrapper NODELETE / pinning.** Smallest proven product lever. Real Vulkan, real Vulkan/X11 callbacks, GL dynamic PFNs, constructor churn, and build modes are covered. The cost is full wrapper code/data/static/TLS residency.
2. **Generated split resident bridge.** Better wrapper unload/reset semantics and now proven on real generated Vulkan in both bridge directions; research generator/CMake implementation still needs clean central generalization.
3. **Owner-generation + execution lease/hazard.** Full reclamation if even resident bridge glue must be reclaimable; largest synchronization change.

### Preferred long-term architecture

1. **Generated split process-resident bridge.** Preserves wrapper physical unload/reset, closes the selected-before-unmap race, passes real generated Vulkan PFNs and callbacks, and passes exact FEX-2608.
2. **Owner-generation + execution lease/hazard.** Only needed if process-long bridge glue is unacceptable or policy requires generation-owned execution.
3. **Whole-wrapper NODELETE.** Robust containment with broader permanent state residency.

## Useful retirement-policy mechanics already proven

Even with resident bridge code, owner-aware policy can still use these proven pieces:

- synthetic H `ACTIVE` / `REVOKED` state;
- all-thread future-dispatch invalidation when a baked target changes;
- retained compatible multi-owner claims and promotion;
- generated thunk/signature SHA as compatibility identity;
- transactional `munmap` prevalidation/rollback if retirement is tied to unmap;
- immutable host trampoline + atomic callback descriptor when the actual GuestTarget can itself unload.

A target cell alone is insufficient for wrapper-owned executable reclamation because another thread can load old T immediately before retirement and branch after unmap. See [`TARGET_CELL_RETIREMENT_RUNTIME.md`](./TARGET_CELL_RETIREMENT_RUNTIME.md).

## Generator generalization plan

The successful Vulkan transformer is research post-processing, not the desired final generator interface.

The next implementation step is a central optional companion bridge emitted by thunk generation/build logic:

```text
${lib}-guest                  unloadable wrapper
${lib}-bridge-guest           resident companion
```

Start per library/per bitness, then deduplicate by signature later if worthwhile.

Detailed plan: [`GENERATED_RESIDENT_BRIDGE_INTEGRATION_PLAN.md`](./GENERATED_RESIDENT_BRIDGE_INTEGRATION_PLAN.md).

`libGL` is already confirmed as a direct second pattern match: wrapper-local dynamic `HostPtrInvokers = GetCallerForHostFunction(...)` plus fixed `CallbackUnpack` addresses for malloc/X11 callbacks. See [`RESIDENT_BRIDGE_LIBRARY_AUDIT.md`](./RESIDENT_BRIDGE_LIBRARY_AUDIT.md).

## Original Apple M5 evidence

Original target:

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

The remaining M5-specific uncertainty is narrow: that historical trace did not capture the immediate terminal native H/R11 or first post-unload synthetic-entry hit. Do not rewrite the original receipt as if that exact edge was captured. Hosted generated-Vulkan work independently proves the dynamic-PFN lifetime defect and race-safe ownership repair.

Detailed original receipts remain in [`EVIDENCE.md`](./EVIDENCE.md) and [`TEARDOWN_CHRONOLOGY.md`](./TEARDOWN_CHRONOLOGY.md).

## Canonical current receipts

- Callback-routing reproduction: [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md)
- Original M5 evidence: [`EVIDENCE.md`](./EVIDENCE.md)
- Real unsplit generated-Vulkan PFN A/B: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md)
- Exact FEX-2608 rebind candidate: [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md)
- Wrapper-owned selected-execution negative control: [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md)
- Split FEX runtime: [`FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md)
- Split selected-before-unmap race: [`FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md`](./FEX_SPLIT_RESIDENT_BRIDGE_INFLIGHT_RUNTIME_2026-08-14.md)
- Real generated Vulkan split PFN: [`REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_RESIDENT_BRIDGE_RUNTIME_2026-08-14.md)
- Exact FEX-2608 real generated Vulkan split: [`FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_SPLIT_RESIDENT_RUNTIME_2026-08-14.md)
- Real generated Vulkan split X11 callbacks: [`REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md`](./REAL_VULKAN_SPLIT_X11_CALLBACK_RUNTIME_2026-08-14.md)
- Real Vulkan callback descriptor integration: [`REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md`](./REAL_VULKAN_CALLBACK_DESCRIPTOR_RUNTIME_2026-08-14.md)
- Whole-wrapper NODELETE Vulkan PFN: [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md)
- Whole-wrapper NODELETE Vulkan X11 callbacks: [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md)
- Current repair decision: [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md)

## Contribution and contact boundary

All FEX source changes in this investigation are diagnostic/research code on local trees or owned forks. FEX currently prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human in compliance with that policy.

No upstream FEX issue, PR, comment, review, reaction, push, discussion, or other mutation has been made by this investigation.

When an external FEX GitHub reference is necessary, use the redirect form, for example:

```text
https://redirect.github.com/FEX-Emu/FEX/commit/e869aa644a16e4332cdc15c1ea0b4d13d482385d
```
