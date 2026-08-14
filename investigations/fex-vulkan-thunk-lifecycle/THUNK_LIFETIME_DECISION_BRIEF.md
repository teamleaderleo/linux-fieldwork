# Thunk lifetime decision brief

Date: 2026-08-14

Audience: project discussion before a patch/RFC is taken to FEX maintainers

## The short version

The recurring bug class is an ownership mismatch.

FEX and native libraries can retain guest executable addresses after the guest wrapper DSO that contains those addresses has closed. That creates stale executable references across dynamic PFN lookup, persistent callbacks, reloads, and teardown.

The most useful rule is:

> Escaped guest executable code needs the lifetime of the thing that retains it.

The investigation now supports two practical responses:

- **near term:** selectively mark lifetime-sensitive guest wrappers NODELETE;
- **long term:** move immutable generated signature bridges into a small process-resident private guest runtime while keeping public wrappers unloadable.

Actual callback targets and stateful helpers remain owner-specific and need explicit lifetime/revocation handling.

## What is already demonstrated

### Selective NODELETE is a strong containment patch

The candidate can be expressed as an opt-in on the guest-library CMake helper and applied to Vulkan, GL, CUDA, and Wayland.

The known advantages are:

- tiny source diff;
- no core/JIT changes;
- no runtime loader bookkeeping;
- both bitnesses use the same build-time contract;
- fresh Vulkan proc lookup after close keeps working;
- real Vulkan/X11 callback behavior survives;
- measured incremental Vulkan residency versus ordinary close is about 304 KiB.

The main semantic cost is that selected wrapper images remain resident until process exit.

### A resident bridge preserves real wrapper unload

This has moved beyond a toy prototype.

Three distinct Vulkan PFN signatures remain callable after the guest Vulkan wrapper reaches zero mappings and after a forced reload at a different base.

A separate Vulkan/X11 run keeps both directions alive with only bridge code resident:

```text
native Vulkan PFN
    -> resident guest CallHostFunction adapter
    -> host Vulkan thunk
    -> host callback trampoline
    -> resident guest CallbackUnpack
    -> still-owned guest X11 target
```

The Vulkan wrapper is physically absent during the second call.

That demonstrates a real ownership split: generated signature bridge code can outlive the wrapper without pinning the whole wrapper.

### Persistent callback targets remain a separate class

The DRM `drmSetServerInfo` lane has a native library retaining a guest callback. Its candidate converts the callback into an FEX host trampoline and retains the host-side server-info object. That candidate succeeds where the recorded pristine reference exits 132.

This reinforces the distinction:

- stable unpacker/adapter code can be process-lived;
- actual guest targets still follow their owner and can require explicit unregister, pinning, generation tracking, or revocation.

### Core-wide reclamation is possible but expensive

The deeper experiments show that physical reclamation is a distributed protocol:

- registry changes alone do not clear every translated/cache path;
- every thread must observe invalidation;
- calls already committed to old code need quiescence;
- address reuse creates ABA hazards;
- failed unmaps need rollback semantics;
- one native host address can have more than one live guest owner.

That capability may eventually be needed for real unloadable targets. It is excessive as the first answer for immutable signature adapters that can simply live under a longer-lived owner.

## What the other lanes are telling us

The parallel work is converging into four buckets.

### 1. Ownership and bridge placement

Vulkan split-runtime work and the independent DRM persistent-callback work both point toward FEX-owned or host-owned bridge objects for references whose useful lifetime exceeds a wrapper call.

### 2. Revocation, rebinding, and address reuse

The rebind/revoked-address/VMA lanes are exploring what happens when code truly must disappear and a host address or guest address can be reused. Their main contribution is showing why generation identity and invalidation become necessary once physical reclamation is allowed.

### 3. In-flight callback races

The callback-concurrency and signal/race lanes are probing calls that are already executing while teardown begins. A revoked future entry does not stop an already-entered callback, so quiescence is a separate requirement.

### 4. API-specific semantic bridges

Native-first XCB and Vulkan allocator/custom-callback work are asking whether selected crossings can be replaced with API-aware host handling. These can simplify individual paths, while their semantics are too API-specific to serve as the universal lifetime policy.

## Recommended position to take into maintainer discussion

I would present the argument in this order:

1. **State the invariant first.** FEX currently allows executable guest addresses to escape wrapper lifetime.
2. **Show two independent examples.** Vulkan dynamic PFNs and persistent callback unpackers demonstrate both directions.
3. **Show the smallest proven correction.** Selective NODELETE removes the confirmed executable-lifetime gap with a tiny patch and modest measured residency.
4. **Show why this can evolve cleanly.** The resident bridge proves the whole wrapper does not need process lifetime; immutable signature code can move to a better owner later.
5. **Keep actual callback targets separate.** DRM and race experiments demonstrate where revocation/generation work still belongs.
6. **Avoid starting with a core JIT rewrite.** The confirmed immutable-adapter class no longer needs that complexity once ownership is corrected.

## Questions worth asking maintainers

The conversation becomes much easier if it asks for decisions rather than approval of one giant design.

- Are maintainers comfortable treating selected generated guest wrappers as process-lived for an immediate correctness patch?
- Do they prefer an explicit per-wrapper NODELETE annotation or a common policy for all shared guest thunks?
- Does a private generated bridge runtime fit the intended thunk architecture?
- Would they prefer one bridge per thunk family first, or one deduplicated process bridge per bitness?
- How important is disposable `dlmopen()` namespace behavior for FEX's supported workloads?
- Where should target-owner/revocation metadata live for persistent callbacks?
- Which existing thunkgen metadata could carry an explicit lifetime classification?

## Suggested sequencing

### Patch 1: containment

Selective NODELETE with tests and a comment describing exported executable thunk lifetime.

### RFC / prototype 2: process-resident generated bridge

Move Vulkan's proven signature adapters/unpackers into a generated private dependency. Preserve physical wrapper unload and rerun the moved-generation/X11 tests.

### Follow-up 3: callback target ownership

Use DRM and callback-race findings to design explicit target owner/revocation semantics.

### Follow-up 4: broader deduplication

Prove equal canonical signatures can share adapters across unrelated thunk libraries, then consider one bridge runtime per bitness.

## Current recommendation

Bring **selective NODELETE as the patch** and **the resident bridge as the architectural direction**.

That pairing has a useful political property in review: the patch stays small and understandable, while the RFC makes clear that process-lifetime whole wrappers are a containment choice rather than the final ownership model.
