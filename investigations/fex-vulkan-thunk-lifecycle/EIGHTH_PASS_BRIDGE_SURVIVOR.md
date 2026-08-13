# Eighth pass: surviving dynamic-PFN bridge after guest-thunk unmap

Status: internal Linux Fieldwork investigation record for issue #672. FEX upstream remains read-only. Any AI-assisted implementation work is diagnostic research only and is not presented as an upstream contribution.

Executed revision under the original runtime investigation: FEX-2608, `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

Current source snapshot already under review: `71afe476751deac24adabd1adb575fd2337b6e0a`.

A compare between those revisions shows that the critical files discussed below did not change: `FEXCore/Source/Interface/Core/Core.cpp`, `FEXCore/Source/Interface/Core/JIT/JIT.cpp`, `FEXCore/Source/Interface/Core/LookupCache.h`, `Source/Tools/LinuxEmulation/Thunks.cpp`, the Linux unmap/VMA tracking files, and the Vulkan/GL/CUDA guest wrappers. The refined mechanism therefore applies to both snapshots at source level.

## Main refinement

The strongest source explanation is now narrower than “CustomIR survives unload.”

There are two addresses with different invalidation ownership:

- `H`: native host function pointer returned by Vulkan/GL/CUDA and exposed to the guest as a synthetic guest-callable address;
- `T`: guest `CallHostFunction<signature>` invoker compiled into an unloadable guest thunk DSO.

FEX registers:

```text
H -> T
```

through `AddThunkTrampolineIRHandler(H, T)`.

The generated CustomIR block for `H` stores `H` in guest R11 and exits to constant guest destination `T`.

The important detail is that a CustomIR block returns `NeedsAddGuestCodeRanges = false`. Its lookup mapping is therefore inserted with an empty `CodePages` dependency list.

Ordinary decoded code at `T` is different: it is associated with the guest pages containing `T`.

## What guest unmap actually cleans up

`GuestToHostMap::Erase(Address)` does two useful things:

1. it removes the compiled block mapping for `Address`;
2. it walks every inbound JIT link registered for that guest destination and invokes its delinker.

Therefore, when `libvulkan-guest.so` is unmapped and the target page containing `T` is invalidated, ordinary FEX invalidation can remove the compiled block at `T` and delink callers that had been directly patched to its host code.

That cleanup does **not** discover `H`, because `H`'s CustomIR block has no guest-page entries in `CodePages` and the unmap range is the guest-thunk range around `T`, not the native-PFN value `H`.

So the surviving object is specifically:

```text
compiled synthetic block at H
    -> ExitFunction link record with GuestRIP = T
```

`ExitFunctionLinkData` stores `HostCode`, `GuestRIP`, and `CallerOffset`. Delinking patches the jump site back to the linker path; it does not replace `GuestRIP`.

## Refined post-unload causal path

A plausible source-complete sequence is:

```text
1. vkGetInstanceProcAddr / vkGetDeviceProcAddr returns native PFN H
2. guest wrapper selects CallHostFunction invoker T
3. LinkAddressToFunction(H, T)
4. first call to H compiles/caches CustomIR block H
5. H exits to T; normal thunk code at T may also be compiled
6. guest dlclose begins final unload of libvulkan-guest.so
7. guest munmap removes pages containing T
8. ordinary range invalidation erases T and delinks inbound H -> T direct link
9. synthetic block H remains cached because it has no CodePages dependency on T
10. later guest call to H finds surviving H block
11. H block stores H in R11 and reaches its now-delinked ExitFunction record
12. ExitFunctionLink uses the retained GuestRIP = T
13. lookup/compile is attempted for T after T's mapping is gone
14. guest instruction-fetch page fault is reported in the old thunk range
```

This sequence fits the retained runtime receipt:

- terminal x86 page fault is an instruction fetch;
- saved guest RIP is in the old `libvulkan-guest.so` image and resolves inside a generated `CallHostFunction<...>` body;
- that guest range is no longer mapped;
- pinning the Vulkan guest thunk changes exit 139 to exit 0;
- a bogus preload does not;
- llvmpipe reproduces the same late failure.

This refinement means a retained **post-unload CustomIR handler lookup is not required** to explain the crash. The already-compiled `H` block is enough. The handler itself is still stale state and must also be retired so a cache miss cannot regenerate the bridge.

## Why both registry retirement and exact H eviction are required

Two stale holders exist:

### Registration holder

`CustomIRHandlers[H]` retains `T` in both the handler closure and `Data`.

If compiled `H` is evicted but the registration remains, a later call to `H` can compile a fresh bridge to the same dead `T`.

### Compiled bridge holder

The compiled `H` block retains the exit destination independently of the registry after compilation.

If the registry is erased but the compiled `H` lookup entry remains, guest execution can still enter that already-generated bridge.

Therefore the narrow retirement primitive needs to do both:

```text
retire CustomIR registration H
exactly evict/delink compiled synthetic entry H
```

The target-range invalidator alone cannot supply the second operation because `H` is intentionally absent from the target page's reverse index.

## Correction: physical unmap ordering

A prior checkpoint described `GuestMunmap` as providing a pre-physical-unmap cleanup point through `TrackMunmap`.

Exact FEX-2608 source shows a stricter ordering:

```text
hold VMATracking.Mutex
    -> host/Get32BitAllocator munmap
    -> TrackMunmap
    -> inspect PendingResourceDeletion
release VMATracking.Mutex
    -> ordinary code-range invalidation
```

The VMA metadata still exists briefly after the host pages have been removed, because `TrackMunmap` has not run yet, but that is already too late for the invariant:

> A bridge that can reach guest target T must become unreachable before T becomes non-executable.

A correct target-owner cleanup therefore needs to identify and revoke affected bridge state **before the real munmap call**, while the VMA lock still allows the target address to be resolved to its live mapped resource.

## MappedResource lifetime implication

`VMATracking::DeleteVMARange` removes a final `MappedResource` immediately unless that resource owns mapped code-cache data. Only the mapped-code-cache case is moved into `PendingResourceDeletions` for delayed destruction.

Therefore a raw `MappedResource*` is useful as an ephemeral live-mapping lookup key but is not a durable bridge owner token.

For a generic load-generation design, a safer model is:

```text
live MappedResource* -> monotonically assigned guest-load generation id
```

The pointer can be used while the VMA exists to resolve the generation; bridge claims retain the generation id rather than the pointer. Final unmap revokes the generation before deleting the mapping-side object.

MRID alone is insufficient because a later mapping of the same backing file can reuse the same MRID. Base address alone is also insufficient because a later load can reuse the same virtual address.

## In-flight execution remains a separate problem

Exact lookup-cache removal closes future lookups, but source inspection does not provide a general execution drain.

`ExitFunctionLink` takes the code-invalidation mutex in shared mode while it looks up a block, then releases that guard before returning the selected host-code pointer. A concurrent invalidator can therefore run after another thread has already selected a bridge.

For this specific bridge class, that gives the race:

```text
thread A: select compiled H
thread B: retire H, invalidate H, unmap T
thread A: execute already-selected H -> T
```

A single-threaded `vulkaninfo` repair can demonstrate the immediate owner, but it does not prove the multi-thread lifetime rule.

Longer-term designs worth comparing:

1. **Quiesce affected bridge execution before unmap.** Precise but potentially expensive and difficult inside a guest memory syscall.
2. **Stable revocable bridge state.** Compiled H consults process-lived state whose active target/generation can be atomically revoked before unmap. A thread that already selected H still observes the tombstone before using T.
3. **Process-lifetime guest invoker code.** Move `CallHostFunction` entrypoints out of unloadable guest DSOs. Larger thunk ABI/generator change, but it removes this raw-code lifetime dependency.
4. **Pin guest thunk DSOs.** Proven runtime control, but it converts the ownership bug into process-lifetime retention and does not address the generic model.

The stable-revocable-state design remains the strongest generic direction because it also supports reload promotion and avoids requiring a global stop for every final thunk unmap.

## Existing signature identity can support safe promotion

FEX's thunk generator already derives a stable SHA-256 identity from each runtime host-function-pointer signature (`fexcallback_` plus the canonical function-pointer signature) and deduplicates matching signatures.

Current `LinkAddressToFunction` only transports:

```text
{ native PFN H, guest invoker T }
```

It does not transport that stable signature identity.

A versioned internal registration carrying the already-generated signature identity would let a process-lived owner registry distinguish:

- compatible dormant owners that may be promoted after active-owner unload;
- incompatible native-PFN collisions that must remain rejected/diagnostic.

The narrow FEX-2608 causality probe does not require promotion metadata. It only needs target-owner retirement plus exact H eviction before physical unmap.

## Generic scope beyond Vulkan

The same dynamic host-function-pointer bridge is present in:

- Vulkan: `vkGetDeviceProcAddr` / `vkGetInstanceProcAddr`;
- OpenGL: `glXGetProcAddress` / `glXGetProcAddressARB`;
- CUDA: `cuGetProcAddress_v2`.

Each family obtains a native host function pointer and calls `LinkAddressToFunction` with a guest invoker from its unloadable guest thunk image.

The executed crash remains Vulkan-specific evidence. The source bug class is generic to this bridge mechanism.

## Callback cache remains adjacent, not merged into the immediate cause

`GuestcallToHostTrampoline` is still a second lifetime-sensitive cache. Its trampoline records embed raw `GuestUnpacker` and `GuestTarget` addresses that may live in guest DSOs.

That deserves the same load-generation/revocation audit, but the retained teardown RIP near `CallHostFunction<...>` aligns more directly with the dynamic-PFN `H -> T` path described above.

## Best next runtime discriminator

For the retained M5 environment, the most economical receipt remains:

```text
REGISTER H -> T
COMPILE/CACHE H
UNMAP range containing T
later call/dispatch at H
R11 = H at the terminal guest fault
saved guest RIP in old target T range
```

The new source refinement lowers the burden on the fourth item: a post-unload CustomIR **handler** hit is no longer required. A surviving compiled lookup entry for H is sufficient.

A diagnostic retirement experiment should happen before physical unmap and should remove both the `CustomIRHandlers[H]` record and the compiled synthetic H entry. If that changes the real `vulkaninfo` teardown from exit 139 to exit 0 while preserving ordinary guest library unload, it would identify the immediate FEX holder more tightly than the existing pinned-thunk control.

## Exact uncertainty after this pass

High confidence from source:

- H and T have separate invalidation ownership;
- CustomIR H has no target-page CodePages dependency;
- T invalidation can delink inbound exits without deleting H;
- the H exit-link record retains guest destination T;
- registry-only and target-range-only cleanup are incomplete;
- cleanup must begin before physical target unmap;
- GL and CUDA share the same source-level bridge class;
- the critical path is unchanged between the executed FEX-2608 and reviewed current-main snapshots.

Still unproved in the retained real crash:

- the exact native PFN H used by the final teardown transfer;
- R11 at the terminal guest fault;
- whether another guest thread was concurrently capable of selecting H during final unload;
- whether a narrow pre-unmap H retirement changes the real `vulkaninfo` result to exit 0.

These are runtime proof gaps, not source-map gaps.
