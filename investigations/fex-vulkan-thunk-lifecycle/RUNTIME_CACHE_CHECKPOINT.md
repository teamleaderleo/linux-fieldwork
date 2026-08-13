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

## Ownership boundary

The next diagnostic should stop relying on a later duplicate registration as the retirement trigger. `LinkAddressToGuestFunction` already sees every `(H,T)` pair. A reverse index can associate H with the guest target/load generation. Before physical `munmap`, registrations whose target belongs to the outgoing mapping should be retired through the exact-entry primitive; a later generation can then register the same stable H against its new T.

For the product design, `MappedResource` is the stronger generation identity than filename/inode alone because the same DSO may reload at a different base while preserving the same native H.

## Separate callback lifetime class

The host->guest callback failure remains independent. Host trampoline memory is process-lifetime and embeds raw `GuestUnpacker` / `GuestTarget`. Vulkan's X11 setup can leave a host-retained trampoline whose guest X11 target still exists while the unpacker compiled into `libvulkan-guest.so` has vanished. Map erasure alone cannot revoke a host pointer already published to a native library; that path needs stable/revocable indirection or equivalent rebinding plus execution lifetime.

## Adjacent independent Vulkan allocator bug

Run `31737446041` establishes another cross-ISA callback defect outside proc-address routing and unload lifetime. A generated `vkCreateBuffer` call with `pAllocator=nullptr` completes successfully. The same call with a real x86 `VkAllocationCallbacks` reaches `BEFORE_CREATE_BUFFER` and dies `132/SIGILL` before returning. FEX currently marks `VkAllocationCallbacks` opaque with a TODO for function-pointer support, so generated functions pass guest callback addresses through to the ARM64 host driver. Existing handwritten Vulkan wrappers already suppress allocator callbacks for a subset of APIs.

This should be tracked separately from the unload diagnosis; `vkCreateBuffer` is a representative reproducer for a broad `VkAllocationCallbacks*` API family.

All source edits described here are diagnostic work on owned surfaces. No upstream FEX interaction occurred.
