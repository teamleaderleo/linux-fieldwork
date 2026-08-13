# CustomIR/JIT lifetime refinement — FEX Vulkan guest-thunk unload

## Why this refinement exists

The earlier adversarial review framed the decisive proof as a post-unload `CustomIRHandlers` hit selecting an unmapped guest thunk target. Source review of the exact executed FEX-2608 revision shows that proof requirement was too strict.

A dynamic host-PFN thunk can hit `CustomIRHandlers` once, compile an ordinary host JIT block, and then execute from the runtime lookup cache on later calls without consulting the CustomIR registry again. The immediate stale object can therefore be the compiled block generated from CustomIR even when there is no second post-unload `CUSTOMIR_HIT` event.

This does **not** rescue an ordinary generic-JIT explanation. The source distinction is that normal guest blocks are associated with their guest executable source ranges for invalidation, while CustomIR-generated blocks deliberately skip that source-range association. The generated block is indexed by the native host PFN `H`, while it embeds a dependency on guest target `T` inside `libvulkan-guest.so`. Unmapping `T`'s DSO naturally invalidates `T`-range guest code but has no recorded reason to invalidate the compiled block at `H`.

## Refined lifecycle

For a dynamic Vulkan function pointer:

```text
native Vulkan PFN H
        |
        | vkGetInstanceProcAddr/vkGetDeviceProcAddr
        v
Guest.cpp MakeGuestCallable(name, H)
        |
        | HostPtrInvokers[name] = guest CallHostFunction helper T
        | LinkAddressToFunction(H, T)
        v
FEX AddThunkTrampolineIRHandler(H, T)
        |
        | CustomIRHandlers[H] captures T
        v
first guest call to H
        |
        | GenerateIR sees CustomIRHandlers[H]
        | emits an exit to T
        | HasCustomIR = true
        v
compiled host/JIT block J keyed by H
        |
        | CustomIR path deliberately does not add normal guest-code ranges
        v
later calls to H can execute J directly

then:

guest dlclose(libvulkan-guest.so)
        |
        | GuestMunmap invalidates ordinary translated code for T's unmapped ranges
        | J has no recorded T-range dependency
        v
J survives and still contains/selects T
        |
        v
instruction fetch at old unmapped T
        |
        v
SIGSEGV / exit 139
```

## Exact source observations

### 1. Vulkan returns H to the application and keeps T private

At FEX-2608, `ThunkLibs/libvulkan/Guest.cpp` maps Vulkan function names to generated guest `CallHostFunction` invokers. `MakeGuestCallable()` calls `LinkAddressToFunction((uintptr_t)func, It->second)` and then returns `func`, the native host Vulkan PFN, to the guest application.

Therefore the application-facing dynamic PFN is `H`. The guest helper `T` remains an implementation address handed to FEX for redirection.

This makes an ordinary guest-loader/application stale pointer to the observed `CallHostFunction` helper materially less likely: the normal dynamic-PFN API path never returns `T` to the application.

### 2. `AddThunkTrampolineIRHandler(H,T)` captures T under H

`Source/Tools/LinuxEmulation/Thunks.cpp` handles `fex:link_address_to_function` by calling `CTX->AddThunkTrampolineIRHandler(original_callee, target_addr)`.

`FEXCore/Source/Interface/Core/Core.cpp` registers a CustomIR handler at `H` that emits an exit to captured guest target `T`; the registration records the thunk handler as creator and `T` as data.

### 3. CustomIR-generated blocks skip normal guest-code-range association

In FEX-2608 `GenerateIR`, a CustomIR handler sets `HasCustomIR = true`. The returned compile metadata uses `NeedsAddGuestCodeRanges = !HasCustomIR && ...`.

`CompileBlock` always adds the compiled block mapping for the block's `GuestRIP` (here `H`), but only adds guest executable source ranges when `NeedsAddGuestCodeRanges` is true.

So the block generated for `H` is intentionally outside the ordinary page/range tracking that associates translated guest code with the DSO pages from which it was decoded.

### 4. `GuestMunmap(T-range)` invalidates the range it is told about

At FEX-2608 the guest `munmap` path tracks the unmapped range and calls `InvalidateCodeRangeIfNecessary(Thread, addr, aligned_size, ...)`.

The thread manager invalidates code-buffer and per-thread lookup-cache state for that address range. This is the correct ordinary invalidation mechanism for guest code whose recorded source ranges intersect the DSO being unmapped.

The missing relationship is `H-generated block J depends on T`. The unmap operation sees `T`'s range; the generated block is indexed by `H` and skipped T-range source association.

### 5. The paired remover invalidates H

`RemoveCustomIREntrypoint(Thread, H)` erases the registry entry and calls `InvalidateGuestCodeRange(Thread, H, 1)`.

That invalidates the lookup/JIT state at the exact `H` key that `T`-range unmap cannot naturally discover. Current thunk load/link code has no guest-DSO unload owner that invokes this paired remover for dynamic host PFNs.

Historical context:

- `https://redirect.github.com/FEX-Emu/FEX/pull/1760` introduced guest-callable host pointers for APIs including Vulkan/GL and explicitly considered unregistering host pointers on `dlclose`.
- `https://redirect.github.com/FEX-Emu/FEX/pull/1770` introduced generic CustomIR add/remove machinery.
- `https://redirect.github.com/FEX-Emu/FEX/commit/8b14bd4e87e5b91a018be1030178d63e351a1e80` later fixed `RemoveCustomIREntrypoint` while describing it as unused.

## Why the earlier four-event proof was insufficient

Earlier proposed proof:

```text
REGISTER H -> T
UNMAP T
CUSTOMIR HIT H -> T
FAULT T
```

A post-unload `CUSTOMIR HIT` is sufficient but **not necessary**. If `H` was compiled before unload, a later call can reach the previously generated host block directly through the lookup cache. No second call to `GenerateIR` is required.

The stronger experiment must observe or manipulate both layers independently:

1. CustomIR registration `R: H -> T`.
2. compiled runtime block `J` produced from `R` and indexed by `H`.

## New 2 × 2 causal experiment

The most discriminating local FEX experiment is to vary registry state and compiled-H-block state separately after the guest DSO unmaps.

| Variant after T-range unload | CustomIR registration H→T | compiled H block J | Prediction |
| --- | --- | --- | --- |
| baseline | retained | retained | crash if current theory is right |
| remove registry only | removed | retained | **crash should persist** if J is the immediate stale object |
| invalidate H block only | retained | invalidated | next H call recompiles through stale H→T registration, then crashes at T; a fresh `CUSTOMIR_HIT` should become visible |
| remove registry + invalidate H | removed | invalidated | late H call can no longer regenerate stale T; crash should disappear or change class |

This separates two statements that were previously conflated:

- **lifetime owner defect:** H→T registration outlives the guest DSO;
- **immediate execution vehicle:** a previously compiled H block may survive and be executed without another registry lookup.

A local diagnostic helper can implement these variants by finding CustomIR entries whose recorded `Data` target lies within an unmapped guest range, then independently erasing the registry entry and/or invalidating the compiled `H` key. This is experiment code for the owned fork only.

## Strongest current counterexamples

### Changed-base fresh reacquisition

A generic libGL probe has been prepared in Fieldwork:

`generic_gl_pfn_reload_probe.c`

It loads `libGL`, obtains `glGetError` through `glXGetProcAddress`, unloads the guest thunk, reserves the old guest DSO base, reloads at a changed base, freshly reacquires `glGetError`, and calls that newly reacquired PFN.

This avoids an application-stale-pointer explanation. If the native host PFN stays stable while the guest invoker `T` moves, current duplicate registration behavior should expose whether the old H→T lifetime survives reload.

A clean changed-base reload with a fresh PFN would materially weaken the leading theory.

### Generic thunk control

libGL uses the same `indirect_guest_calls` mechanism as Vulkan. Reproducing the failure there would establish that the lifetime defect is generic to dynamic function-pointer thunking and that Vulkan merely exposes it during teardown.

## Callback trampoline alternative

FEX also caches host→guest callback trampolines containing raw guest unpacker/target addresses, with no visible guest-DSO lifetime key. That remains a genuine generic lifetime hazard.

For this crash it is a weaker immediate-cause candidate because the recorded dead guest RIP resolves to a generated `CallHostFunction<...>` helper, matching the dynamic host-PFN path. A stale host→guest callback would normally first enter a `CallbackUnpack<...>::Unpack` helper.

Diagnostic tracing in the owned FEX fork should retain both classes so a callback invocation can be ruled in/out empirically.

## Host/guest thunk lifetime asymmetry

Another source observation strengthens the generic-lifetime interpretation. The host thunk loader `dlopen`s host thunk DSOs and records their exported functions and loaded names in process-lived FEX state. There is no paired host-thunk unload path corresponding to a guest `dlclose` of `libvulkan-guest.so`.

So it is normal for the host thunk/native PFN side of the bridge to outlive the guest image that supplied the guest helper targets. A correct design therefore needs explicit ownership/revocation for the cross-lifetime H→T relationship; guest address-range invalidation alone cannot express it.

## Hosted callback CI contamination

The existing hosted ARM64 callback probe must not be interpreted as evidence that callback lookup routing failed.

Its captured run selected `HostThunks_32/libvulkan-host.so` for an x86-64 guest through a `find ... | head -1` path and used a minimal x86 rootfs without `libX11.so.6`. Vulkan guest initialization therefore attempted unrelated X11 callback bridge setup with null guest targets and died in `MakeHostTrampolineForGuestFunction` before the debug-report/debug-utils routing discriminator.

The hosted source audit remains useful; the runtime matrix from that lane is contaminated by setup and should be excluded from causal conclusions until repaired.

## Owned fork diagnostic branch

Diagnostic trace tooling is retained in the writable fork on:

`teamleaderleo/FEX:fieldwork/thunk-lifetime-trace-2608`

rooted exactly at executed FEX-2608 revision `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

`Fieldwork/apply_thunk_lifetime_trace.py` instruments:

- H→T thunk links;
- CustomIR registration/duplicates/removal;
- CustomIR compilation hits;
- guest munmap/invalidation boundaries;
- host→guest callback trampoline creation/reuse/invocation.

The trace should now be extended with explicit H lookup/JIT invalidation controls because a new post-unload CustomIR compilation hit is not required for the failure.

## Current conclusion

The broad phrase “FEX retains thunk execution state after Vulkan guest-thunk unload” remains true but underspecified.

The source-supported diagnosis is now:

> Dynamic function-pointer thunking creates a cross-lifetime dependency from native host PFN `H` to guest helper `T`. CustomIR uses that relationship to generate a runtime block keyed by `H`, while normal guest unmap invalidation operates on `T`'s DSO range. CustomIR-generated blocks deliberately skip normal guest source-range association, and no thunk unload owner revokes the H→T relationship and invalidates H. Consequently both the registration and already-generated H block can outlive `T`.

The exact remaining runtime gap is to prove which retained layer is consumed by the observed late call:

- existing compiled H block;
- stale H→T registration after forcing H recompilation;
- or a different pointer/trampoline class.

The 2×2 registry/block experiment plus the changed-base libGL fresh-reacquisition probe are the strongest next discriminators.
