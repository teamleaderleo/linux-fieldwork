# FEX integration notes

Owned source/research surfaces only. FEX upstream remains untouched.

## Current source lifecycle map

`ThunkFunctions::LinkAddressToGuestFunction` receives a native function address H and guest target T, then calls `AddThunkTrampolineIRHandler(H, T)`. The current API does not carry guest DSO identity, mapping generation, or signature ownership.

`ContextImpl::AddThunkTrampolineIRHandler` installs a synthetic CustomIR entry keyed by the native H address. In the existing design the generated handler captures T and emits an exit to that guest address.

The Vulkan guest wrapper builds its dynamic name→invoker table from `GetCallerForHostFunction(name)`. Those `CallHostFunction<signature>` instantiations currently live inside `libvulkan-guest.so`, so an H registration held in process-owned FEX state can name executable code owned by an unloadable guest wrapper generation.

The host→guest callback side independently retains guest `GuestUnpacker` and `GuestTarget` addresses. The preferred callback prototype now keeps escaped host trampoline bytes immutable and moves revocable lifetime state into an FEX-owned descriptor.

## Runtime facts now established

### Generated Vulkan moved-reload defect

A real generated-Vulkan stock/candidate A/B uses `vkGetInstanceProcAddr(NULL, "vkEnumerateInstanceVersion")`, forces the guest Vulkan wrapper to reload at a different guest base, and keeps the generated guest/host thunk binaries byte-identical across phases.

Observed:

```text
stock_hold=0
stock_close=139
stock_reload=139
candidate_hold=0
candidate_close=139
candidate_reload=0
```

The same native PFN H is returned across generations while the guest invoker T moves. Stock accepts the generation-2 registration but the newly reacquired PFN still crashes. Exact retirement/revocation followed by reactivation to T2 makes the call succeed.

See `../REAL_VULKAN_PFN_LIFETIME_AB_2026-08-14.md`.

### All-thread future-dispatch retirement is required

A worker can hold a hot H lookup after another thread retires the owner. Removing only shared state and the current thread cache is insufficient. The exact synthetic H must be invalidated from every live emulation thread's lookup cache when using baked-target compiled blocks.

### Execution quiescence is **not** supplied by cache invalidation

This is no longer an open source question.

A runtime barrier forced this sequence:

```text
worker selects T1 -> HostCode1
worker leaves lookup/invalidation guard
worker pauses
teardown removes H definition + shared mapping + H from every thread cache
teardown physically unmaps T1 owner
worker resumes already-selected HostCode1
SIGSEGV
```

The pin control resumes and returns successfully.

Therefore:

> future lookup retirement cannot revoke a transfer whose host-code selection already escaped the lookup/invalidation critical section.

Any physical-unload design must add execution ownership/quiescence, use a process-lived final bridge target, or keep the wrapper generation resident.

See `../TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`.

### Existing thread Pause is not an execution drain

FEX's pause machinery saves interrupted execution and later restores it. It is also external-control machinery rather than a guest-`munmap` primitive. Pausing a thread that already owns a selected old-generation transfer preserves the stale context rather than draining it.

See `../TWENTY_SECOND_PASS_PAUSE_IS_NOT_EXECUTION_DRAIN.md`.

### Failed `munmap` requires transaction semantics

Eager pre-unmap retirement can kill H even when an invalid `munmap` returns `EINVAL` and the old code remains mapped. Product retirement therefore needs prevalidation, rollback, or a two-phase transaction.

### Callback descriptor is preferred over mutable trampoline state

The successful descriptor prototype uses:

```text
escaped immutable host trampoline
    -> process-lived descriptor
         atomic LIVE / REVOKED
         GuestUnpacker
         GuestTarget
```

Moved reload and same-address ABA pass, and the descriptor design also coexists successfully with the real generated-Vulkan PFN lifetime candidate.

## Integration families

### 1. Keep generated guest wrappers resident

A central guest-thunk `-z nodelete` policy has real Vulkan runtime coverage for both:

- dynamic H→T PFNs retained across ordinary guest `dlclose()`;
- retained Vulkan/X11 host→guest callbacks after ordinary guest `dlclose()`.

Build coverage is green across the current 64-bit shared thunk set, representative real 32-bit thunking, VDSO's special link mode, and alternate lld thunk linking.

This is the strongest demonstrated containment and avoids execution reclamation races by not reclaiming wrapper executable state.

### 2. Split process-resident bridge runtime

Move only generic signature-specific adapter/unpacker code that FEX stores or exposes process-long into a resident guest bridge runtime. Keep library-specific wrapper state unloadable.

A standalone loader model already passes on x86-64 and AArch64. A stock-FEX synthetic thunk integration experiment is now the next gate.

If successful, generator integration can reuse the existing generated signature/thunk identity rather than inventing a new ABI discriminator.

### 3. Full owner-generation + execution lease/hazard

For true physical reclamation of all bridge code, bridge entry/selection must publish execution ownership of the target generation and unload must prevent new acquisitions then wait for old acquisitions to leave.

This is semantically complete but difficult in the current tail-transfer path. A prior simple active-counter/call-return prototype did not yield a usable runtime result.

### 4. Generation-neutral target cell

A stable compiled H block can load its current T from a process-lived cell and rebind generations without H cache replacement. This simplifies generation handoff but does not solve reclamation: another thread can load old T immediately before retirement and branch after unmap.

## Owner and compatibility metadata

A robust multi-owner implementation cannot discard non-winning H claims. Runtime evidence shows retaining compatible claims and promoting a surviving owner works.

The preferred compatibility identity is FEX's existing generated signature/thunk hash. Current `LinkAddressToFunction(H,T)` does not carry this metadata, so a generic owner registry would need an API extension or another reliable way to resolve signature identity.

For owner identity, raw guest target ranges are sufficient for diagnostics. A product implementation should reuse or extend FEX's existing VMA/load resource identity so one ELF load generation can own all relevant bridge claims across its VMAs.

## Current ordering invariant for physical unload

For a full-reclamation design the conceptual order is:

```text
identify owner generation
validate / stage the unmap transaction
mark generation draining / prevent new bridge acquisitions
retire future H and callback lookup paths
wait for already-acquired execution of that generation to leave
physically unmap guest executable state
commit owner/VMA retirement
```

The execution drain must not hold locks required by translated threads or callbacks as they leave the retiring generation.

## Remaining workload-specific uncertainty

The original Apple M5 `vulkaninfo` teardown proves execution reached the old unmapped Vulkan guest image and that pinning only `libvulkan-guest.so` changes exit 139 to exit 0. That historical trace did not capture the immediate terminal H/R11 or first post-unload synthetic-entry hit.

The hosted generated-Vulkan stock/candidate A/B independently proves the dynamic-PFN lifetime defect and successful generation rebind; do not rewrite the original M5 receipt as if its exact final transfer was captured.

All code discussed here is diagnostic/research code on owned surfaces. FEX contribution policy requires any upstream implementation to be independently derived and written by a human.