# Runtime checkpoint — compiled CustomIR cache holder isolated

## Real-FEX lifetime result

Hosted ARM64 run `31736707315` at FEX `71afe476751deac24adabd1adb575fd2337b6e0a` executes the retained full thunk pair and confirms both stale-reference directions after unloading a guest thunk DSO and forcing its reload to a different guest VA:

- retained `H -> T` / `LinkAddressToFunction` path faults with SIGSEGV while the native host address `H` remains stable;
- retained host->guest callback trampoline faults after its embedded guest target/unpacker generation disappears;
- fresh current-generation direct host calls and fresh current-generation callbacks succeed;
- pinning the guest DSO keeps the retained paths executable.

The forced-different case also shows that simply registering the same stable native `H` again after reload does not repair the old path.

## CustomIR registration and cache layers

Instrumented run `31739983487` proves the duplicate registration arm is reached. For `H=0x7ffff7d80860`, generation 1 target `T=0x7ffff7da21b0` collides with generation 2 target `T=0x7ffff7d781b0`. `RemoveCustomIREntrypoint(H)` erases the old handler, ordinary range invalidation completes, and re-add inserts the new target, yet the post-rebind call still faults.

A second diagnostic, run `31741352482`, adds an exact shared `GuestToHostMap` erase that bypasses page reverse indexes. The trace reports `handler=1 shared_exact=1`, followed by a successful handler re-add to the new target. The post-rebind call still faults.

Source inspection explains the remaining holder:

1. CustomIR compilation reports `NeedsAddGuestCodeRanges = false`, so its native-key entrypoint `H` receives no `CodePages` association.
2. Normal range invalidation depends on `CodePages` / `CachedCodePages`, so it cannot find this CustomIR block by page.
3. Compile-time `AddBlockMapping` seeds the compiled entry directly into the current thread's L1 lookup cache.
4. `FindBlock` consults L1 first, then L2, then shared L3.
5. Exact shared L3 erasure therefore leaves a guaranteed stale L1 entry able to dispatch the old compiled `H -> old T` block.

This tightens the immediate H->T defect from “stale CustomIR registration” to a concrete invalidation mismatch: `RemoveCustomIREntrypoint` uses page/range invalidation for a class of entrypoint that CustomIR deliberately excludes from page tracking.

A thunk retirement primitive needs to erase the handler definition, directly erase the shared compiled H entry/direct links, directly clear H from every thread's L1/L2, and do all of that before the guest target generation is allowed to unmap. The full design still needs execution lifetime/quiescence for the selected-bridge vs unload race.

## Pre-unmap owner retirement: causal runtime proof

Hosted ARM64 run `31744407289` (job `94595330634`, artifact `9198508307`) moves the retirement trigger to the legal lifetime boundary and demonstrates recovery after a moved reload.

The diagnostic records every `LinkAddressToGuestFunction` pair as `(H,T)`. `GuestMunmap` checks the outgoing range before physical unmap; matching targets are removed from the owner index and their H entrypoints are retired. The retirement implementation uses existing CustomIR handler removal followed by `ClearCodeCache(Thread, false)`. That broad cache clear is intentionally diagnostic: it supplies the missing hot-cache eviction without claiming the final granularity or multithread design.

The trace records the generation transition directly:

```text
DIAG_LINK_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_PREUNMAP_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_RETIRE_H H=0x7ffff7d80860 thread=0xff81f0c01000
DIAG_LINK_OWNER H=0x7ffff7d80860 T=0x7ffff7d781b0
```

After the generation-1 guest DSO is forced to reload at a different VA while native H remains stable:

- the retained generation-1 H path invoked before a new guest owner is published faults, as an already-retired bridge has no valid current T;
- the retained generation-1 host->guest callback still faults;
- fresh current-generation direct calls and fresh callbacks succeed;
- after generation 2 registers the same native H against its new T, `Link after re-register` returns the expected value and exits 0;
- the original callback remains dead while the current-generation callback succeeds.

This establishes the immediate H->T causal chain end to end: FEX publishes a hidden H-to-guest-T dependency, the guest target's load generation is detected before it disappears, retiring the FEX-owned bridge/cache state allows the same stable H to bind safely to the new generation, and the unrelated callback path remains broken as an orthogonal control.

Current `GuestMunmap` ordering performs physical `munmap` before `TrackMunmap` and ordinary range invalidation. A product retirement hook therefore must execute before physical unmap while the outgoing target/load-generation identity remains available. The fork's current `main` retains the same ordering.

For the product design, `MappedResource` remains the strongest existing load-generation identity: the same file/inode can reload at another base while native H stays stable. The diagnostic's simple H-to-T map is sufficient for this one-owner causality test; the real owner model needs aliases/multiple logical owners, partial-unmap semantics, failed-`munmap` rollback or equivalent transaction ordering, and retirement only when the dependency's generation truly ceases to be executable.

The broad cache flush should be replaced by one coherent exact-entry operation that removes the handler, evicts the compiled H entry/direct links from shared lookup state, clears H from every emulation thread's L1/L2, and participates in an execution-lifetime rule for the selected-H-to-T versus unload race.

## Separate callback lifetime class

The host->guest callback failure remains independent. Host trampoline memory is process-lifetime and embeds raw `GuestUnpacker` / `GuestTarget`. Vulkan's X11 setup can leave a host-retained trampoline whose guest X11 target still exists while the unpacker compiled into `libvulkan-guest.so` has vanished. Map erasure alone cannot revoke a host pointer already published to a native library; that path needs stable/revocable indirection or equivalent rebinding plus execution lifetime.

The pre-unmap H->T diagnostic strengthens this separation: it repairs generation-2 H rebinding while the original retained callback continues to SIGSEGV and the new callback succeeds.

## Adjacent independent Vulkan allocator bug

Run `31737446041` establishes another cross-ISA callback defect outside proc-address routing and unload lifetime. A generated `vkCreateBuffer` call with `pAllocator=nullptr` completes successfully. The same call with a real x86 `VkAllocationCallbacks` reaches `BEFORE_CREATE_BUFFER` and dies `132/SIGILL` before returning. FEX currently marks `VkAllocationCallbacks` opaque with a TODO for function-pointer support, so generated functions pass guest callback addresses through to the ARM64 host driver. Existing handwritten Vulkan wrappers already suppress allocator callbacks for a subset of APIs.

This should be tracked separately from the unload diagnosis; `vkCreateBuffer` is a representative reproducer for a broad `VkAllocationCallbacks*` API family.

All source edits described here are diagnostic work on owned surfaces. No upstream FEX interaction occurred.
