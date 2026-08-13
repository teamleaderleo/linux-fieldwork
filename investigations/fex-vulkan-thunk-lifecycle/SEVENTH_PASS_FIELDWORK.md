# Seventh-pass fieldwork: dynamic PFN lifetime, CustomIR eviction, and unload ownership

Date: 2026-08-14

Branch at start of pass: `investigation/fex-vulkan-thunk-lifecycle`

FEX revision executed by the retained investigation: `FEX-2608` / `e869aa644a16e4332cdc15c1ea0b4d13d482385d`

Current FEX source comparison used during this pass: `71afe476751deac24adabd1adb575fd2337b6e0a`

This note records the seventh source/history pass over the final `vulkaninfo` teardown crash. It deliberately separates observed crash evidence, source deductions, candidate ownership models, unresolved questions, and findings produced by other investigation lanes.

No upstream interaction is authorized or performed here. FEX's contribution policy forbids AI-generated contribution code. Everything below is research, diagnosis, experiment design, and pseudocode-level reasoning. A human contributor would need to independently derive any source change.

## Short version

The unload hypothesis became narrower.

The strongest source-level candidate is now a lifetime mismatch between:

- a process-lived native Vulkan PFN used as a synthetic FEX guest entrypoint;
- a CustomIR registration keyed by that native PFN;
- a compiled lookup-cache block for the native PFN;
- and the guest `CallHostFunction<...>` target inside `libvulkan-guest.so`, whose mapping can disappear on `dlclose`.

Two separate cleanup gaps exist in the examined FEX code:

1. Dynamic thunk CustomIR registrations have no lifetime retirement path tied to the guest target mapping.
2. `RemoveCustomIREntrypoint()` cannot reliably evict an already-compiled custom block through ordinary range invalidation, because custom blocks intentionally carry an empty `CodePages` dependency list.

The exact low-level cache primitive needed for a repair already exists: `GuestToHostMap::Erase(native_pfn)` erases the block and delinks inbound compiled callers. Per-thread L1/L2 state still needs exact invalidation at the same native PFN.

A correct retirement operation therefore appears to be an atomic CustomIR + exact-cache transaction under the code-invalidation lock, triggered when the guest target address range is unmapped.

The immediate predecessor of the final dead guest target remains the key runtime proof gap. The retained core may close it cheaply: on 64-bit guests FEX stores the native PFN in guest `R11` immediately before jumping to the guest `CallHostFunction` target. Inspecting guest `R11` at the retained no-exec fault is the highest-value next M5 probe.

## Evidence carried into this pass

The following observations were already executed and retained before this source pass:

- pristine `FEX-2608` reaches a SIGILL in the dynamic debug-report callback path;
- routing `vkCreateDebugReportCallbackEXT` dynamic lookup through FEX's existing callback-aware custom implementation removes that earlier SIGILL;
- `vulkaninfo --summary` then completes Vulkan enumeration and exits `139` during teardown;
- the native debug-report destroy call returns before the terminal crash;
- the stable native SIGSEGV stop is FEX's deliberate `GuestSignal_SIGSEGV` trampoline;
- FEX records an x86 page-fault-style synchronous fault with instruction-fetch semantics;
- the saved guest RIP is `0x7ffff7cd21f0`;
- at the crash, that RIP lies in an unmapped hole formerly occupied by `libvulkan-guest.so`;
- relative to the former guest thunk base, the offset is `0x4b1f0`;
- `addr2line` resolves that offset inside generated `CallHostFunction<...>` code in `ThunkLibs/include/common/Guest.h`;
- making guest `dlclose()` a no-op changes the post-callback-fix run from exit `139` to exit `0`;
- a bogus preload keeps exit `139`;
- pinning only `libvulkan-guest.so` changes the run to exit `0`;
- the pinned-thunk Venus run enumerates `Virtio-GPU Venus (Apple M5)` and exits `0`;
- llvmpipe reproduces the teardown failure, removing Venus/virtio/Apple GPU as requirements for the crash.

These remain the executed basis for the unload-localization claim.

## New finding 1: the no-exec RIP is stronger than the packet originally claimed

FEX-2608's `NoExecOp` uses `BreakOp` to synthesize a guest page fault. `BreakOp` stores the current attempted guest PC into `CPUState.rip` immediately before generating the synchronous fault.

That changes the interpretation of the retained fault record.

For this fault class, `State.rip = 0x7ffff7cd21f0` is the attempted guest execution target chosen by FEX's frontend for the no-exec path. It deserves more weight than a generic JIT-era saved RIP.

The safe bounded conclusion is:

> FEX attempted guest execution at an address in the old, already-unmapped Vulkan guest-thunk image, and that address resolves inside generated `CallHostFunction<...>` code.

There can still be uncertainty about the precise byte-level instruction boundary reported by DWARF/JIT bookkeeping. The attempted target belonging to the dead thunk image is much firmer.

## New finding 2: dynamic PFN CustomIR blocks are cached even though they have no guest code-page dependency

The FEX-2608 compile path distinguishes custom IR from decoded guest code.

For a CustomIR entrypoint:

- `GenerateIR()` sets `NeedsAddGuestCodeRanges = false`;
- `CompileBlock()` therefore leaves its local `CodePages` vector empty;
- `CompileBlock()` still calls `AddBlockMapping()` for the custom entrypoint;
- the resulting native-PFN entry therefore exists in the shared guest-to-host lookup map and may populate per-thread L1/L2 caches.

So the comment in the thunk handler that the synthetic thunk entrypoint does not need normal guest-code caching cannot be read as "this route has no compiled cache entry." It skips guest executable-page dependency tracking while still receiving compiled lookup-cache state.

That distinction is central to the teardown bug.

## New finding 3: ordinary range invalidation cannot discover those compiled CustomIR blocks

FEX's current two-pass invalidation model is dependency driven.

Shared-map range invalidation walks the reverse `CodePages` index to discover compiled blocks whose decoded guest code intersects an invalidated range. Each thread similarly tracks `CachedCodePages` to discover which local L1/L2 entries need invalidation.

A custom block with an empty `CodePages` list has no reverse edge in either system.

Consequences:

- unmapping `libvulkan-guest.so` can invalidate ordinary guest code in that range;
- it cannot discover the separately keyed compiled block whose guest entrypoint is the native Vulkan PFN;
- that compiled native-PFN block may still contain a constant exit to the now-dead guest `CallHostFunction` target;
- later dispatch to the native PFN can therefore reuse the compiled synthetic route without consulting the now-invalid guest target mapping first.

This is source-level support for the stale dynamic-PFN route. Runtime capture of the actual post-unload dispatch remains desirable.

## New finding 4: `RemoveCustomIREntrypoint()` has a separate cache-eviction defect

The current removal path does roughly:

```text
lock CustomIRMutex
erase CustomIR handler
update HasCustomIRHandlers
ask SyscallHandler to invalidate [Entrypoint, Entrypoint + 1)
```

For an ordinary decoded guest block, range invalidation can find dependent compiled entries through `CodePages`.

For an already-compiled CustomIR block, `CodePages` is empty. The same range invalidation therefore cannot find the shared L3 entry or thread-local L1/L2 entry for the synthetic entrypoint.

This means the generic CustomIR removal API can remove the generator while leaving already-compiled code reachable from the lookup caches.

Historical context supports why this could remain latent: a 2025 FEX commit described `RemoveCustomIREntrypoint` as unused while fixing a separate null-thread crash in it.

This cache defect deserves an isolated regression independent of Vulkan.

## New finding 5: exact block eviction already delinks direct compiled callers

`GuestToHostMap::Erase(Address)` does more than erase `BlockList[Address]`.

Before removing the block it walks inbound `BlockLinks` for that guest destination and invokes each recorded delinker.

That is important because FEX may backpatch a compiled caller directly to the synthetic native-PFN block. Erasing only a hash-map lookup entry would leave those direct links alive. The existing exact `Erase(native_pfn)` primitive already handles that part.

A narrow exact-eviction operation therefore needs two layers:

1. every live shared `GuestToHostMap`: exact `Erase(native_pfn)`;
2. every live guest thread: exact `InvalidateCache(native_pfn)` for L1/L2.

If a local cache entry was observed, the call/return shadow cache should also be cleared using the same policy FEX uses for ordinary code invalidation.

## New finding 6: removal and compilation need one lock transaction

`CompileBlock()` holds `CodeInvalidationMutex` shared across lookup, CustomIR generation, compilation, and lookup-cache insertion.

That gives a clean atomicity tool for retirement: take the same mutex uniquely while removing the registration and evicting every compiled cache layer.

Doing registration removal and cache eviction as two independent operations leaves races:

- remove handler, then another thread can still execute an old cached block before eviction;
- evict cache first, then another compiler can regenerate the old CustomIR block before handler removal.

There is also a likely lock-order problem in the existing unused removal API. Compilation takes code invalidation shared and can then consult `CustomIRMutex`; current removal takes `CustomIRMutex` and then enters the syscall/code-invalidation path. A new bulk retirement API should avoid preserving that inversion.

The existing ThreadManager cross-thread invalidation order is a good outer skeleton:

```text
ThreadCreationMutex
→ CodeInvalidationMutex unique
→ mutate/evict shared and per-thread translation state
```

CustomIR mutation can happen inside that transaction.

## Candidate transaction for the first diagnostic implementation

Research pseudocode only:

```text
guest munmap [start, end)
    ↓
ThreadCreationMutex
    ↓
CodeInvalidationMutex UNIQUE
    ↓
collect thunk CustomIR entries where
    Creator == ThunkHandler
    and Data guest_target ∈ [start, end)
    ↓
erase or retire those registrations
    ↓
for each affected native PFN:
    for every live shared GuestToHostMap:
        exact Erase(native_pfn)
        # also runs inbound delinkers

    for every guest thread:
        exact InvalidateCache(native_pfn)
        clear call/return shadow state if observed
    ↓
release
```

The first runtime candidate should be intentionally narrower than the eventual generic model. `GuestMunmap()` is the cleanest trigger for the observed `dlclose` failure because the target address ceases to exist there. `mremap` needs equivalent retirement when an old target range moves. Replacement mappings need equivalent treatment. `mprotect` deserves separate reasoning because loader protection transitions can be transient and do not necessarily mean the DSO generation ended.

## Why the VMA signal is useful

A 2023 FEX discussion raised the desire to clean up other library state on `dlclose`. The maintainer response was that after redirecting the thunk FD, FEX had lost loader-level control and had no good `dlclose` hook.

The modern VMA path gives a lower-level event that avoids reproducing glibc's DSO reference-count semantics.

`GuestMunmap()` knows:

- the exact guest VA range being removed;
- that the host unmap succeeded;
- and when to run FEX code invalidation before returning to guest userspace.

For this dynamic-PFN route, the registration already stores the guest target address as `CustomIRHandlerEntry::Data`. A target-range retirement operation can therefore ask a direct question:

> Which synthetic native PFN routes point into the guest range that just ceased to exist?

That is enough for the observed class of stale target without a symbolic library name or explicit `dlclose` interception.

## Historical finding: unregister/rebind was contemplated in the original feature

The history is unusually aligned with the present failure.

FEX PR #1760 introduced the generic guest-callable host function-pointer mechanism used by APIs such as Vulkan and GL proc-address lookup.

The PR explicitly listed:

```text
[x] Consider unregistering host-pointers on dlclose
```

as a design TODO that had received consideration.

An intermediate implementation had an explicit `RemoveGCHTrampoline(host_entrypoint)` operation. The later generic CustomIR work supplied `RemoveCustomIREntrypoint` as the generalized removal primitive.

The same 2022 review called out another edge still visible today: one stable host function pointer can map to different guest thunk targets. Current FEX's first-wins `emplace` behavior means a later load at a changed guest address does not replace the old target; it logs the collision and leaves the first route active.

That is exactly why unload → reload-at-different-base is such a useful discriminator.

## Candidate alternatives considered

### 1. Keep guest thunk wrappers resident

Pinning `libvulkan-guest.so` already turns the observed run from 139 to 0. A process-lifetime wrapper policy would align the wrapper with process-lived host thunk state and avoid dead guest invoker addresses.

Advantages:

- simple lifetime rule;
- covers dynamic PFN invokers and guest helper addresses that a host thunk stores;
- matches the successful control.

Costs/questions:

- changes normal `dlclose` residency semantics for every thunk wrapper;
- can retain state and mappings for process lifetime;
- does not exercise the unregister/rebind capability anticipated by the original guest-callable-host design;
- makes reload-generation behavior disappear instead of defining it.

I now view pinning as a strong control and a plausible fallback policy, while explicit retirement/rebind better matches the original feature's lifetime concerns.

### 2. Stable guest target addresses independent of wrapper mapping

A permanent FEX-owned guest trampoline could make the native PFN target survive guest DSO unload. The permanent trampoline would then dispatch through current owner metadata.

This can be elegant, especially for multi-owner cases, but it is a larger change than the present source evidence requires. It also still needs explicit ownership so the permanent trampoline knows whether a compatible live target exists.

### 3. Guest-wrapper destructor unregisters each PFN

A guest thunk could explicitly unregister its links while its own code remains mapped.

FEX history makes this unattractive as the primary trigger. The project has already encountered shared-library destructor behavior that did not reliably align with `dlclose`, and a 2023 discussion explicitly worried about relying on unload destructors. A VMA lifetime signal is harder to miss for the concrete dead-address case.

## Highest-value runtime proof: guest R11 in the retained core

For 64-bit guests, `AddThunkTrampolineIRHandler()` emits a synthetic block that:

1. stores the native host entrypoint/PFN into fixed guest register `R11`;
2. exits to the guest `GuestThunkEntrypoint` (`CallHostFunction<...>`).

At the terminal no-exec fault, the target page is already absent, so the guest `CallHostFunction` body cannot execute instructions that overwrite R11 before FEX synthesizes the fault.

That makes retained guest R11 a possible receipt for the immediate predecessor.

GDB probe:

```gdb
set $f = (FEXCore::Core::CpuStateFrame*)$x28
p/x $f->State.rip
p/x $f->State.gregs[11]
p/x $f->State.gregs[4]
x/16gx $f->State.gregs[4]
```

Primary interpretation:

```text
State.rip in old CallHostFunction target range
+
R11 equals a native Vulkan PFN that FEX previously linked
=
very strong direct receipt for
native PFN synthetic block → old guest invoker → no-exec fault
```

If R11 is unrelated or has been overwritten, the result is still useful and the next step becomes stack/call-ret reconstruction.

## Suggested R11 decision table

| R11 result | Interpretation | Next action |
| --- | --- | --- |
| matches logged Vulkan PFN | immediate dynamic-PFN predecessor strongly supported | identify exact PFN/name if possible; run retirement candidate |
| plausible host executable address but no prior log | dynamic route remains plausible; logging coverage incomplete | resolve host mapping/symbol and rerun with link logging |
| ordinary guest address / small value | synthetic PFN predecessor weakened | inspect call/return shadow state and guest stack |
| points to another thunk/helper | alternate FEX thunk route | trace that helper's lifetime and registration source |

## Synthetic regression A: CustomIR removal/cache correctness

This test isolates the generic cache bug from Vulkan and ELF unloading.

Concept:

```text
install CustomIR handler A at synthetic entrypoint H
execute H so A is compiled and cached
remove handler A
install handler B at the same H
execute H again
```

Expected correct result: second execution reaches B.

A stale-cache result that still reaches A would directly demonstrate that the removal API failed to evict the compiled custom block.

The test should exercise both a direct lookup and a caller that has linked/backpatched to H, because exact `GuestToHostMap::Erase()` is expected to sever those inbound links.

## Synthetic regression B: guest-thunk unload/reload at changed address

The existing `libfex_thunk_test` is a good integration surface because it already has a real guest wrapper, process-lived host thunk, native test library, and FEX Linux-test harness.

Add a proc-address-style API whose returned native function pointer remains stable while the guest wrapper can reload.

Test sequence:

```text
load libfex_thunk_test guest wrapper
obtain stable native PFN through proc-address path
link native PFN to guest CallHostFunction invoker
call it successfully
record old guest invoker page

dlclose guest wrapper
reserve old guest page with MAP_FIXED_NOREPLACE
reload wrapper, forcing changed guest base
obtain same stable native PFN again
call it
```

Baseline prediction under first-wins registration:

```text
same native PFN key
+ changed guest target
→ old target remains active
→ stale route / collision
```

Lifetime-aware prediction:

```text
old load generation retired
same native PFN re-claimed by new generation
→ route reaches new guest image
```

The current thunk Linux-test fixture opens its thunk library and keeps the handle for the fixture lifetime, so existing cases largely sidestep this unload/reload behavior. A dedicated case closes that coverage gap.

## Generic multi-owner problem

The Vulkan-sized repair and the fully generic design are slightly different tasks.

A single native PFN can legitimately acquire several guest claims:

```text
native PFN H
  ↳ guest target A, load generation 1
  ↳ guest target B, load generation 2
```

Current FEX keeps the first active target and reports later mismatches. Simply deleting the first owner on unload could discard a still-live compatible second claim.

A more complete owner model should retain claims and distinguish:

- active compatible owner;
- dormant compatible owners;
- incompatible collisions retained for diagnosis;
- tombstoned synthetic keys whose native PFN identity remains known after all owners disappear.

On active-owner retirement:

- invalidate the compiled synthetic path;
- promote the oldest/specified surviving ABI-compatible claim;
- leave the key tombstoned if no compatible owner survives;
- allow a later compatible reload generation to revive the tombstone.

This is where the parallel owner-registry experiment becomes relevant.

## Relationship to the parallel load-generation owner model

A separate lane on this investigation branch added `thunk_owner_registry_probe.cpp` and retained a `22 passed / 0 failed` synthetic result.

That model exercises:

- first-owner activation;
- explicit owner revocation;
- compiled synthetic-key invalidation;
- tombstones retaining native PFN identity;
- compatible dormant-owner promotion;
- incompatible-ABI collision retention without automatic promotion;
- changed-generation reload and rebind;
- one generation revoking several aliased synthetic keys;
- preservation of unrelated owners;
- distinction between formerly synthetic native PFNs and arbitrary guest addresses.

This affects my design conclusions in a bounded way:

- it increases confidence that load-generation ownership, tombstones, compatible promotion, and reload semantics form a coherent generic model;
- it independently lands on the same multi-owner concern that appeared in the 2022 FEX review and in this source pass;
- it gives a ready vocabulary for separating active route identity from native PFN identity.

It does **not** increase the confidence of the observed M5 crash mechanism by itself. It is a synthetic model. The crash still rests on the retained M5 evidence plus the FEX-2608 source path. Runtime R11 or equivalent dispatch capture remains the clean bridge between those two layers.

## Relationship to Agent B callback findings

`agent-b/` is focused on the earlier callback-routing failure. Its reduced debug-report/debug-utils programs intentionally keep `libvulkan.so.1` resident through process exit so the callback experiment stays independent of the unload finding.

Therefore:

- Agent B can strengthen or revise the earlier dynamic callback-routing finding;
- it does not replace this teardown-lifetime investigation;
- if callback-specific results change, they affect the setup required to reach teardown, while the late dead-thunk target and unload controls remain separately interpretable.

This is a useful example of parallel results touching the same library without belonging to the same causal chain.

## Open questions after this pass

### Immediate dispatch proof

- What is guest R11 at the retained terminal no-exec fault?
- Does it equal one of the native Vulkan PFNs registered by `LinkAddressToFunction`?
- Can that PFN be resolved to the exact Vulkan command whose synthetic block jumped to the old `CallHostFunction` target?

### Registration ownership

- Is `CustomIRHandlerEntry::Data` used anywhere else with semantics that would conflict with treating it as the guest-target ownership address for thunk handlers?
- Should the generic API expose load-generation owner identity directly instead of inferring lifetime solely from target ranges?
- Can one guest load generation produce aliases across several native PFNs that should be retired together? The owner-registry model says yes; real thunk generation should be audited.

### Cache retirement

- What is the clean public/core API for exact synthetic-entry eviction across every code buffer and thread cache?
- Should `RemoveCustomIREntrypoint()` be rewritten around exact eviction even before any thunk-specific lifetime policy is added?
- Which call/return cache clearing is required after exact custom entry eviction?

### Mapping events

- `munmap`: clear trigger for the observed case.
- `mremap`: old target range may move; retirement/rebind semantics needed.
- `MAP_FIXED` replacement: old target may disappear without a standalone `munmap`; audit required.
- `mprotect`: loss of execute permission may be transient; avoid conflating permission transitions with load-generation death until real cases require it.

### Concurrency

- Current FEX already performs VMA bookkeeping and code invalidation in separate lock phases after `munmap`. Is that existing post-unmap window acceptable for synthetic target retirement too?
- Can another guest thread legally call a PFN while its owning DSO is being unloaded? Application-level behavior may already be undefined, but FEX's internal state should still avoid resurrecting a retired route.
- Does owner retirement need to happen before the host `munmap`, or is the existing post-success invalidation phase sufficient for supported semantics?

### Host-to-guest callbacks

- Permanent helper trampolines used by Vulkan/GL rebind cleanly when OnInit runs at a new guest base because the cache key includes guest target/unpacker and host-side pointers are overwritten.
- A host library object retaining a callback trampoline beyond the guest DSO's legal lifetime remains a separate escaped-callback issue.
- Normal API teardown should destroy those objects before `dlclose`; a dedicated misuse/hardening test could examine this later.

### `Libs` lifetime bookkeeping

- `ThunkHandler_impl::Libs` still carries the TODO about unloading libraries and remains process-lived.
- Does any future unload-aware route need to retire entries from `Libs`, or is it correctly a host-thunk-residency set while guest generations are tracked separately?
- Avoid coupling host thunk residency to guest wrapper generation unless a concrete need appears.

## Candidate experiment matrix

| Experiment | Registration retired? | Compiled synthetic route evicted? | What it tests |
| --- | --- | --- | --- |
| baseline | no | no | current crash |
| handler retirement only | yes | no | whether cached block alone sustains stale route |
| exact/full cache eviction only | no | yes | whether stale registration recompiles the route |
| both | yes | yes | core lifetime hypothesis |
| guest wrapper pinned | irrelevant | irrelevant | existing lifetime control |
| unload + changed-base reload | should retire/rebind | should evict/recompile | reload ownership correctness |

For the M5 crash, the most useful source candidate is still "both." The two partial variants are valuable diagnostic A/Bs if they can be implemented locally without excessive churn.

## Confidence ledger

### High confidence

- the final fault is a guest instruction-fetch no-exec/page-fault path synthesized by FEX;
- the attempted guest target belongs to the old unloaded Vulkan guest-thunk image;
- the target resolves inside generated `CallHostFunction<...>` code;
- guest thunk residency changes the outcome 139 → 0;
- custom thunk PFN handlers can compile into lookup-cache blocks with empty guest `CodePages` dependencies;
- ordinary range invalidation cannot discover those custom blocks through the reverse page indexes;
- exact `GuestToHostMap::Erase(native_pfn)` delinks inbound callers;
- current `RemoveCustomIREntrypoint()` uses a range invalidation path that is unsuitable for already-compiled custom blocks.

### Medium-to-high confidence

- stale dynamic-PFN CustomIR state is the leading owner of the final dead target;
- unload-triggered retirement keyed by guest target range is a viable first repair direction;
- exact registration + cache retirement should be one code-invalidation transaction.

### Open

- exact native PFN immediately preceding the terminal old `CallHostFunction` target;
- whether a second live compatible owner exists for any PFN involved in this specific `vulkaninfo` run;
- exact public API boundaries for a polished generic owner model;
- concurrent unload/call semantics beyond the single-threaded observed teardown;
- mremap/MAP_FIXED/general replacement coverage.

## Next field steps

1. **Retained core: inspect guest R11.** This is the cheapest remaining direct causal receipt.
2. Resolve R11 to a logged/link-time native Vulkan PFN if possible.
3. Build the isolated CustomIR remove/reinstall regression in a local research harness.
4. Build the `libfex_thunk_test` proc-address unload/reload regression with a forced changed guest base.
5. Compare four diagnostic behaviors: baseline, registration-retire only, cache-evict only, both.
6. If "both" changes the M5 terminal failure, inspect the new terminal state before claiming success; a different fault can reveal a second stale owner.
7. Only after the narrow tests converge, decide whether the generic implementation should use target-range retirement alone or explicit load-generation owner IDs plus target-range lifecycle signals.

## Working conclusion

The seventh pass moves the leading explanation from a broad "guest thunk unloaded while FEX retained something" to a specific two-layer stale route:

```text
stable native Vulkan PFN
        ↓ synthetic guest entrypoint key
CustomIR handler
        ↓ compiles once
lookup-cache block with empty CodePages dependency
        ↓ stores native PFN in R11
constant exit to guest CallHostFunction<...>
        ↓
libvulkan-guest.so unloads
        ↓
guest target disappears
        ↓
registration + compiled synthetic route can survive
        ↓
subsequent dispatch reaches old target
        ↓
NoExecOp / guest #PF / SIGSEGV
```

The source supplies every edge in that chain except the final runtime receipt that the specific terminal dispatch came through the synthetic native-PFN block. Guest R11 in the retained core is the shortest path to closing that gap.
