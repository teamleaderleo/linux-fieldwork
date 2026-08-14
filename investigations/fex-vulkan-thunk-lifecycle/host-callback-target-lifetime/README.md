# FEX host callback target lifetime successor

## TL;DR

The guest-wrapper self-pin candidate protects executable code that lives in FEX's own guest thunk wrapper, including `CallbackUnpack<...>::Unpack` and generated guest-to-host continuation code. It does **not** establish a lifetime rule for an arbitrary `GuestTarget` supplied by a different unloadable guest DSO.

This successor investigation isolates that remaining question with a fresh-process synthetic FEX thunk fixture. Native host state will retain a host-callable trampoline after the guest target DSO is unloaded. The fixture must distinguish three cases: target resident, target unloaded, and target kept alive deliberately.

No result from this successor is required to validate the original Vulkan-wrapper teardown repair. It tests a broader generic API contract.

## Explain like I'm five

FEX can hand native ARM code a special callable pointer that eventually jumps back into x86 code.

That pointer remembers two x86 addresses:

- a small FEX helper that knows how to unpack the arguments;
- the real x86 function the program wanted called.

The self-pin repair keeps the FEX helper alive. But the real x86 function might live in some completely different library. If that second library is unloaded while native code still keeps the special callback pointer, FEX may still have a perfectly good doorway whose destination has disappeared.

This test checks exactly that case.

## Why care

`MakeHostTrampolineForGuestFunction` publishes a raw native-callable function pointer. Native code is free to retain that pointer beyond the immediate call that created it. The trampoline embeds a raw `GuestTarget` address and a raw `GuestUnpacker` address. Cache erasure cannot revoke copies already held by native code.

If the API has no explicit unregister/release contract, FEX needs some lifetime policy for every guest executable address reachable through a published trampoline.

## Source boundary

Primary runtime source under study:

- FEX-2608: `e869aa644a16e4332cdc15c1ea0b4d13d482385d`.

Relevant source behavior already established:

- `ThunkHandler_impl::MakeHostTrampolineForGuestFunction` caches by raw `(GuestUnpacker, GuestTarget)`.
- the emitted host trampoline stores `GuestUnpacker` and `GuestTarget` as executable guest addresses;
- native host code can retain the returned function pointer independently of the cache;
- guest `munmap` / VMA deletion has no edge that revokes or retires those externally published native pointers.

## Bounded question

When native host code still holds a host-to-guest trampoline, what happens if the guest DSO containing **only the `GuestTarget`** loses its final loader reference while the FEX-owned `GuestUnpacker` remains resident?

## Fixture shape

Use three components in one fresh FEX process:

1. **guest callback target DSO**
   - x86-64;
   - exports one trivial callback such as `int callback(int)`;
   - no FEX thunk code inside it;
   - application opens it with `dlopen`, resolves the target with `dlsym`, and can drop its final handle with one `dlclose`.

2. **guest thunk test wrapper**
   - supplies `CallbackUnpack<decltype(callback)>::Unpack` as the `GuestUnpacker`;
   - asks FEX to create the host trampoline for the target address;
   - passes the resulting native-callable trampoline to host state.

3. **host thunk state**
   - stores the native-callable trampoline pointer in a static/global slot;
   - exposes one thunk to invoke the stored callback later;
   - does not reacquire or recreate the trampoline before invocation.

The important ownership split is deliberate:

```text
GuestUnpacker -> FEX guest thunk wrapper -> retained by wrapper self-pin
GuestTarget   -> separate guest DSO      -> ordinary application lifetime
Host pointer  -> native host thunk state -> survives guest target dlclose
```

## Required phases

### Phase A — live control

1. load target DSO;
2. resolve target;
3. publish trampoline to host state;
4. invoke through host state;
5. require the expected callback result.

This proves the trampoline and ABI wiring work before any unload.

### Phase B — unload discriminator

1. close the application's only target-DSO handle;
2. verify the target address is no longer mapped;
3. invoke the **already-published** host callback pointer without calling trampoline creation again.

The current raw-address model is expected to fault or otherwise demonstrate invalid guest entry. The exact signal should be recorded rather than assumed in advance.

### Phase C — target pin positive control

Repeat in a fresh process, but retain one deliberate extra reference to the target DSO before the application's ordinary close.

Require:

- target mapping remains present;
- the same already-published host callback succeeds after the ordinary close;
- dropping the deliberate pin is the action that finally permits unmapping.

### Phase D — cache-erasure negative control

If practical, erase/retire the FEX cache entry after publication while leaving native host state's trampoline pointer intact, then unload the target DSO and invoke the saved native pointer.

Expected interpretation: cache removal alone cannot revoke the already-published pointer. This phase is secondary if it requires invasive FEX instrumentation; the external-pointer fact is already visible in source.

## Distinguishing matrix

| Case | Guest wrapper | Target DSO | Published host pointer | Expected discriminator |
|---|---|---|---|---|
| live control | mapped | mapped | retained | callback succeeds |
| target unload | mapped | unmapped | retained | stale target becomes observable |
| target pin | mapped | mapped by extra ref | retained | callback succeeds after ordinary close |
| cache erase only | mapped | unmapped | retained | saved pointer remains independently callable/stale |

## What would count as a generic defect

The generic lifetime defect is demonstrated if all of these are true in the real FEX path:

1. native code retains a published trampoline;
2. the `GuestTarget` DSO can unload while that pointer remains retained;
3. later invocation reaches an unmapped or generation-reused target address;
4. FEX has no release/revocation mechanism that invalidates the externally held pointer before unload.

## Candidate design space after reproduction

Do not choose a generic fix before the real FEX fixture runs. The likely design families are:

### Lifetime ownership / pinning

A published trampoline owns references to guest mappings/modules containing every guest executable address it can enter. With no release callback, this may imply process-lifetime retention.

Advantages:

- matches the raw-pointer API;
- simple invocation path;
- prevents both stale target and stale unpacker addresses.

Cost:

- intentionally reduces guest DSO unloadability.

### Revocable stable indirection

Publish a stable native trampoline whose mutable slot records module identity/generation and validity. Invalidate the slot before the target mapping disappears; invocation checks validity before entering guest code.

Advantages:

- supports real unload when an API has a clear callback lifetime.

Costs:

- requires a reliable pre-unmap invalidation edge;
- still needs an API or ownership rule telling FEX when a callback is no longer externally retained;
- generation must be checked at invocation, not merely added to the cache key.

### Cache-key generation only

Insufficient by itself. It can stop a later lookup from reusing an old cache entry, but cannot revoke a native pointer already copied into host state.

## Relationship to Vulkan

Vulkan gives a concrete ownership split:

- guest `libvulkan-guest.so` supplies `CallbackUnpack<...>::Unpack`;
- guest X11 supplies `XSync`, `XGetVisualInfo`, and `XDisplayString` targets;
- native Vulkan host state stores host-callable trampoline pointers.

The current combined Vulkan gate proves registration occurs with the real constructor and that the guest Vulkan wrapper remains resident. It does not force one of those X11 callbacks after a guest X11 unload, so this successor remains open.

## Evidence limits

Until this synthetic fixture executes through real FEX thunk machinery, the arbitrary-target issue is source-supported and reproduced by the earlier native model, but not yet independently demonstrated end-to-end inside FEX.

Do not use this open successor to weaken the narrower result already demonstrated for `libvulkan-guest.so` lifetime.

## FEX contribution boundary

The FEX source checkout says that AI-generated code must not be used for project contributions. This Fieldwork branch is therefore a research/evidence carrier, not an upstream-ready FEX contribution branch. Any experimental source mutation used to obtain evidence remains research-only unless a human independently authors an acceptable contribution under FEX's rules.

## Next action

Finish the original real-`vulkaninfo` application gate first. Once its llvmpipe result is recorded, implement this successor as a fresh-process synthetic fixture on a separate Fieldwork execution branch so the application repair and generic target-lifetime question remain independently reviewable.
