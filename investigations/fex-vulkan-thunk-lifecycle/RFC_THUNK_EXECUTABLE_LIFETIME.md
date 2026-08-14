# RFC: Executable lifetime for FEX guest thunks

Date: 2026-08-14
Status: research proposal
Scope: owned research surfaces only

## TL;DR

FEX can publish or retain executable guest addresses beyond the load generation that owns them. The investigation has demonstrated this in both major bridge directions:

- native function pointer -> guest `CallHostFunction<signature>` adapter;
- native callback path -> guest `CallbackUnpack<signature>::Unpack` and guest callback target.

The proposed rule is:

> Executable guest code that escapes a wrapper generation needs an owner whose lifetime covers every retained reference to that code.

For the current generated thunk set, two practical repairs are ready for review:

1. selective `DF_1_NODELETE` on lifetime-sensitive guest wrappers as immediate containment;
2. a generated resident per-library bridge that owns escaped signature adapters and callback unpackers while ordinary API wrapper code remains unloadable.

Full owner/generation retirement plus execution quiescence remains necessary when FEX must reclaim executable code that can still be selected or executed by another thread, or when an independently unloadable guest callback target is retained past its owner lifetime.

## Explain like I'm five

FEX builds small pieces of guest executable code that act like doorways between native libraries and x86 code. Some native objects keep the address of a doorway after the guest library that contained it has been unloaded.

The address still exists as a number, while the code behind it is gone.

There are two clean ways to avoid that:

- keep the whole guest wrapper loaded;
- move the doorways that can escape into a small companion library that stays loaded, while the rest of the wrapper can unload normally.

If FEX also wants to reclaim the escaping doorway itself, it needs a stronger owner/generation and execution-drain mechanism before unmapping it.

## Why care

The original FEX-2608 Vulkan investigation observed an x86 `vulkaninfo` teardown failure whose result changed when the guest Vulkan thunk stayed resident. Subsequent controlled tests independently reproduced the lifetime mechanism with generated thunks, forced moved reloads, callback paths, and in-flight execution.

Current upstream FEX main still contains the relevant lifetime relationships. The exact historical application crash has a narrower evidence boundary, while the generic ownership problem now has independent runtime proof.

## Current source model

Current main audit:

- FEX main inspected: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`;
- historical FEX-2608 runtime: `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

`LinkAddressToGuestFunction` registers a native address `H` through `AddThunkTrampolineIRHandler(H, T)`, where `T` is a generated guest thunk entrypoint. The resulting CustomIR path is keyed by `H` while embedding `T` as its guest exit target.

Host->guest callback trampolines separately retain raw guest executable addresses, including `GuestUnpacker` and `GuestTarget`.

See [`CURRENT_MAIN_LIFETIME_AUDIT_20260814.md`](./CURRENT_MAIN_LIFETIME_AUDIT_20260814.md).

## Demonstrated failure classes

### 1. Future dispatch can retain an old generation

Moved-generation tests show that a native PFN `H` can remain bit-identical while the guest wrapper reloads at a different address and produces a different wrapper-owned adapter `T`.

Exact H retirement, cache eviction, and fresh registration can repair future dispatch to the new generation.

This establishes that host address alone is insufficient generation identity.

### 2. Cache retirement cannot revoke an already-selected target

A deterministic two-thread test stops one emulation thread after FEX has selected guest target `T`. A second thread retires H->T, clears the relevant caches, and physically unmaps the owner. When the first thread resumes, it executes the already-selected stale target and faults.

Observed control:

```text
pin=0
unmap=139
```

Therefore true reclamation of an executable target requires an execution-lifetime rule in addition to registry and cache retirement.

See [`NODELETE_RESIDENCY_AND_INFLIGHT_RACE_20260814.md`](./NODELETE_RESIDENCY_AND_INFLIGHT_RACE_20260814.md).

### 3. Host callback state can retain wrapper-owned executable unpackers

Generated or handwritten callback setup can publish `CallbackUnpack<signature>::Unpack` into native/FEX state that outlives the ordinary wrapper generation.

Vulkan X11, GL helper paths, and DRM callback experiments all exercise this class.

A resident unpacker removes that wrapper-lifetime dependency. The actual callback target remains owned by the guest image that supplied it.

### 4. Same-address replacement creates an ABA identity problem

`MAP_FIXED` tests demonstrate that a successful destructive replacement can install a new executable mapping at the same numeric guest address. Address equality therefore cannot identify the old and new load generations.

The current research branch has separately demonstrated:

- pre-retirement before destructive replacement;
- rollback when the destructive syscall fails;
- explicit re-registration after a successful replacement;
- non-reusable owner IDs for VMA mapping generations.

The owner-ID runtime discriminator records the key target mapping changing from owner `0xe` to owner `0xf` across successful same-address `MAP_FIXED`, while an RX->RW->RX `mprotect` cycle preserves owner `0xe` and still exposes the modified code through the existing H path. Failed replacement creates no new owner and transaction rollback restores the old H -> T claim.

See [`MAP_FIXED_PRE_RETIRE_LOG.md`](./MAP_FIXED_PRE_RETIRE_LOG.md), [`MAP_FIXED_ROLLBACK_LOG.md`](./MAP_FIXED_ROLLBACK_LOG.md), and [`VMA_OWNER_ID_LOG.md`](./VMA_OWNER_ID_LOG.md).

## Immediate containment: selective NODELETE

Owned-FEX candidate:

```text
candidate/selective-nodelete-guest-thunks-20260814
cee502da1867531621f3f8af8483c31ea22776a0
```

The candidate adds an opt-in `NODELETE` argument to the generated guest-library helper and enables it for Vulkan, Wayland client, GL, and CUDA.

For Vulkan, a focused FEX residency A/B measured the exact retained mapping difference after final `dlclose`:

```text
normal after close    3,985,408 bytes
NODELETE after close  4,296,704 bytes
difference              311,296 bytes = 304 KiB
```

The lost mappings in the normal arm are exactly the guest Vulkan wrapper mappings. Guest X11, libstdc++, libgcc, and native host Vulkan are already resident in both arms.

### Advantages

- tiny product change;
- directly protects both wrapper-owned dynamic PFN adapters and wrapper-owned callback unpackers;
- no FEXCore/JIT reclamation changes;
- validated with real ARM64 FEX execution;
- straightforward rollback: remove the linker policy.

### Cost and caveat

Process residency increases for each selected wrapper that has been loaded.

`dlmopen(LM_ID_NEWLM, ...)` exposes a real namespace caveat: retaining a NODELETE object in new namespaces can consume loader namespace slots. A base-namespace-only runtime promotion experiment also failed as a general repair because an unloadable NEWLM generation can publish wrapper-owned callback unpackers into persistent host state before closing.

Therefore NODELETE is strongest as a deliberate wrapper-lifetime policy, with loader-namespace semantics called out explicitly.

## Unload-preserving repair: generated resident bridge

The resident bridge moves escaped generated executable helpers out of the ordinary unloadable wrapper.

The current Vulkan prototype derives both wrapper and bridge from the same thunkgen guest output:

```text
normal guest runtime signatures    = 476
resident bridge runtime signatures = 476
sets identical                     = yes
wrapper NODELETE                   = no
wrapper NEEDED bridge              = yes
bridge NODELETE                    = yes
```

Runtime gates pass for:

- retained `vkEnumerateInstanceVersion` after wrapper/GIPA unmap;
- Vulkan/X11 callback path after wrapper unmap using resident unpackers;
- forced moved reload with stable native H and a moved wrapper generation;
- real distro `vulkaninfo --summary` with many dynamic Vulkan PFNs routed through resident bridge adapters.

See [`GENERATED_VULKAN_SPLIT_BRIDGE_PFN_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_BRIDGE_PFN_RUNTIME_2026-08-14.md), [`GENERATED_VULKAN_SPLIT_BRIDGE_X11_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_BRIDGE_X11_RUNTIME_2026-08-14.md), [`GENERATED_VULKAN_SPLIT_MOVED_RELOAD_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_MOVED_RELOAD_RUNTIME_2026-08-14.md), and [`HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md`](./HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md).

GL independently passes the same moved-wrapper/stable-H lifetime test. This removes Vulkan-specificity from the core design claim.

## Generator coverage is expanding beyond direct callbacks

Current-main DRM `drmHandleEvent` exposes callbacks inside `drmEventContext`. A research `callback_member` annotation lets thunkgen generate the nested callback allocation/finalization automatically.

Observed matrix:

```text
native=0
pristine_reference=132
generated_candidate=0
```

The generated guest code copies the caller structure, replaces only annotated callback members in the temporary copy, and transports it normally. Generated host code finalizes each typed trampoline before calling libdrm.

See [`DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md`](./DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md).

This gives thunkgen enough semantic information to classify another escape shape without handwritten DRM bridge code.

## Lifetime classes

The proposed implementation should treat three owners separately.

### Wrapper generation

Ordinary exported guest API wrapper code belongs to the loaded wrapper generation and may remain unloadable.

### Escaped generated adapter

Generated `CallHostFunction<signature>` adapters and generated `CallbackUnpack<signature>::Unpack` helpers whose addresses escape the wrapper belong to a resident bridge owner.

The first generic implementation should use one resident companion per thunk family and bitness. Cross-library deduplication is a later optimization after semantic identity is proven sufficient.

### Actual callback target

The guest function supplied as a callback target belongs to its actual guest mapping/load generation.

A resident unpacker cannot extend that target's lifetime. If native/FEX state retains a callback after its target owner can unload, the target needs explicit owner/generation retirement and an execution-safety rule.

## Retained containing objects are a separate contract

`drmEventContext` is consumed synchronously by `drmHandleEvent`, so a temporary converted copy is sufficient.

`drmServerInfo` is different: native libdrm retains the containing structure pointer after `drmSetServerInfo` returns and later invokes its callback.

Generator metadata therefore needs two independent concepts:

```text
callback member            -> how the callable pointer crosses ISA
retained containing object -> who owns the converted object and for how long
```

Conflating these would hide another use-after-lifetime class behind successful callback conversion.

## Full reclamation model

When FEX needs physical reclamation of an escaped executable target, the research now separates four layers:

```text
mapping-generation identity  -> owner ID + exact target
transaction integrity        -> prepare / commit / rollback around destructive mapping changes
future lookup correctness    -> exact H retirement, cache eviction, revoked/active state
already-in-flight execution  -> quiescence, lease, hazard, epoch, or equivalent generation validation
```

The serial `MAP_FIXED` transaction experiment has validated rollback behavior:

```text
failed replacement      -> old H restored, exit 0
successful replacement  -> old H remains revoked, exit 139 control
successful + new claim  -> H reactivated to generation 2, exit 0
```

The VMA identity discriminator is also green:

```text
failed replacement      -> no replacement owner; old claim restored
successful MAP_FIXED    -> same T, OwnerID 0xe -> 0xf
successful + new claim  -> generation 2 returns 222
mprotect RX/RW/RX       -> OwnerID 0xe preserved; modified code returns 333
```

This validates mapping-generation identity independently of the transaction layer and the separate already-selected execution race.

## Designs rejected or demoted by evidence

### Target-range invalidation alone

Insufficient because the compiled custom path is keyed at H and can retain a dependency on T.

### Exact H retirement plus all-thread cache invalidation

Repairs future dispatch and still loses the select-before-unmap race.

### Address equality as generation identity

Fails on same-address replacement and moved/reloaded ownership cases.

### Base-namespace-only runtime NODELETE promotion

Fails when a NEWLM wrapper generation publishes generation-owned callback unpackers into persistent host state.

### Immediate process-global cross-library bridge

Premature. FEX has historical evidence that GL and Vulkan helper symbol identity can collide when internal interfaces are insufficiently namespaced. Signature equality alone also may omit semantic differences carried by generator annotations.

## Proposed staging

### Stage A — containment

Review selective NODELETE as the smallest production correction for wrappers whose generated executable helpers escape into persistent state.

### Stage B — generated resident companions

Teach thunkgen to emit per-library/per-bitness resident bridge output directly from typed analysis rather than regex post-processing generated C++.

Bridge output should include:

- indirect host-call signatures used by proc-address returns;
- direct callback parameter unpacker signatures;
- nested `callback_member` signatures;
- explicitly declared custom raw-address helpers whose executable addresses escape.

### Stage C — retained-object metadata

Add an explicit contract for converted objects retained by native libraries after the thunk call returns.

### Stage D — reclaimable external targets

Use owner/generation identity, transaction-safe retirement, exact future-path invalidation, and execution quiescence for guest callback targets or bridge code that FEX deliberately wants to reclaim.

## Open discriminators

The following tests can still change implementation details:

- 32-bit generated resident-bridge runtime proof;
- explicit loader-namespace policy for resident companions;
- same workload with two independent NEWLM namespaces and independent close/reload cycles;
- real incremental resident-memory accounting for generated bridge versus whole-wrapper NODELETE;
- callback target placed in a separately unloadable guest DSO, with retained native callback state and concurrent unregister/unload;
- production generator representation for custom escape metadata and retained containing objects.

## Review questions

A maintainer reviewing this proposal should be able to answer these independently:

1. Is process-lifetime residency acceptable for the selected generated guest wrappers? If yes, selective NODELETE is the smallest repair.
2. If wrapper unload is a desired contract, is a resident per-library generated bridge an acceptable owner for executable adapters that escape wrapper lifetime?
3. What loader-namespace semantics should private FEX bridge DSOs have?
4. Which guest callback targets are expected to remain valid after their supplying guest image unloads, and where should that contract be expressed?
5. Does FEX require reclamation of escaped bridge executable code during process lifetime? If yes, the owner/generation plus execution-quiescence work becomes product scope.

## Evidence boundary

This RFC is a research synthesis, not an upstream submission.

The exact historical Apple M5 terminal transfer remains incompletely captured. The generic lifetime mechanism, moved-generation behavior, callback-unpacker lifetime, same-address ABA, transaction rollback, owner-ID separation, and in-flight race all have independent controlled evidence.

The hosted Ubuntu `vulkaninfo` unsplit and split variants both exit `0`; that run is compatibility coverage for the split design rather than a reproduction of the historical teardown failure.

No upstream FEX repository interaction is authorized or performed by this record.
