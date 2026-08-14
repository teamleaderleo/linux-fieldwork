# FEX thunk lifetime repair synthesis — 2026-08-14

## Executive result

The investigation has moved beyond a source-only hypothesis. Real FEX runtime experiments now demonstrate two independent lifetime classes and the minimum retirement behavior needed to make each safe.

### Guest -> host dynamic function pointers

For `LinkAddressToFunction` / native-host-PFN redirection, the stale state is not one object. There are at least two independently surviving layers:

```text
native host address H
  -> CustomIR definition H -> guest thunk target T
  -> compiled synthetic H block in lookup caches
       -> shared GuestToHostMap/L3
       -> per-thread L1/L2 copies
```

After the guest DSO containing `T` unloads, either retained layer can preserve execution toward the dead generation.

Runtime A/Bs prove:

- the stale H -> T mechanism exists on real current FEX;
- the same mechanism exists on exact FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`;
- handler removal/re-add alone does not fix it;
- exact shared H erase without all required local-cache eviction does not fix it;
- exact pre-unmap retirement plus re-registration fixes moved-generation reload;
- exact retirement must invalidate H from every live emulation thread's private L1/L2, not only the unmapping thread.

### Host -> guest callbacks

For host-callable callback trampolines, FEX allocates process-lived host executable memory whose embedded record contains guest `GuestUnpacker` and `GuestTarget` addresses.

The host trampoline pointer can escape to native libraries and cannot be retracted after publication.

Runtime A/Bs prove:

- an old callback trampoline can survive after its guest target/unpacker generation disappears;
- leaving it untouched reaches stale guest code and faults;
- retaining the escaped host pointer but revoking its FEX-owned dispatch record redirects the old pointer to a controlled tombstone instead of dead guest code;
- removing the retired `{GuestUnpacker, GuestTarget}` cache key allows a later generation to allocate a fresh working host trampoline;
- this remains correct even when the guest loader reuses the exact same guest target/unpacker addresses, preventing same-address ABA from reviving the old host pointer.

These two lifetime classes should share an owner-retirement protocol, but their steady-state dispatch representation need not be identical.

---

## What is now proven

### 1. `LinkAddressToFunction` has a real unload/reload lifetime defect

The retained full-thunk fixture runs under real FEX on hosted AArch64. It uses one stable native host function address `H`, registers a guest invoker `T1`, unloads the guest DSO, reserves the old span so the next generation must move, and reloads a new invoker `T2` while `H` remains stable.

Observed on current FEX:

```text
H stable
T1 unmapped
T2 at a different guest VA
retained H call -> SIGSEGV
fresh direct T2 path -> healthy
```

This removes Vulkan, Mesa, driver objects, proc-address tables, and teardown complexity while preserving the actual FEX marker and dispatch machinery.

### 2. Exact FEX-2608 has the same generic defect

The exact all-cache rebind diagnostic was rerun with source commit:

```text
e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

This is the FEX-2608 source revision used by the original Apple M5 workload.

It exhibits the same forced-different stale H -> old-T failure and the same recovery after exact H eviction plus H -> T2 registration.

Therefore the reduced mechanism is not a regression introduced after FEX-2608.

### 3. `CustomIRHandlers` is only holder one

A controlled negative variant changes duplicate-H registration to:

```text
RemoveCustomIREntrypoint(H)
AddThunkTrampolineIRHandler(H, T2)
```

The handler is removed and the new handler is installed, yet the next H call still faults.

Therefore erasing the `CustomIRHandlers[H]` definition does not remove already-compiled synthetic H dispatch.

### 4. Synthetic H is outside normal page-based invalidation

Current source and executed probes converge on the reason.

CustomIR compilation reports no ordinary guest code ranges for the synthetic native key. The compiled H block therefore has no useful guest `CodePages` ownership tying it to the outgoing DSO's pages.

Normal guest-range invalidation cannot discover H by invalidating the old T range.

The compiled H mapping is placed directly in lookup state. `LookupCache::AddBlockMapping()` seeds the current thread's L1 immediately, and normal lookup order is:

```text
L1 -> L2 -> shared L3
```

That explains why removing the definition or even erasing shared L3 can leave a hot local H dispatch alive.

### 5. Exact H eviction is sufficient in the single-thread case

Two independent runtime paths demonstrate this.

One variant repairs at duplicate registration. Another performs pre-unmap owner retirement.

The successful exact operation is:

```text
retire CustomIR definition H
exact erase shared compiled H mapping/direct links
exact invalidate H in local L1/L2
register H -> T2
```

A moved-generation call then reaches T2 and exits correctly.

### 6. Exact retirement has to cover every emulation thread

Run `31768898015` provides a direct cross-thread A/B.

Worker B preheats its own H cache on generation 1 and then becomes quiescent. Main thread A unloads generation 1, forces generation 2 to a different guest address, and publishes H -> T2. Worker B then calls H again.

`local` variant:

```text
handler removed
shared H erased
unloading thread's local H retired
worker B local H untouched
T2 registered
-> exit 139 before worker produces a valid generation-2 result
```

`all` variant:

```text
handler removed
shared H erased
H invalidated from main thread
H invalidated from worker thread
T2 registered
worker post-reload H call -> expected generation-2 value
exit 0
```

All-thread L1/L2 coverage is therefore a runtime correctness requirement, not a cleanup optimization.

### 7. Owner retirement belongs before physical unmap

The pre-unmap diagnostics track H -> T dependencies and retire H when the outgoing guest range containing T is about to disappear.

With that ordering, the old H path becomes invalid at the legal owner boundary, and a later generation can bind the same stable H to a new T safely.

This is a better lifecycle primitive than waiting for a duplicate registration collision to repair state after the fact.

### 8. Host callback trampolines are independently stale

The full-thunk fixture also preserves a generation-1 host-callable callback trampoline while unloading the DSO containing its guest target/unpacker.

After a forced-different reload:

```text
old callback -> SIGSEGV
new callback -> correct generation-2 result
```

Fixing dynamic H -> T does not fix the old callback. Fixing callback revocation does not fix dynamic H -> T. The two defects are independent retained-reference directions.

### 9. An escaped callback pointer can be made safe without changing its address

FEX owns the host trampoline storage. The generated host callback packer reads its FEX-owned instance record at invocation time.

A diagnostic retirement replaces the callback dispatch function in that record with a stable FEX tombstone before the guest target/unpacker unmaps.

Result:

```text
old escaped callback pointer -> controlled revoked path
new generation callback       -> healthy guest generation-2 target
```

The old native pointer remains valid as a host executable address but no longer reaches the retired guest generation.

### 10. Callback cache-key removal defeats same-address ABA

A second callback run allows normal same-address guest reload.

Generation 2 reuses the same guest target/unpacker numeric addresses. If the old callback cache entry remained keyed only by those addresses, a lookup could return the old revoked trampoline and make address reuse define identity accidentally.

The diagnostic erases the old key during retirement.

Observed result:

```text
same guest target/unpacker addresses reused
old host trampoline remains revoked
new lookup allocates a different host trampoline
new callback works
```

Therefore callback retirement needs both:

```text
revoke escaped old trampoline
erase retired callback cache key
```

---

## Recommended repair architecture

The evidence favors one common ownership layer with different dispatch strategies for the two directions.

### Common owner model

Any FEX bridge containing executable guest addresses should be registered against an owner that can be retired before those addresses stop being executable.

At minimum, the owner records dependencies such as:

```text
Dynamic PFN bridge:
  H
  guest target T
  owner/load identity

Host callback bridge:
  stable host trampoline / descriptor
  GuestUnpacker
  GuestTarget
  owner/load identity
```

The outgoing guest mapping event supplies the retirement boundary.

FEX's VMA tracking already has `MappedResource`, with one object per mapped file/base instance and VMAs pointing to their resource. This is a promising existing load-instance identity, but address-based matching is already enough for the proven sequential safety cases provided retirement is guaranteed before the matching address disappears.

A heavier generation token should be introduced only where it buys concrete semantics: multiple simultaneous owners, safe promotion, or concurrent/draining state.

### Dynamic PFNs: preserve the fast direct path, retire exactly on unload

The normal hot path can stay close to the existing implementation:

```text
guest sees native H
compiled synthetic H block jumps to current guest adapter T
```

No extra descriptor lookup is required on every Vulkan/GL dynamic PFN call.

The cost is paid at rare lifecycle transitions.

On final owner retirement:

```text
1. mark/revoke outgoing H claim(s)
2. remove or replace their CustomIR definitions
3. exact erase shared compiled H mapping
4. delink inbound direct links to H
5. exact invalidate H in every live guest thread's L1/L2
6. only then permit outgoing guest executable mapping to disappear
```

Later registration may compile H against a new T.

### Keep a revoked synthetic-H state rather than falling through to ordinary decoding

A pure erase has an ugly stale-pointer failure mode. Once H is no longer recognized as synthetic, a stale guest call to numeric native H can fall through to normal x86 frontend decoding at an address containing native ARM code.

The production state machine should therefore favor:

```text
ACTIVE(H -> owner/T)
  -> REVOKED(H)
  -> ACTIVE(H -> new compatible owner/T)
```

A stale H while revoked should fail deterministically or route to a controlled synthetic fault path, never decode the native host bytes as guest x86.

Compiled ACTIVE H blocks must still be exact-evicted during the transition so old direct dispatch cannot bypass the state change.

### Callbacks: stable host pointer + stable FEX descriptor

The callback case naturally benefits from permanent indirection because the host pointer may already be stored anywhere in a native driver/library.

Instead of mutating multiple raw fields in executable trampoline memory, a production design should make each published host trampoline point at a process-owned descriptor.

Conceptually:

```text
escaped host callback pointer C
  -> immutable FEX trampoline
  -> stable descriptor D
       state = LIVE | REVOKED
       GuestUnpacker
       GuestTarget
       owner
```

The stable FEX dispatcher atomically observes D's state before entering guest code.

Retirement:

```text
D: LIVE -> REVOKED
remove old callback-cache key
prevent new entry into retired guest addresses
```

A new guest generation receives a new descriptor/trampoline even if its guest numeric addresses are identical to the previous generation.

This adds a small descriptor/state read per host->guest callback, but callback transitions are already much more expensive than an ordinary host function call and the indirection gives a clean correctness boundary for an escaped pointer.

---

## Locking and invalidation transaction

The diagnostic code proves mechanics but is not the desired production lock sequence.

Current compilation obtains `CodeInvalidationMutex` shared before it may consult `CustomIRMutex` while generating IR.

Current `RemoveCustomIREntrypoint()` does the opposite direction internally:

```text
CustomIRMutex
  -> syscall code-invalidation path
```

Using that remover unchanged inside a new global retirement transaction would preserve an inversion opportunity.

The final dynamic-PFN retirement primitive should use one coherent ordering, matching FEX's existing thread-wide invalidation discipline:

```text
ThreadCreationMutex
  -> CodeInvalidationMutex UNIQUE
    -> CustomIRMutex
       mark/remove/revoke outgoing synthetic H definitions
    -> shared GuestToHostMap exact erase/delink for each H
    -> every live thread LookupCache exact H invalidation
  -> release transaction
  -> physical guest unmap
```

Prefer batching all H values owned by the outgoing mapping in one transaction rather than repeatedly acquiring the same global locks.

This also blocks concurrent compilation from recreating a synthetic H block from the outgoing definition while retirement is in progress.

---

## Mapping-event semantics

### `munmap`

Current guest `munmap` performs the host physical unmap before normal FEX range invalidation.

For bridge ownership this is too late. Retirement must occur before the physical unmap while the outgoing executable identity is still valid.

### Failed unmap

A production pre-unmap transaction has to consider failure.

If FEX revokes bridges and the underlying host `munmap` then fails, either:

- validate enough beforehand that the operation is expected to succeed;
- commit retirement only after a reversible/prepared host operation;
- or provide rollback/restoration of bridge claims.

The diagnostics do not model failed `munmap` because the controlled loader paths succeed.

### Other mapping-destroying operations

If the goal is a generic guest-executable lifetime abstraction, equivalent ownership retirement must be considered for operations that can remove/move/replace executable mappings, including relevant `mremap` and replacement mapping cases.

The safety invariant is tied to executable address lifetime, not specifically to the spelling `dlclose`.

---

## Multiple live owners and aliases

The sequential unload/reload defect can be fixed without immediately redesigning all host-pointer identity semantics.

The harder generic compatibility case is:

```text
owner A claims H -> T1
owner B claims H -> T2 while A is still live
A retires
```

Current first-wins behavior does not retain enough semantic information to know whether T2 is a legal replacement.

Numeric guest target equality is not ABI identity. Native H equality is not sufficient either.

The guest thunk helper is generated from the function signature, so a fuller registration API could carry a stable signature/ABI token alongside H and T. That would allow the owner registry to retain multiple claims and promote only a compatible live claim.

A staged implementation is reasonable:

1. fix sequential owner retirement with current collision semantics;
2. retain revoked H rather than native-byte fallthrough;
3. add explicit signature/claim identity if real GL/Vulkan/X11 multi-owner cases require promotion.

Do not silently implement `last T wins` as the generic rule.

---

## Concurrency and execution lifetime

This remains the main unresolved correctness question.

The new multithread A/B deliberately keeps the worker quiescent during retirement. It proves every thread's future cache must be invalidated.

It does not prove safety when another thread is simultaneously:

- reading its L1 entry for H;
- already executing the compiled synthetic H block;
- already committed to guest target T;
- or, for callbacks, entering through a host trampoline concurrently with owner retirement.

Current `LookupCache` source describes cross-thread L1 invalidation as a soft guarantee without atomics and says it has not been thoroughly vetted.

Therefore separate two questions:

```text
A. future selection safety
   Can any thread select the retired bridge after retirement completes?

B. in-flight execution safety
   Can an execution selected before/during retirement cross into T after T is unmapped?
```

A is now strongly proven and requires all-thread exact invalidation.

B is not yet proven.

Possible mechanisms for B include:

- an execution lease/refcount associated with the owner/descriptor;
- a draining state that blocks new bridge acquisition and waits for existing acquisitions;
- stronger thread quiescence at mapping retirement;
- or proving that an existing FEX synchronization boundary already supplies equivalent quiescence for legal guest-loader behavior.

The synthetic Thunderdome ranked `lease_slot` highest because it handles this race explicitly. The new real-FEX evidence validates most of its ownership direction but does not yet prove a lease is necessary for ordinary correctly synchronized guest `dlclose()`.

For host callbacks, asynchronous native invocation makes a descriptor lease/drain particularly plausible.

---

## `NODELETE` remains a legitimate alternate contract

A process-resident generated guest thunk image is still a valid, much smaller policy for selected foundational thunks.

The clean FEX-2608 experiment marks the Vulkan guest thunk `DF_1_NODELETE`.

The original M5 external pinning control already demonstrated:

```text
normal guest-thunk unload -> exit 139
keep only libvulkan-guest.so resident -> exit 0
```

Residency prevents both dynamic-PFN targets and callback unpackers in that image from becoming unmapped.

The new work changes how to interpret this option:

- it is not the only known engineering path;
- true unload/reload is mechanically recoverable with explicit retirement;
- therefore `NODELETE` should be chosen only if FEX wants generated Vulkan bridge code to be process-resident by contract.

That decision trades implementation complexity for memory/static-state/finalizer semantics.

---

## Proposed regression matrix

A generic lifecycle implementation should retain the reduced tests rather than relying only on `vulkaninfo`.

### Dynamic H -> T

1. single-thread load -> register -> call -> unload -> moved reload -> re-register -> call;
2. handler-only removal negative control;
3. shared-L3-only removal negative control;
4. cross-thread worker-L1 preheat, owner-thread unload, moved reload;
5. same-address reload / ABA;
6. aliases where two API names resolve to the same native H;
7. multiple live owners for H if/when promotion semantics are implemented;
8. 32-bit guest variant, including its different implicit native-address ABI.

### Host callbacks

1. old escaped callback after forced-different unload -> deterministic revoked result, not guest SIGSEGV;
2. new callback after reload -> healthy;
3. same-address target/unpacker reload -> old pointer stays revoked, new host pointer works;
4. callback invocation racing retirement if the production descriptor supports asynchronous use;
5. duplicate/signature-equivalent callback creation and cleanup.

### Mapping lifecycle

1. normal final `munmap`;
2. non-final close that does not remove the executable mapping must not retire the owner early;
3. failed unmap behavior;
4. executable `mremap`/replacement cases where relevant;
5. repeated cycles and address reuse.

### Original Vulkan workload

After the generic primitive is viable:

1. FEX-2608-equivalent llvmpipe run;
2. Venus / Apple M5 run;
3. preserve callback-routing correction from the earlier defect;
4. preserve bogus-preload negative control;
5. preserve guest-thunk-pinned positive control;
6. capture the first post-unload synthetic H hit / immediate final caller if possible.

---

## Relationship to the original Apple M5 teardown

The original evidence remains unusually specific:

- Vulkan enumeration succeeds after the separate debug-callback routing correction;
- teardown exits 139 on both Venus and llvmpipe;
- saved guest instruction-fetch fault is inside the old, now-unmapped `libvulkan-guest.so` image;
- the old-image offset resolves to generated `CallHostFunction` code;
- pinning only `libvulkan-guest.so` changes exit 139 -> 0;
- a bogus preload does not;
- exact FEX-2608 now runtime-reproduces the generic stale H -> guest-invoker mechanism in the reduced full-thunk fixture.

This makes dynamic-PFN CustomIR/compiled-H retention the strongest explanation for the original terminal fault.

One evidentiary gap remains: the immediate caller that produced the final transfer in the original M5 `vulkaninfo` teardown has not been directly captured. The saved RIP proves old thunk code was reached, not which retained bridge initiated the transfer.

The host-callback lifetime class is also independently real, so the original workload should not be described as end-to-end proven H -> T until that immediate transfer is captured or a generic retirement patch eliminates the original crash while preserving orthogonal controls.

---

## Selected direction

For an owned-fork research implementation, the strongest next design is:

```text
COMMON
  pre-unmap bridge-owner retirement
  mapping/load ownership records
  explicit REVOKED state

DYNAMIC PFN
  keep existing fast synthetic-H hot path
  exact batch retirement of H from definition + shared map/direct links + every thread cache
  deterministic revoked H until compatible rebind

HOST CALLBACK
  immutable escaped host trampoline
  stable FEX-owned descriptor/dispatcher
  atomic LIVE/REVOKED state
  remove retired callback cache key
  fresh descriptor/trampoline for a new owner generation

CONCURRENCY
  preserve lock order: ThreadCreation -> CodeInvalidation(unique) -> CustomIR
  separately test/solve in-flight execution drain before final physical unmap
```

This direction is narrower than putting every thunk call behind a universal stable slot, but it preserves a place to add a lease/draining state where real concurrency proves it necessary.

## Remaining uncertainty

The remaining questions are now concentrated rather than diffuse:

1. What exact execution-quiescence rule is needed for a bridge already selected when final unmap begins?
2. Does legal guest-loader behavior plus an existing FEX synchronization point already answer that, or is an explicit lease/drain required?
3. What owner identity should the product API expose: raw executable range, `MappedResource`, or a dedicated generation object?
4. How should multiple simultaneously live claims for the same native H carry signature/ABI identity and promotion policy?
5. What controlled guest fault should a revoked synthetic H produce?
6. Can the final original-M5 caller be captured directly, closing the last workload-specific causality gap?

Everything else above has direct source and/or runtime support in retained Fieldwork receipts.

No upstream FEX interaction was performed. All code, branches, workflows, and experiments remained on owned repositories.