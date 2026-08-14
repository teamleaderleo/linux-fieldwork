# FEX Vulkan callback routing and guest-thunk lifetime

## Current status

This investigation has two independent findings.

### Finding A — dynamic debug-report callback routing

FEX already has a custom `vkCreateDebugReportCallbackEXT` host implementation that suppresses an unsafe guest callback before entering native Vulkan. Dynamic `vkGetInstanceProcAddr()` lookup does not select that custom implementation on the reviewed revisions.

On the original Apple M5 / FEX-2608 environment, adding the missing diagnostic custom lookup removes the observed SIGILL and lets x86-64 `vulkaninfo` enumerate Vulkan devices.

The same routing defect was independently reproduced on hosted ARM64 using reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a`; the pristine dynamic GIPA route signals before the debug-report fire returns, while the diagnostic custom route returns normally. See [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md).

### Finding B — guest-thunk lifetime across unload/reload

The second finding is no longer only a stale-CustomIR hypothesis.

A stock/candidate A/B now reproduces the lifetime defect with FEX's **real generated Vulkan guest/host thunks** and a real dynamic Vulkan PFN obtained through:

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

The guest Vulkan wrapper is forced to reload at a different guest base. The native Vulkan PFN address remains stable while the guest `CallHostFunction` invoker moves. Stock FEX accepts generation-2 registration but the newly reacquired generation-2 PFN still crashes. The research candidate retires/revokes the old synthetic native entry, reactivates the same native PFN against generation-2 guest code, and the Vulkan call succeeds.

Canonical receipt: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md).

The same real generated-Vulkan candidate behavior also passes on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`, the source revision used by the original M5 investigation. See [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md).

## Important correction: rebind success is not a complete physical-unload fix

Exact retirement/revocation fixes stale **future dispatch** and generation rebinding, but physical unmap has a second concurrency problem.

A forced runtime race proves a worker can:

```text
select old guest T1 -> old host code
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

When the worker resumes its already-selected host-code pointer, it still faults into the retired generation. The pin control returns correctly.

Therefore all-thread cache retirement is **necessary but not sufficient** for safe physical guest-thunk reclamation. See [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md).

FEX's existing thread pause API is not an execution drain; it preserves interrupted execution and later restores it. See [`TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md`](./TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md).

## Current repair decision

The detailed current ranking is in [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md).

In short:

1. **Keep generated guest thunk wrappers resident (`NODELETE` / pinning).** This is the strongest demonstrated containment today because it removes the proven reclamation race. Real generated-Vulkan tests cover both retained dynamic PFNs and retained Vulkan/X11 callbacks after ordinary `dlclose()`. See [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md) and [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md).
2. **Split process-resident bridge runtime.** Move generic signature-specific bridge adapter code out of unloadable wrapper DSOs while allowing library-specific wrapper state to unload/reset. A standalone loader model passed on hosted x86-64 and AArch64, including repeated wrapper cycles; FEX integration remains to be implemented. See [`SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md`](./SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md).
3. **Full owner-generation + execution lease/hazard.** Strongest full-reclamation semantics, but the execution-ownership mechanism still lacks a successful FEX implementation prototype.
4. **Exact retirement + revoked H without execution draining.** Proven generation-rebind mechanism and required cleanup primitive, but incomplete as a physical-unload repair because it cannot revoke already-selected execution.
5. **Target cell alone.** Useful for generation-neutral H dispatch and rebinding, but another thread can load old T before retirement and branch after unmap. See [`TARGET_CELL_RETIREMENT_RUNTIME.md`](./TARGET_CELL_RETIREMENT_RUNTIME.md).

## Required lifetime properties already established

Any unload-capable generic solution must account for all of these:

- **Owner identity:** FEX-retained guest executable addresses need mapping/load ownership rather than process-lifetime pointer semantics.
- **Synthetic native key state:** a native host PFN previously advertised to guest code should remain distinguishable as `ACTIVE` or `REVOKED`; after final retirement it must not fall through to ordinary x86 decoding of a native ARM address.
- **All-thread future-dispatch invalidation:** baked H→T runtime mappings must be removed from shared state and every live emulation thread's hot cache when the active generation changes.
- **Already-selected execution:** future lookup invalidation cannot revoke a host-code pointer already selected outside the invalidation critical section.
- **Multi-owner claims:** multiple live guest owners can claim one native H. Compatible claims must be retained rather than discarded. FEX's generated thunk/signature hash is the preferred compatibility identity; see [`THUNK_SIGNATURE_IDENTITY.md`](./THUNK_SIGNATURE_IDENTITY.md).
- **Host→guest callbacks:** callback trampolines retain guest unpacker/target addresses and require their own owner-aware revocation.
- **Transactional unmap:** retirement cannot be irreversibly committed before a `munmap` that may fail. The failed-munmap A/B is retained in [`TWENTY_THIRD_PASS_FAILED_MUNMAP.md`](./TWENTY_THIRD_PASS_FAILED_MUNMAP.md).

## Preferred callback representation

The older diagnostic callback tombstone mutated embedded trampoline fields. A safer prototype now keeps the escaped host trampoline immutable and points it at a process-lived FEX descriptor:

```text
host trampoline
    -> callback descriptor
         state = LIVE / REVOKED
         GuestUnpacker
         GuestTarget
```

Retirement atomically marks the descriptor revoked and removes its lookup key. Old escaped trampoline pointers deterministically take the revoked path; a new generation allocates a new live descriptor. Moved reload and same-address ABA controls both pass. See [`TWENTY_SEVENTH_PASS_CALLBACK_DESCRIPTOR.md`](./TWENTY_SEVENTH_PASS_CALLBACK_DESCRIPTOR.md).

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

Two FEX-owned lifetime classes are central:

### Dynamic native PFN → guest invoker

`ThunkLibs/libvulkan/Guest.cpp` obtains native Vulkan PFNs and registers them through `LinkAddressToFunction`. The target is a generated `CallHostFunction<...>` body compiled into the guest Vulkan thunk DSO.

Core installs a synthetic entry keyed by the native host address H and routes it to the guest invoker T. The defect appears when H remains stable while T belongs to an unloadable guest generation.

### Host → guest callback trampoline

`MakeHostTrampolineForGuestFunction` creates executable host trampolines whose state can retain guest `GuestUnpacker` and `GuestTarget` addresses. Those guest addresses can also belong to unloadable wrapper code.

These two directions need coordinated owner semantics, even though the real Vulkan teardown evidence most directly fits the dynamic-PFN H→T path.

## Canonical current receipts

- Callback-routing reproduction on reviewed source: [`HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md`](./HOSTED_ARM64_FINDING_A_CURRENT_MAIN.md)
- Original M5 evidence matrix: [`EVIDENCE.md`](./EVIDENCE.md)
- Teardown chronology: [`TEARDOWN_CHRONOLOGY.md`](./TEARDOWN_CHRONOLOGY.md)
- Real generated-Vulkan stock/candidate PFN A/B: [`REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`](./REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md)
- Exact FEX-2608 real-Vulkan candidate: [`FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md`](./FEX2608_REAL_VULKAN_PFN_RUNTIME_2026-08-14.md)
- In-flight selected-execution negative control: [`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`](./TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md)
- Current repair decision: [`CURRENT_REPAIR_DECISION_2026-08-14.md`](./CURRENT_REPAIR_DECISION_2026-08-14.md)
- Atomic callback descriptor: [`TWENTY_SEVENTH_PASS_CALLBACK_DESCRIPTOR.md`](./TWENTY_SEVENTH_PASS_CALLBACK_DESCRIPTOR.md)
- NODELETE real Vulkan PFN: [`NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md`](./NODELETE_REAL_VULKAN_CANDIDATE_RUNTIME.md)
- NODELETE real Vulkan X11 callback: [`NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md`](./NODELETE_REAL_VULKAN_X11_CALLBACK_RUNTIME.md)
- Split resident bridge model: [`SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md`](./SPLIT_BRIDGE_RUNTIME_EXPERIMENT.md)

## Contribution and contact boundary

All FEX source changes in this investigation are diagnostic/research code on local trees or owned forks. FEX currently prohibits AI-generated contribution code. Any upstream implementation must be independently derived and written by a human in compliance with that policy.

No upstream FEX issue, PR, comment, review, reaction, push, discussion, or other mutation has been made by this investigation.

When an external FEX GitHub reference is necessary, use the redirect form, for example:

```text
https://redirect.github.com/FEX-Emu/FEX/commit/e869aa644a16e4332cdc15c1ea0b4d13d482385d
```
