# FEX thunk lifetime: history, intent, and compatibility constraints

This note extends the Vulkan guest-thunk teardown investigation with historical design intent and compatibility constraints. It is an owned-repository engineering record. FEX upstream remains read-only.

Related internal records:

- [README.md](./README.md)
- [EVIDENCE.md](./EVIDENCE.md)
- [ADVERSARIAL_REVIEW.md](./ADVERSARIAL_REVIEW.md)
- [CUSTOM_IR_FINDINGS.md](./CUSTOM_IR_FINDINGS.md)
- [DYNAMIC_CUSTOM_ROUTING_AUDIT.md](./DYNAMIC_CUSTOM_ROUTING_AUDIT.md)
- [lifetime-designs/README.md](./lifetime-designs/README.md)

Reviewed current source snapshot: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Executive conclusion

The current unload problem fits a long-standing ownership gap in FEX's generic function-pointer thunk machinery.

The machinery was introduced to make **native host function pointers directly usable as guest-visible function pointers**, especially for APIs such as `vkGetDeviceProcAddr` and `glXGetProcAddress`. The original design discussion explicitly considered unregistering those host pointers on `dlclose`, while also identifying hard cases where one native host pointer can correspond to different guest wrappers.

Later FEX history documents the missing lifecycle owner from another angle: after a thunk library FD is redirected into the guest loader, FEX does not retain a convenient loader-level `dlclose` interception point. XCB teardown work in 2023 therefore moved resource lifetime away from DSO destructors. In 2025, `RemoveCustomIREntrypoint` was repaired while its commit message still described it as unused.

Current source keeps the host thunk side loaded while guest thunk DSOs can disappear. The guest-side wrapper address is captured by CustomIR and by host-to-guest trampoline state, while the host-side thunk definitions and native library pointers can remain alive. This creates a direct lifetime asymmetry.

That history changes the preferred repair direction in two important ways:

1. **Guest `munmap` / VMA retirement is a stronger lifecycle observation point than a guest `dlclose` hook.** FEX always sees the disappearing guest executable mapping even when it has lost loader-level control.
2. **Raw deletion of a synthetic host-PFN CustomIR key is insufficient as a final design.** After deletion and compiled-code invalidation, a stale guest call to that native PFN can fall through to ordinary x86 frontend decoding at a host-native address. A revoked/tombstoned synthetic entry, or a stable indirection object, gives a safer post-unload state and allows a later reload to rebind the same native PFN.

The decisive runtime edge for the current Vulkan crash remains the four-event trace:

```text
REGISTER host_pfn=H -> guest_target=T
UNMAP    guest thunk range containing T
CUSTOMIR HIT H -> T while T is dead
FAULT     at/inside T
```

Until that is captured, stale CustomIR remains the strongest immediate-cause hypothesis rather than a completed end-to-end proof.

## Historical timeline

### 2022: host function pointers become guest-callable

Upstream PR [FEX-Emu/FEX#1760](https://redirect.github.com/FEX-Emu/FEX/pull/1760), **“Thunks: Support returning host function pointers to the guest”**, introduced the generic mechanism used by `vkGetDeviceProcAddr`, `vkGetInstanceProcAddr`, and `glXGetProcAddress`.

The stated compatibility goal was broader than Vulkan or Mesa: make APIs that return runtime function pointers work generically across vendors, multiple devices, vtables, and libraries without a 1:1 symbol-name mapping.

The central design choice was that the guest receives the **native host function pointer value itself**, and FEX teaches its dispatcher that this otherwise non-guest address is a synthetic guest-call entrypoint. The guest wrapper receives the original native address through an implicit register and marshals the call to the host.

The PR's soft TODO list explicitly included:

> Consider unregistering host-pointers on dlclose

The wording demonstrates that unload ownership was recognized during the original feature design. It does not by itself prove a finished `dlclose` cleanup path ever shipped.

The same discussion also identified a compatibility edge that remains important now: **one host pointer can be mapped to different guest thunks**, including mappings originating in different libraries. An early implementation asserted when the same host entrypoint was reinserted with a different guest wrapper.

That means any lifetime repair has to account for aliases and ownership; a global `host pointer -> one guest DSO` assumption is too narrow.

### 2022: generic CustomIR add/remove semantics

Upstream PR [FEX-Emu/FEX#1770](https://redirect.github.com/FEX-Emu/FEX/pull/1770) generalized the mechanism as `CustomIREntrypoints`.

Its design explicitly paired:

```text
AddCustomIREntrypoint
RemoveCustomIREntrypoint
```

and named guest-callable host functions as a use case.

An early guest-callable-host implementation, commit [`9ad701a3c14d79d9522aec8a635827099626dd1a`](https://redirect.github.com/FEX-Emu/FEX/commit/9ad701a3c14d79d9522aec8a635827099626dd1a), likewise contained both:

```text
AddGCHTrampoline(host_entrypoint, guest_thunk_entrypoint)
RemoveGCHTrampoline(host_entrypoint)
```

with removal erasing the synthetic host key and invalidating translated code at that key.

So synthetic-key removal and code-cache invalidation were part of the mechanism's conceptual model from its early implementation. The unresolved part is **who owns the removal and when it is safe to perform it**.

### 2022: signature-based function-pointer semantics broaden

Upstream PR [FEX-Emu/FEX#1868](https://redirect.github.com/FEX-Emu/FEX/pull/1868) expanded the machinery substantially for X11, callbacks, vtables, and global function pointers.

A major stated design property was that guest-callable host functions and host trampolines should be based primarily on the **function signature**, rather than on one named symbol. Current generator code still derives the callback-thunk SHA from:

```text
"fexcallback_" + function_pointer_signature
```

This matters for lifetime ownership. Two different guest DSOs can contain distinct wrapper addresses that are semantically the same signature adapter. Treating each wrapper address as the complete identity loses that relationship.

The same PR documented large compatibility gains across X11/OpenGL/Vulkan games, which means a generic lifetime fix has to preserve behavior beyond the current `vulkaninfo` reproducer.

### 2023: FEX records the loader-lifecycle problem explicitly

Issue [FEX-Emu/FEX#2369](https://redirect.github.com/FEX-Emu/FEX/issues/2369) records an XCB thunk shutdown bug caused by relying on shared-library destructors. The issue states that shared-library global destructors are not reliably called at `dlclose`, which could leave an XCB thread alive and hang shutdown.

The resulting PR [FEX-Emu/FEX#2583](https://redirect.github.com/FEX-Emu/FEX/pull/2583) moved XCB cleanup toward explicit resource lifetime.

A review question asked whether FEX could hook `dlclose` and manually clean other thunk libraries. The maintainer response was that once FEX had redirected the thunk-library FD for guest loading, it lost control of that unload and had not found a good workaround.

That is directly relevant to the present Vulkan lifetime problem. It explains why a theoretically obvious `dlclose -> remove every bridge owned by this DSO` solution may have remained absent: the architecture does not expose a dependable guest-loader callback at the point the original function-pointer machinery would want one.

### 2023: 32-bit support adds ABI constraints

Upstream PR [FEX-Emu/FEX#3225](https://redirect.github.com/FEX-Emu/FEX/pull/3225) extended function-pointer support to 32-bit guests.

Relevant constraints include:

- the guest-side thunk transport uses 64-bit fields even for 32-bit pointer values because the host runtime expects that representation;
- the implicit native host address is carried in `mm0` for 32-bit guests instead of `r11`;
- 32-bit callback/function-pointer support has additional address-space constraints.

A lifetime/ownership API should therefore avoid baking in an x86-64-only register or pointer-size model.

### 2025: the removal primitive is repaired and still described as unused

Commit [`8b14bd4e87e5b91a018be1030178d63e351a1e80`](https://redirect.github.com/FEX-Emu/FEX/commit/8b14bd4e87e5b91a018be1030178d63e351a1e80) fixed `RemoveCustomIREntrypoint` so it could invalidate code with a valid thread object.

The commit message says:

```text
Unused, but would have crashed prior due to providing a nullptr thread.
```

This is strong historical evidence that the add/remove abstraction survived while the ordinary thunk lifecycle still did not have a production owner invoking the remover.

## Current source: host/guest lifetime asymmetry

Current `Source/Tools/LinuxEmulation/Thunks.cpp` contains several clues.

### Host thunk libraries are retained

`ThunkHandler_impl::LoadLib()` calls host `dlopen()` for `<name>-host.so`, uses the resulting handle to obtain exports, and does not retain the handle for a later `dlclose()`.

The practical result is a process-lived host thunk side once loaded.

At the same time, the guest dynamic loader is free to release `libvulkan-guest.so`. The retained field evidence demonstrates that this guest DSO really does disappear during the failing teardown.

That creates the lifetime asymmetry:

```text
host thunk / native Vulkan PFN     remains alive
FEX synthetic dispatch state       can remain alive
guest CallHostFunction wrapper     can be unmapped
```

### FEX source already acknowledges missing unload tracking

`ThunkHandler_impl::Libs` has a current source comment stating that FEX ideally would track when a library is unloaded and remove it from the set before the backing memory disappears.

That is an independent current-code signal that thunk-library lifetime is incompletely represented.

### Guest loading has a constructor but no symmetric unload notification

`ThunkLibs/include/common/Guest.h` defines `LOAD_LIB*` through a guest-side constructor which tells FEX to load/register the corresponding host thunk library.

There is no matching general unload/destructor notification in that interface.

So registration is explicit while retirement is inferred only indirectly from guest memory events.

## Why `munmap` / VMA retirement is attractive

The 2023 loader discussion makes a direct `dlclose` hook difficult, while the Linux syscall layer always sees successful guest mapping retirement.

For executable bridge safety, the hard event is ultimately **the guest code becoming unavailable**, not the spelling of the loader operation that caused it.

A generic VMA-driven owner can therefore cover more cases:

```text
dlclose -> munmap
manual munmap
mremap that removes/moves executable code
mapping replacement
```

The owner should reason from the disappearing executable target range or mapped-resource generation to every FEX bridge that embeds a dependency on that range.

Current candidates include at least:

1. dynamic-PFN CustomIR entries whose `Data` / captured target points into the mapping;
2. compiled synthetic-key blocks generated from those entries;
3. `GuestcallToHostTrampoline` entries whose `GuestUnpacker` or `GuestTarget` points into the mapping.

A resource identity or load-generation token is stronger than address range alone because one ELF load spans multiple VMAs and addresses can later be reused.

## Revision to the first CustomIR cleanup candidate

The first candidate patch in this investigation used:

```text
remove matching CustomIR handlers
invalidate their synthetic native-PFN keys
```

That remains a useful mechanism experiment, because it proved the two stale-state layers have to be retired together.

It is now demoted as a production design candidate for two compatibility reasons.

### 1. Erasing a synthetic host key can expose normal frontend decode

CustomIR is checked before ordinary guest instruction decoding.

If a host-PFN handler is erased and the compiled mapping is invalidated, a later stale guest call to the same numeric host PFN can reach ordinary guest frontend decoding.

On an ARM host, that address can point at native ARM code. FEX then has a chance to interpret native bytes as x86 guest instructions instead of rejecting an expired synthetic pointer.

That is a poor failure mode even when native `dlclose` semantics make the stale function pointer invalid from the application's perspective.

A safer retirement state is a **revoked/tombstoned synthetic entry**:

```text
host PFN H remains recognized as a synthetic address
state = revoked
compiled H entry is invalidated
future stale calls reject/fault deterministically
reload can rebind H to a new guest target
```

This preserves the original guest-visible pointer identity while preventing frontend decode of a host-native address.

The semantic model for this distinction is retained in [`custom_ir_retirement_probe.cpp`](./custom_ir_retirement_probe.cpp).

### 2. First-wins insertion loses alternate live owners

Current `AddCustomIREntrypoint`/thunk registration semantics use first insertion as the active mapping. If the same native PFN is later presented with a different guest target, FEX treats it as a collision rather than retaining multiple owners.

The original 2022 discussion explicitly anticipated this across libraries.

Therefore a simple tombstone also has a limitation:

```text
DSO A: H -> T1   accepted
DSO B: H -> T2   rejected/unrecorded
unload DSO A
```

At that point FEX cannot promote `T2`, because it never retained B's claim.

Possible ownership models are:

- retain multiple claims keyed by load generation and signature, selecting a live compatible owner;
- use a process-lifetime signature adapter so equivalent wrappers do not depend on one guest DSO's code address;
- give each guest load a stable indirection slot and rebind the slot when compatible ownership changes;
- define and enforce that conflicting live owners are invalid, but then test real GL/Vulkan/X11 behavior to prove the restriction is compatible.

## SMC configuration is part of correctness

Current `RemoveCustomIREntrypoint` calls the syscall-handler invalidation path.

On Linux, `SyscallHandler::InvalidateGuestCodeRange()` routes through `InvalidateCodeRangeIfNecessary()`, which only invokes `ThreadManager::InvalidateGuestCodeRange()` when `SMCChecks != CONFIG_SMC_NONE`.

For an ordinary unmapped guest code page, SMC policy can reasonably control translation invalidation strategy. A synthetic host-PFN key is different: the key itself is outside the disappearing guest DSO range, and the compiled block embeds a hidden dependency on that DSO.

Retiring that hidden dependency must work independently of the SMC policy. A production API should either:

- invalidate synthetic entrypoint caches directly under FEX's code-invalidation synchronization, or
- define an explicit synthetic-entry invalidation primitive that is not suppressed by `SMC_NONE`.

The existing `ThreadManager::InvalidateGuestCodeRange()` implementation demonstrates the necessary synchronization pattern: it serializes thread creation and code invalidation, invalidates code buffers, then invalidates each thread's cached range.

## Concurrency and unload ordering

Cleaning state *after* the host `munmap()` succeeds leaves a window where another thread can acquire a still-active bridge whose target has already disappeared.

Cleaning state *before* `munmap()` avoids that window, but requires rollback or a staged state if `munmap()` fails.

A safer conceptual order is:

```text
identify disappearing guest load/range
authoritatively mark dependent bridges draining/revoked
invalidate compiled synthetic entrypoints
prevent new acquisitions
allow/handle in-flight transitions according to the chosen execution-lifetime rule
perform/finalize unmap
retire or retain tombstones for stale guest-visible pointers
```

Whether FEX needs a full execution lease for every indirect thunk call is still open. Native `dlclose` already requires applications to stop using a library's function pointers after unload. FEX's minimum obligation is to prevent **FEX-owned hidden bridge state** from extending the apparent lifetime of guest code and to avoid dispatching stale synthetic addresses as ordinary guest instructions.

This distinction may allow a cheaper implementation than the strongest synthetic `lease_slot` experiment while preserving correctness.

## Compatibility matrix that a real fix should cover

### Vulkan

- `vkGetInstanceProcAddr` and `vkGetDeviceProcAddr` native PFNs;
- same native PFN returned repeatedly;
- aliases where multiple names resolve to one host address;
- unload/reload at the same guest base;
- unload/reload at a different guest base;
- multiple Vulkan devices/drivers returning stable or differing PFNs;
- dynamic custom-host implementations and ordinary native implementations;
- stale PFN use after unload should reject safely rather than decode host code.

### GL / GLX

- `glXGetProcAddress` paths using the same generic mechanism;
- large function-pointer inventories;
- duplicate/same-signature aliases;
- Steam/Wine/X11 environments that historically relied on thunk preload/visibility behavior.

### X11 / callbacks / vtables

- host-to-guest trampoline cache ownership;
- signature-based wrappers;
- callbacks retained by host libraries longer than the guest DSO that created the wrapper;
- explicit resource lifetimes such as XCB's post-2023 approach.

### 32-bit guests

- 64-bit transport fields containing 32-bit pointer values;
- `mm0` implicit host-address ABI;
- lower-address-space requirements;
- no truncation when owner/generation metadata is added.

### SMC / caches

- `SMCCHECKS=mtrack`;
- `SMCCHECKS=full`;
- `SMCCHECKS=none`;
- code cache disabled/enabled where supported;
- compiled-before-unload and never-compiled-before-unload variants.

### Concurrency

- another guest thread calling the PFN while unload begins;
- callback host thread attempting guest transition during unload;
- reload racing with final retirement;
- fork/clone interactions with owner tables if the state is process-global.

## Refined implementation directions

### Direction A: VMA-driven tombstone + rebind

Smallest likely generic improvement over the range-erase sketch.

Store explicit thunk metadata per synthetic host key:

```text
host entrypoint
active guest target
load/resource identity or generation
signature identity if available
state: active / draining / revoked
```

Before a target mapping disappears:

1. revoke matching entries;
2. invalidate their compiled synthetic keys independently of SMC mode;
3. preserve a tombstone so stale calls never enter ordinary frontend decode;
4. permit compatible later registration to rebind the same host key.

Open problem: multiple simultaneous owners for the same host key.

### Direction B: retain multiple claims / promote compatible owner

Extend the synthetic host key from one target to a set of claims:

```text
H -> [owner A, T1, signature S]
     [owner B, T2, signature S]
```

When A unloads, select another live compatible claim.

This directly addresses the 2022 cross-library collision concern, at the cost of more bookkeeping and clear rules for incompatible signatures.

### Direction C: process-lifetime signature adapters

Move the hidden guest-facing adapter away from unloadable per-DSO text when possible. A stable FEX-owned guest-code/runtime adapter can hold only signature and host-PFN identity, while the unloadable guest DSO supplies metadata rather than executable target code.

This attacks the root lifetime mismatch and fits the generator's signature-based model, but it is a larger ABI/runtime redesign.

### Direction D: stable slot + generation / execution lease

The existing lifetime-design experiment's strongest model remains useful when strict concurrent unmap safety is required. A stable host-owned slot, generation identity, draining state, and execution lease prevents use-after-unmap even during active concurrent calls.

The remaining question is whether all of that machinery is necessary for native-compatible thunk semantics, or whether a staged revoke under existing FEX invalidation/loader synchronization is sufficient.

## New semantic probe

[`custom_ir_retirement_probe.cpp`](./custom_ir_retirement_probe.cpp) models the difference between raw erase and a revoked synthetic entry.

Its retained results are in [`retirement-probe-results.txt`](./retirement-probe-results.txt).

The important outcomes are:

```text
erase cleanup -> stale host key falls through to frontend decode
tombstone      -> stale host key rejects
reload         -> same host PFN can bind a new guest target
cross-owner    -> current first-wins model cannot promote an unrecorded second DSO claim
```

This is a semantic model, not an end-to-end FEX run.

## Current judgment

The historical intent and present source both strengthen the broad thunk-lifetime diagnosis.

The important refinement is that the problem is bigger than “remember to erase a hash-map row.” The function-pointer system intentionally exposes stable native host pointer values to guest software, supports signature-based wrappers across several thunk libraries, and has known cross-library pointer-collision cases. At the same time, FEX lacks a dependable guest `dlclose` ownership callback and keeps host-side thunk state alive longer than individual guest thunk DSOs.

The next implementation should therefore treat guest-thunk unload as **revocation of executable dependencies**, not merely deletion of guest code pages. The most useful immediate runtime work remains the four-event CustomIR trace plus equivalent logging for host-to-guest trampolines. That will identify which hidden bridge consumes the dead Vulkan target and tell us which generic owner path must be fixed first.
