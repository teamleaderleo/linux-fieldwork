# RFC: Lifetime ownership for executable guest thunk bridges

Status: Draft for maintainer discussion

Date: 2026-08-14

## Decision requested

Choose an explicit lifetime policy for guest executable addresses that escape a thunk call and remain reachable from FEX-owned or host-owned state.

The immediate recommendation is:

1. use selective `DF_1_NODELETE` for currently identified lifetime-sensitive guest wrappers as a small containment patch;
2. develop a process-resident generated guest bridge runtime as the preferred long-term home for immutable signature adapters and callback unpackers;
3. reserve generation-aware revocation/reclamation for stateful objects and real guest callback targets whose owning DSO can unload.

This RFC separates the common ownership problem from those policy choices so reviewers can agree on the invariant even if they prefer a different implementation.

## Problem statement

FEX thunking can export guest executable addresses beyond the dynamic extent of the thunk call that produced them.

Two confirmed forms are:

### Host PFN to guest adapter

Dynamic API lookup can produce:

```text
native host function pointer H
    -> FEX LinkAddressToFunction(H, T)
    -> guest CallHostFunction<signature> adapter T
```

`T` is currently instantiated in a guest wrapper DSO such as `libvulkan-guest.so`. FEX may retain routing for `H` after the guest loader has closed and unmapped that wrapper.

### Host trampoline to guest callback unpacker

A host callback trampoline can retain:

```text
{ GuestUnpacker, GuestTarget }
```

For Vulkan/X11, `GuestUnpacker` is a generated `CallbackUnpack<signature>::Unpack` currently emitted inside `libvulkan-guest.so`, while `GuestTarget` is an ordinary guest X11 function.

The host-side object can outlive the Vulkan guest wrapper that supplied the unpacker address.

## Core invariant

> Any guest executable address that becomes reachable from FEX-owned or host-owned state beyond the initiating thunk call must remain executable for the lifetime of every such reference, or every reference must be revoked before the backing executable mapping disappears.

This applies independently to adapter code, callback unpackers, actual callback targets, and stateful helper code.

## Why this is an ownership problem

The current placement of generated bridge code inside a wrapper DSO gives it wrapper-image lifetime by accident. Its semantic identity can be broader.

Thunkgen callback markers are keyed by canonical function-pointer signature rather than wrapper-library name. `CallHostFunction<signature>` and `CallbackUnpack<signature>` are also signature-driven templates. For immutable cases, wrapper generation is therefore a poor lifetime owner.

Stateful helpers are different. Per-instance/device data, custom repacking, allocator behavior, actual callback targets, and mutable wrapper state can carry a real owner relationship.

The implementation should distinguish those categories.

## Experimental evidence

### Whole-wrapper residency proves the lifetime diagnosis

`DF_1_NODELETE` preserves guest wrapper code across `dlclose()` and allows retained dynamic PFNs and callback paths to continue executing.

Loader contract probes found the expected glibc behavior:

- constructors run once;
- destructors are deferred to process exit;
- `RTLD_NOLOAD` continues to find the resident object;
- later reopen can promote `RTLD_LOCAL` to `RTLD_GLOBAL`;
- runtime promotion with `RTLD_NOLOAD | RTLD_NODELETE` works on glibc 2.31, 2.35, and current glibc.

The practical Vulkan residency delta measured in a real FEX guest process is 311,296 bytes (304 KiB) versus ordinary unload. Most C++/X11 dependencies already remain mapped in the ordinary-close case.

A real Ubuntu amd64 `vulkaninfo --summary` run under FEX/Lavapipe passes with the NODELETE candidate. The hosted normal case also passes, so that workload is compatibility coverage rather than a causal discriminator.

### Resident bridge proves whole-wrapper residency is stronger than necessary

A separate `DF_1_NODELETE` guest bridge DSO was used while leaving `libvulkan-guest.so` fully unloadable.

One-signature, three-signature, moved-reload, and bidirectional Vulkan/X11 experiments all support the same ownership split:

```text
process lifetime:
    immutable generated bridge executable code

wrapper lifetime:
    libvulkan-guest.so state and loader lifecycle

callback-target owner lifetime:
    actual guest callback target functions
```

In the three-signature experiment, three distinct Vulkan PFNs remained callable with zero guest Vulkan-wrapper mappings and through a forced wrapper reload at a new base.

In the real Vulkan/X11 experiment, the wrapper reached zero mappings, then a retained native Vulkan Xlib PFN re-entered guest X11 through resident callback unpackers and succeeded.

### Persistent DRM callback demonstrates the remaining target-lifetime problem

An independent DRM experiment found a persistent callback path through `drmSetServerInfo`. A candidate that converts the guest callback to an FEX host trampoline and retains a host-side copy of the server-info object succeeds where the recorded pristine reference exits 132.

This is a useful distinction: resident unpacker code can remove one executable-lifetime hazard, while the actual guest callback target still needs an owner-aware policy.

### Full reclamation has distributed costs

Generic experiments around physical unload show that safe reclamation requires more than removing an `H -> T` map entry:

- translated code and lookup caches can survive registry changes;
- every FEX thread must observe invalidation;
- execution already committed to an old target needs quiescence or an equivalent protocol;
- guest address reuse creates ABA hazards;
- failed unmap operations require prepare/commit/abort behavior;
- one native `H` can have multiple simultaneous guest owner claims.

Those costs remain justified for objects that genuinely need reclaimable lifetime. Immutable signature adapters can avoid that protocol if they move to a longer-lived owner.

## Candidate policies

| Policy | Correctness coverage | Loader semantics | Implementation cost | Main concern |
|---|---|---|---|---|
| Selective static NODELETE | Covers all currently identified lifetime-sensitive wrappers | Pins selected wrapper images | Very small | Wrapper remains resident through process lifetime |
| Global static NODELETE | Broadest containment against unknown future escaping addresses | Pins every shared guest thunk | Minimal | Applies lifetime policy to thunks that do not need it |
| Base-namespace runtime promotion | Pins ordinary application copy while allowing disposable namespaces | glibc-specific loader work | Moderate | Guest-side self-discovery and loader compatibility |
| Process-resident generated bridge | Keeps wrapper unload semantics and stabilizes immutable bridge code | Adds one private resident dependency | Moderate/high | Generator, packaging, namespace, and classification work |
| Full generation-aware reclamation | Can preserve physical reclamation for every owned object | Preserves ordinary loader semantics | High | Thread quiescence, cache invalidation, ABA, rollback, multi-owner cases |
| Native-first routing | Can eliminate selected guest bridge crossings | API-specific | Variable | Does not generalize to every thunk ABI or callback pattern |

## Near-term proposal: selective static NODELETE

Add an explicit `NODELETE` option to the guest-library CMake helper and apply it to the currently demonstrated lifetime-sensitive wrappers:

- Vulkan;
- GL;
- CUDA;
- Wayland client.

Reasons to prefer the selective form for an immediate patch:

- tiny diff;
- no runtime loader code;
- no JIT/cache ownership changes;
- both guest bitnesses can use the same build-time policy;
- the call-site annotation documents why each wrapper has process lifetime;
- simple wrappers retain their current loader behavior.

The policy should be described as containment of exported executable thunk addresses, rather than as a Vulkan-specific workaround.

### Known caveat: loader namespaces

`DF_1_NODELETE` is scoped to a loader namespace. A synthetic glibc test can exhaust disposable `dlmopen(LM_ID_NEWLM)` namespaces when each contains a NODELETE copy. In the real FEX/Vulkan namespace workload tested so far, guest glibc static TLS exhausts first, at roughly the same point for ordinary and NODELETE wrappers.

This deserves explicit documentation even though current FEX behavior already limits that workload.

## Long-term proposal: process-resident generated guest bridge runtime

Move immutable generated executable bridges out of unloadable wrappers and into a private process-lived guest runtime.

Candidate contents:

- signature-specialized callback thunk markers;
- `CallHostFunction<signature>` adapters;
- `CallbackUnpack<signature>::Unpack` adapters;
- a generated lookup surface for wrappers to obtain those stable addresses.

Candidate non-contents:

- per-instance/device state;
- actual callback targets;
- allocator/custom-repacking state with wrapper semantics;
- wrapper constructors/destructors;
- mutable API-specific tables unless proven process-owned.

FEX's thunk database already supports dependencies and recursively overlays them from the private GuestThunks path, providing a plausible packaging route for a private bridge DSO.

## Relationship between the two proposals

Selective NODELETE and a resident bridge are compatible migration stages.

NODELETE provides a small corrective patch with a narrow review surface. The bridge runtime can then move stable executable adapters out of those wrappers one family at a time. Once a wrapper has no process-lived executable references left, its NODELETE annotation can be removed.

This avoids making the larger generator change a prerequisite for fixing the current lifetime bug.

## What still requires explicit ownership or revocation

A resident signature bridge does not extend the lifetime of arbitrary guest callback targets. If native/FEX state retains a callback into a guest library that later unloads, FEX still needs one of:

- explicit unregister/revocation tied to the owner;
- owner claims and generation identity;
- a stable indirection object that can reject stale calls;
- an API-specific lifetime hook;
- a deliberate policy that pins the target owner.

The DRM `drmSetServerInfo` work is a current example of this separate class.

In-flight callback teardown also remains its own problem: revocation prevents future entry, while execution already inside an old target requires quiescence or API-level guarantees.

## Rejected first move: core-wide JIT retirement

A core-wide reclamation protocol remains a valid end-state capability, especially for truly unloadable callback targets. It is a poor first patch for immutable thunk signature adapters because the bridge experiments show those adapters can simply have process lifetime.

Taking on thread-wide invalidation, execution quiescence, ownership generations, and rollback before exhausting the simpler ownership correction would increase risk with little benefit for the confirmed adapter class.

## Rollout and tests

### Immediate patch gates

- build all 64-bit guest thunks;
- build representative 32-bit thunk paths, including Wayland;
- assert NODELETE appears only on selected wrappers;
- retained Vulkan PFN after close;
- fresh proc lookup after close to exercise wrapper static state;
- real Vulkan/X11 callback after close;
- existing `glxinfo` and `vulkaninfo` thunk functional tests;
- loader contract checks for constructor/destructor and reopen behavior.

### Bridge-runtime gates

- several unrelated signatures in one wrapper;
- guest-to-host and host-to-guest directions;
- forced different-base reload;
- same-signature reuse across two different thunk libraries;
- per-namespace behavior;
- 32-bit ABI path;
- code-size/residency measurement across a realistic signature set;
- audit for TLS/static-data/relocation dependencies;
- explicit tests showing actual callback targets remain owner-governed.

## Open questions

1. Should the bridge runtime be one process-wide DSO per bitness, or a small private DSO per thunk family?
2. Can equal signature hashes from unrelated libraries share one adapter in every supported ABI case?
3. How should `dlmopen` namespaces interact with a process-lived bridge?
4. Which generated/custom helpers close over wrapper-local state and therefore stay wrapper-owned?
5. Should callback-target ownership become a first-class thunkgen annotation?
6. Can FEX expose a stable indirection object for callbacks whose target owners may unload?
7. Which parts of the DRM persistent-callback work generalize into common thunk helpers?

## Maintainer-facing summary

The bug class is an ownership mismatch: FEX or native state can retain guest executable addresses longer than the wrapper DSO that currently contains them.

The smallest correction is to keep the affected wrapper resident. The cleaner long-term correction for immutable generated signature bridges is to give that code an owner whose lifetime already matches its consumers. Stateful helpers and real callback targets continue to use explicit owner-aware lifetime rules.
