# Seventh-pass continuation: existing signature identity and staged owner model

Date: 2026-08-14

Companion to [SEVENTH_PASS_FIELDWORK.md](./SEVENTH_PASS_FIELDWORK.md).

This continuation records source findings made after the main seventh-pass note was written. It focuses on whether the broader load-generation owner model can reuse identities FEX already computes, and where that policy can live without coupling correctness to ordinary SMC behavior.

No upstream interaction is authorized or performed here. This is research/design analysis, not contribution code.

## 1. `CustomIRHandlerEntry::Data` is currently a cheap target-lifetime tag

Current source search found `CustomIRHandlerEntry::Data` used in the CustomIR definition/add path and in thunk duplicate-registration checking. No separate subsystem was found assigning conflicting semantics to this field.

For thunk PFN registrations, FEX sets:

```text
Creator = ThunkHandler
Data    = GuestThunkEntrypoint
```

That makes the existing pair useful for a first range-retirement discriminator:

```text
Creator == ThunkHandler
&& Data inside disappearing guest range
→ registration belongs to guest code being unmapped
```

This is attractive for the narrow M5 A/B because it needs no new owner registry.

For a polished generic model, explicit owner metadata remains preferable. A raw target address answers "which guest code does this active route jump to?" It does not by itself answer "which load generation claimed this PFN?" or "which dormant compatible claims survive?"

## 2. FEX already computes the stable function-pointer signature identity the owner model needs

The thunk generator already canonicalizes runtime host-function-pointer signatures.

For each thunked function-pointer type it computes:

```text
SHA256("fexcallback_" + canonical_function_pointer_signature)
```

The hash intentionally omits the library name. Identical signatures are deduplicated before `MAKE_CALLBACK_THUNK` emission.

The generated callback thunk is then associated with:

```text
fexthunks_invoke_callback<Result(Args...)>
```

and `GetCallerForHostFunction()` selects its `CallHostFunction` specialization only from the C++ function signature.

This has several useful consequences.

### Within one guest-wrapper generation

Functions with truly identical guest-call ABI signatures naturally converge on the same `CallHostFunction` specialization/invoker address.

The guest target address is therefore a practical per-generation signature identity.

### Across a relocated reload

The DSO base may move, so the raw invoker address changes even when the signature is identical.

The already-generated callback SHA-256 stays stable. It is a much better compatibility key for dormant-owner promotion than comparing relocated guest addresses.

### Across thunk libraries

Because the signature hash omits the library name, the same canonical guest function-pointer ABI can carry the same identity in Vulkan, GL, CUDA, or another generated thunk library built for that guest ABI.

This directly fills the `Signature` field used by the synthetic `thunk_owner_registry_probe.cpp`; a production design does not need to invent a parallel type-hash scheme.

## 3. Current `LinkAddressToFunction` discards that signature identity

The current internal registration operation carries only:

```text
original_callee = native host PFN
target_addr     = guest CallHostFunction invoker
```

The Linux thunk handler forwards those two values to:

```text
Context::AddThunkTrampolineIRHandler(native_pfn, guest_target)
```

So the stable callback signature hash exists during thunk generation but is absent from the PFN ownership record.

That is sufficient for current first-wins dispatch. It is insufficient for safe automatic promotion after an active owner disappears:

```text
same native PFN
  claim A: guest target A, signature S
  claim B: guest target B, signature ?
```

Without a stable signature identity, FEX cannot prove B is ABI-compatible with the previously active route after A unloads.

## 4. Staged compatibility design

A narrow correctness repair and a generic owner model can be deployed as separate layers.

### Stage A: existing two-field registrations

For old/current registration requests:

```text
{ native PFN, guest target }
```

support:

- target-range retirement on unmap;
- exact synthetic-key cache eviction;
- clean tombstone/removal of the active route;
- later fresh registration after unload.

Avoid automatic dormant-owner promotion when compatibility cannot be proved.

This is already enough to test the observed Vulkan crash and fix the stale active route class.

### Stage B: versioned registration with signature identity

A future internal operation can carry:

```text
{ native PFN, guest target, callback signature SHA-256 }
```

That enables:

- active + dormant claims;
- compatible-owner promotion;
- incompatible collision retention for diagnostics;
- reload revival of tombstoned PFNs;
- cross-library collision reasoning.

A versioned FEX-internal thunk operation is cleaner than silently extending the existing argument record. An old guest wrapper supplies the old payload; a newer wrapper can opt into the richer ownership contract. This avoids a new host implementation reading fields beyond an old guest payload.

Exact naming/versioning remains a human implementation decision.

## 5. The current use sites fit mapping-backed ownership

Current source search found direct `LinkAddressToFunction` use in:

- Vulkan guest thunk;
- GL guest thunk;
- CUDA guest thunk;
- shared guest helper code.

The linked guest targets are generated thunk-wrapper invokers or guest-thunk-local fallback code. They live in mapped guest thunk DSOs.

No current call site was found registering an arbitrary anonymous/JIT guest target through this API.

This makes VMA-backed load-generation ownership a natural fit for the feature as it exists today.

A future generic API can still define a fallback owner class if new users appear.

## 6. VMA tracking has resource identity but no persistent load-generation number

FEX VMA tracking defines:

```text
MRID { dev, id }
MappedResource
VMAEntry -> MappedResource
```

The comments explicitly state that the same ELF/PE file mapped at different base addresses receives separate `MappedResource` objects while retaining the same MRID.

That means:

- MRID identifies backing storage;
- it does not uniquely identify one load generation;
- `MappedResource*` identifies the live object but dies with the mapping and can be unsuitable as a durable tombstone owner ID.

For range-retirement Stage A, no owner number is required.

For the richer owner registry, a monotonic load-generation token (or an equivalent durable identity) is cleaner. It can be associated with each mapped resource generation and copied into PFN claims while the target is live.

Important case:

```text
same ELF
unload
reload at same base
```

MRID and addresses may both repeat. A true generation token distinguishes the two lifetimes.

## 7. The Linux thunk handler is a natural process-lifetime registry home

Guest wrappers call the FEX load thunk from a constructor.

The Linux thunk handler:

- `dlopen`s the native host thunk;
- records the library name in a process-lived `Libs` set;
- stores thunk definitions in a process-lived map;
- retains host-to-guest trampoline caches;
- has no symmetric host-thunk unload path for guest wrapper `dlclose`.

This explains the lifetime asymmetry cleanly:

```text
native host thunk / PFN identity      process-lived
PFN ownership registry               can be process-lived
guest wrapper generation             unloadable/reloadable
```

A PFN claim registry can therefore outlive individual guest wrapper generations while revoking claims as those generations disappear.

There are two plausible homes:

### Linux `ThunkHandler`

Benefits:

- already owns thunk-specific runtime state;
- link registration arrives here first;
- Linux syscall handler can call a thunk-specific retirement method after guest mapping changes;
- keeps load-generation policy outside generic CustomIR.

Core then only needs exact active synthetic-entry install/replace/evict operations.

### FEXCore `Context`

Benefits:

- CustomIR registration and compiled-cache state live here;
- one lock domain can atomically change active route + cache;
- `AddThunkTrampolineIRHandler` already lives here.

This would require opaque owner/signature metadata to cross into Core.

The final placement should prioritize lock simplicity. The owner policy is thunk-specific, while exact cache replacement is clearly a Core responsibility.

A split design may be cleanest:

```text
ThunkHandler registry decides active claim
        ↓
Context atomically installs/replaces/evicts active synthetic route
```

## 8. The registration syscall can resolve owner generation host-side

`ThunkFunctions::LinkAddressToGuestFunction` receives the guest invoker address and has access to:

- the current FEX guest thread;
- the Linux syscall handler;
- the FEX context.

Therefore an explicit owner generation does not have to be manufactured by guest thunk code. The host side can resolve the guest target to its tracked mapping/resource while registration occurs.

Potential flow:

```text
guest LinkAddressToFunction(native_pfn, guest_target, [signature])
        ↓
Linux thunk handler
        ↓
resolve guest_target -> current mapped-resource generation
        ↓
owner registry claim
        ↓
activate/retain/reject according to signature + generation
```

This preserves guest-facing simplicity and makes the VMA tracker the authority on whether an owner generation is still alive.

## 9. Ordinary code invalidation is explicitly gated by SMC policy

`SyscallHandler::InvalidateCodeRangeIfNecessary()` calls the ThreadManager invalidator only when:

```text
SMCChecks != CONFIG_SMC_NONE
```

`mremap` invalidation has the same SMC gate.

Thunk ownership retirement is a lifetime correctness operation. It must remain effective when normal SMC detection is disabled.

Therefore a production cleanup path should be conceptually separate from:

```text
if SMC enabled -> invalidate ordinary decoded guest code
```

It can share low-level locking/cache helpers, but its invocation must be unconditional when a registered guest thunk target ceases to exist.

This is one reason the earlier `CUSTOM_IR_FINDINGS.md` synthetic `SMC-none` control is important.

## 10. The earlier full-FEX candidate needs exact synthetic-key invalidation

`CUSTOM_IR_FINDINGS.md` correctly identified that both registration retirement and compiled-route invalidation are required.

It proposed collecting synthetic PFN keys, then invalidating those keys through existing thread-manager/cache machinery.

The seventh source pass adds a specific correction:

- ordinary range invalidation uses `CodePages` / `CachedCodePages` reverse indexes;
- compiled CustomIR blocks have empty `CodePages` dependencies;
- therefore passing a synthetic PFN through the current range invalidator does not guarantee the compiled custom block is removed.

The full-FEX candidate needs an **exact entrypoint** operation.

Conceptually:

```text
for each affected native PFN:
    every live GuestToHostMap:
        Erase(native_pfn)        # also delinks inbound callers
    every live thread cache:
        InvalidateCache(native_pfn)
    clear call/return shadow state as required
```

This exact path should also become the basis of `RemoveCustomIREntrypoint()` correctness.

## 11. Suggested two-level testing plan

### Level 1: prove the narrow active-route repair

Use the retained M5 path and/or generic thunk test:

```text
unmap guest target range
→ retire active CustomIR registration by stored target address
→ exact-evict native PFN synthetic block
→ rerun
```

This requires no new signature token and no dormant-owner promotion.

### Level 2: prove generic owner semantics

Once Level 1 changes the real failure as predicted, exercise:

- two compatible live owners;
- active owner unload;
- dormant owner promotion;
- incompatible same-PFN claim;
- full unload to tombstone;
- reload at changed base;
- reload at same base but new generation;
- aliases sharing one load generation;
- old two-field registration compatibility.

The existing `thunk_owner_registry_probe.cpp` already demonstrates the abstract state transitions with `22 passed / 0 failed`. The missing integration proof is that FEX's actual mapping, CustomIR, and cache ownership can feed those transitions correctly.

## 12. Updated questions

### Signature transport

- Can the existing callback SHA-256 be surfaced to the PFN-link helper with minimal generated metadata?
- Is a versioned internal link thunk the cleanest compatibility boundary?
- Would passing the signature callback-thunk identity and resolving its embedded SHA be simpler than materializing a 32-byte hash in each guest-side invoker table?

### Generation identity

- Should `MappedResource` gain a monotonic generation ID?
- Is the generation assigned on mapped-resource insertion, or only when a thunk PFN first claims a target in that resource?
- How should `fork` copy or reseed the generation namespace? Copying the live registry into the child may be correct because mappings are inherited.

### Registry placement

- ThunkHandler owner registry + Core active-route operations?
- Context-owned thunk claim registry with opaque owner tokens?
- Which choice gives one unambiguous lock order across registration, compilation, unmap retirement, and fork?

### Replacement events

A final repair should audit all events that can destroy/replace an invoker target:

- `munmap`;
- `mremap` move/shrink;
- `MAP_FIXED` replacement through `mmap`;
- `shmdt` only if this API ever gains shared-memory targets;
- process exit needs no per-entry cleanup for correctness.

`mprotect` remains a permission event rather than an obvious generation-death event.

### Old registrations

- Existing two-field routes can be retired safely by target range.
- If several live old-format claims collide on one PFN, there is no stable compatibility token for automatic promotion.
- Conservative behavior is preferable: remove the dead active route and wait for a fresh registration instead of guessing ABI compatibility.

## 13. Current design preference

For the immediate investigation:

```text
Data-range retirement
+ exact synthetic-entry eviction
```

is the smallest discriminating repair.

For the generic model after causal confirmation:

```text
process-lived PFN registry
    key: native PFN
    claims:
      mapped-resource generation
      guest invoker
      existing callback-signature SHA-256
      sequence/priority
    active claim or tombstone

VMA generation retirement
    ↓
revoke claims
    ↓
exactly evict compiled active route
    ↓
promote compatible survivor if proven
```

This matches three independently arrived-at observations:

1. FEX's 2022 review anticipated host-PFN unload/rebinding and same-PFN/multiple-thunk collisions.
2. The current source retains enough target metadata to perform range retirement and already generates a stable callback-signature hash.
3. The owned synthetic owner-registry probe demonstrates the desired active/dormant/tombstone/reload state transitions.

The remaining real-runtime gap is still the immediate dispatch receipt at the terminal M5 fault. Guest R11 remains the highest-value next probe.
