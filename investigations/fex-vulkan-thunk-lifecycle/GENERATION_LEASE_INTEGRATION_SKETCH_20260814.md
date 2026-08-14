# Generation + execution-lease integration sketch — 2026-08-14

## Status

This is an implementation sketch derived from source inspection and executable experiments. It is not an upstream-ready FEX patch and it does not claim the exact historical `vulkaninfo` final branch has been directly captured.

The design is constrained by four demonstrated facts:

1. FEX dynamic thunk bridges can compile a native-address key H into code that embeds guest thunk target T as a constant.
2. unload/reload can reuse the same raw guest executable addresses, so raw-address identity is vulnerable to ABA;
3. removing shared H→T registrations and invalidating all thread caches is insufficient after another thread has already selected T;
4. a generation token + revocation + active execution lease passes a deterministic select/retire/reload model where raw-address-only state fails.

## 1. Give each mapped load instance a monotonic generation ID

`VMATracking::MappedResource` already represents the right semantic object for a load instance:

- the same backing file may have multiple `MappedResource`s at different bases;
- re-mapping an ELF header can create a fresh `MappedResource` even when MRID is the same;
- VMAs refer back to their current `MappedResource`.

Add an integer such as:

```cpp
uint64_t Generation;
```

and assign it centrally in `VMATracking::InsertMappedResource` from a monotonic counter owned by `VMATracking` or the enclosing syscall/process state.

Do **not** use MRID as load identity: the same inode/backing storage may be unloaded and reloaded as a new lifetime.

Do **not** use `MappedResource*` as durable bridge identity: the resource object is destroyed after its final VMA disappears and allocator reuse could create another ABA class.

A bridge stores the integer generation ID, while VMA tracking remains the authority that maps a currently valid guest address to its current generation.

## 2. Add an internal address→generation resolver

The existing `FindVMAEntry(GuestAddr)` already returns a VMA whose `Resource` identifies the current load instance.

Add an internal helper on the syscall/VMA side, conceptually:

```cpp
std::optional<uint64_t> LookupGuestLoadGeneration(
    FEXCore::Core::InternalThreadState* Thread,
    uintptr_t GuestAddress);
```

It should take the VMA tracking shared lock, resolve `GuestAddress`, and return the current `MappedResource::Generation` when the address belongs to a tracked resource.

This is deliberately separate from `QueryGuestExecutableRange`, which answers range/protection questions but not load-instance identity.

## 3. Stable host-owned bridge state must outlive the VMA object

Introduce a stable bridge object for FEX-created executable crossings. Conceptually:

```cpp
struct ThunkBridgeState {
  uint64_t BridgeID;
  vector<uint64_t> Dependencies; // load generations
  mutex Mutex;
  condition_variable CV;
  bool Draining;
  uint32_t Active;
  ... direction-specific payload ...
};
```

The bridge state is not stored inside `MappedResource`; it must survive resource retirement long enough for escaped/cached host-visible references to observe `Draining` and reject instead of dereferencing freed VMA state.

For a dynamic PFN bridge, dependencies normally contain the generation owning T.

For a host→guest callback bridge there can be at least two independent guest generations:

- the thunk-owned `GuestUnpacker` generation;
- the application/other-DSO `GuestTarget` generation.

A single bridge-level active count is simpler than trying to atomically acquire two separate generation leases. Retirement of *either* dependency marks the whole bridge draining.

## 4. Callback trampoline private ABI can carry the stable token directly

FEX already copies private instance data next to each generated host trampoline. Current state contains raw `GuestUnpacker` and `GuestTarget` addresses.

Extend that private instance data with a pointer/token to stable `ThunkBridgeState`.

The important property is that the token is copied/selected **with** the old trampoline generation. A later same-address reload creates a new bridge state object/token even if unpacker, target, and native host addresses are numerically identical.

Therefore an old delayed callback cannot look up the raw pair after reload and accidentally bind to the new generation.

The callback call path already has a natural lease scope:

```text
native callback
  -> generated host trampoline
  -> host CallbackUnpack::CallGuestPacker
  -> FEX ThunkHandler_impl::CallCallback
  -> CTX->HandleCallback
  -> guest callback returns
  -> CallCallback returns
```

Acquire the bridge execution lease before `HandleCallback`; release it only after `HandleCallback` returns. This covers the actual host→guest→host transition, not merely lookup.

If the selected bridge state is already `Draining`, reject/tombstone instead of entering guest code.

## 5. Retirement ordering

When a load generation is about to disappear:

```text
mark generation retiring
  -> find every bridge whose Dependencies contains generation
  -> mark those bridges Draining / revoke externally reachable slots
  -> prevent new lease acquisition
  -> remove/invalidate discoverable dynamic-PFN H registrations
  -> invalidate compiled code at bridge keys H and affected guest target ranges as appropriate
  -> wait for Active == 0 on dependent bridge states
  -> physical munmap / VMA resource deletion
  -> later reclaim bridge metadata only when no escaped stable reference can observe freed state
```

The deterministic in-flight race proves that `invalidate caches -> munmap` is not enough: a thread can already possess a selected target outside the invalidated lookup/cache structures.

The physical unmap therefore belongs **after** bridge drain, not merely after registry cleanup.

## 6. Dynamic-PFN path needs stable dispatch if true unload/reload is supported

Current CustomIR can embed T directly as a constant in the compiled H-keyed block. That makes a generic execution lease harder because execution can jump from the compiled bridge straight to T without consulting stable per-bridge state at transition time.

Two practical directions exist:

### A. Full generic direction

Compile H to a stable bridge-dispatch entry/state rather than directly to T. The stable dispatch:

1. carries the original bridge generation token;
2. acquires a lease if not draining;
3. obtains the currently bound T for that same bridge generation;
4. performs the guest transition;
5. releases after the FEX-owned transition/return window is complete.

Reload may create/rebind a new bridge object, but an old selected object remains old and therefore rejects after retirement.

### B. Narrow containment for FEX-owned guest wrappers

For wrappers whose generated `CallHostFunction`/unpacker code is intentionally published outside ordinary DSO call/return scope, selectively mark those guest wrappers `DF_1_NODELETE`.

Current source/evidence supports at least Vulkan, GL, CUDA, and Wayland-client as candidates. Their combined page-rounded ELF LOAD footprint in the hosted audit is about 1.45 MiB.

This cheaply removes the FEX-owned wrapper-code side of the use-after-unmap problem, but it is not a generic callback-target solution: an arbitrary guest target DSO can still be legitimately unloaded while native state retains an FEX-created callback trampoline.

A reasonable staged repair may therefore combine selective wrapper residency with generation-aware callback revocation/leases, while a fully generic dynamic-PFN stable-dispatch design is developed separately.

## 7. Pre-unmap integration point

`GuestMunmap` is entered before the host `::munmap`, and FEX already performs VMA/code tracking around that transition. This gives the runtime a real pre-unmap phase in which generation retirement and drain can happen while the guest code remains physically executable.

Avoid trying to solve this by calling global `ThreadManager::Pause()` from the emulation thread: existing constraints make that an unsafe/simple dead-end, and the bridge-level lease gives a narrower synchronization boundary.

## 8. Required regression classes

A production repair needs more than the original `vulkaninfo` reproduction.

Minimum useful classes:

1. **same-address reload / ABA:** old callback/PFN generation remains revoked, fresh generation works even when raw addresses are identical;
2. **in-flight acquire before retire:** owner remains mapped until transition returns;
3. **selected but lease acquired after retire:** old token rejects rather than entering guest code;
4. **escaped host callback pointer:** retained native pointer reaches a stable revoked state, not unmapped guest unpacker/target code;
5. **dynamic H reuse with changed T/generation:** old compiled/published bridge cannot silently retain/rebind the wrong target;
6. **real application teardown:** historical Fedora `vulkaninfo` environment when reproducible, plus generic GL/Wayland/CUDA lifetime cases;
7. **normal native lifetime semantics:** no promise that arbitrary application-owned function pointers remain valid after the application legitimately releases their owner.

## Current recommended direction

The strongest generic invariant is now:

> FEX-created executable bridges must carry stable load-generation identity, remain revocable after guest mappings disappear, and hold an execution lifetime across every FEX-owned transition that can still require code from those generations. Physical unmap may proceed only after the relevant bridges are draining and their active transitions are gone.

Selective `DF_1_NODELETE` remains a pragmatic containment mechanism for a small set of FEX-owned guest thunk wrappers, not a substitute for generation-aware ownership of arbitrary callback targets.
