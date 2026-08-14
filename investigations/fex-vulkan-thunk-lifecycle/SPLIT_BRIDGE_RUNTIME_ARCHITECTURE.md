# Split guest bridge runtime: ownership model and experiments

## Status

This note records the emerging third contract for FEX thunk lifetime:

- keep ordinary guest wrapper DSOs physically unloadable;
- move executable bridge adapters whose useful lifetime is process-wide into a small process-resident guest bridge runtime;
- keep genuinely library-generation-owned state in the ordinary wrapper;
- do not claim that residency of bridge code solves lifetime of arbitrary callback targets or other stateful objects.

This is distinct from both whole-wrapper `DF_1_NODELETE` and a fully generation-aware physical-unload reclamation protocol.

## Why this contract exists

The original dynamic host-function-pointer mechanism associates a native host function pointer `H` with generated guest adapter code `T` through `LinkAddressToFunction(H, T)`. The generated adapter is a `CallHostFunction<signature>` instantiation. FEX may cache executable routing keyed by `H` after the DSO containing `T` has become unloadable.

The host-to-guest callback path has the symmetric shape. FEX caches host trampolines by the pair:

```text
{ GuestUnpacker, GuestTarget }
```

and stores both raw guest addresses in the generated host trampoline instance. For Vulkan's X11 integration:

- `GuestTarget` is an actual guest libX11 function such as `XSync` or `XDisplayString`;
- `GuestUnpacker` is `CallbackUnpack<signature>::Unpack`, currently emitted inside `libvulkan-guest.so`;
- the host-side `X11Manager` is process-resident with the host Vulkan thunk.

Therefore the current guest Vulkan DSO owns executable adapter code whose semantics do not inherently depend on the Vulkan wrapper generation.

## Generator identity already points toward process ownership

In FEX thunkgen, callback-thunk identity is generated from:

```text
SHA256("fexcallback_" + canonical_function_pointer_signature)
```

The library name is not part of this identity, and the generator explicitly deduplicates equal callback hashes while emitting a guest thunk.

That means FEX's ABI identity model is signature-based even though the emitted machine code is currently placed inside each guest wrapper DSO. This mismatch is important: bridge identity is naturally broader than wrapper-image lifetime.

A future process-owned bridge runtime could potentially deduplicate adapters across thunk libraries, not only across Vulkan wrapper generations. That requires separate compatibility work before it should be treated as a product design.

## Confirmed real Vulkan result: one guest-to-host dynamic PFN

A hosted ARM64 experiment on pristine FEX main `71afe476751deac24adabd1adb575fd2337b6e0a` split one generated Vulkan adapter into an x86-64 `DF_1_NODELETE` DSO while leaving `libvulkan-guest.so` ordinarily unloadable.

The selected function was `vkEnumerateInstanceVersion`.

Observed behavior:

1. wrapper generation 1 loaded;
2. native Vulkan PFN `H` was linked to resident adapter `T`;
3. the PFN call succeeded;
4. `libvulkan-guest.so` physically unmapped on `dlclose()`;
5. the resident bridge mapping remained;
6. wrapper generation 2 was forced to a different guest base;
7. native `H` remained the same;
8. resident `T` remained the same;
9. both a fresh generation-2 PFN and the retained generation-1 PFN succeeded.

The repaired v2 Actions workflow is green. This establishes that at least one real Vulkan `CallHostFunction` adapter can outlive the wrapper that originally requested it without requiring whole-wrapper residency.

## Current experiments

### Multi-signature dynamic-PFN test

The multi-signature probe obtains and retains three real Vulkan global PFNs with different signatures:

- `vkEnumerateInstanceVersion`;
- `vkEnumerateInstanceLayerProperties`;
- `vkEnumerateInstanceExtensionProperties`.

The candidate resident bridge contains three distinct signature adapters. The wrapper remains unloadable. The probe requires:

- zero guest Vulkan-wrapper mappings after real `dlclose()`;
- a surviving resident bridge mapping;
- all three retained PFNs to work while the wrapper is absent;
- a forced different-base wrapper reload;
- stable native `H` per function across generations;
- stable resident `T` per signature across generations;
- all new and retained-old PFNs to remain callable.

The first workflow attempt did not execute the experiment because recursive checkout hit transient GitHub HTTP 500 errors. An unchanged rerun was started so infrastructure failure is not confused with experimental failure.

Probe source: `fex_vulkan_multisig_pfn_unload_probe.c`.

### Bidirectional real Vulkan/X11 callback test

This experiment is deliberately stronger than the whole-wrapper NODELETE callback control.

The ordinary guest Vulkan wrapper remains physically unloadable. A small resident bridge DSO contains:

- the guest-to-host `CallHostFunction` adapter for `vkGetPhysicalDeviceXlibPresentationSupportKHR`;
- `CallbackUnpack<decltype(XSync)>::Unpack`;
- `CallbackUnpack<decltype(XGetVisualInfo)>::Unpack`;
- `CallbackUnpack<decltype(XDisplayString)>::Unpack`.

The actual guest callback targets remain in a normal guest `libX11.so.6` stub. Vulkan `OnInit()` installs host trampolines with:

```text
GuestTarget   = address in guest libX11
GuestUnpacker = address in resident bridge runtime
```

The probe creates a real Vulkan instance with Xlib WSI under llvmpipe, obtains a real `vkGetPhysicalDeviceXlibPresentationSupportKHR` PFN, calls it once, physically unloads the guest Vulkan wrapper, verifies the bridge and guest X11 remain mapped, and invokes the retained PFN again. Success requires the post-unload host call to re-enter guest `XSync` and `XDisplayString` through the resident unpackers while the Vulkan wrapper has zero mappings.

Probe source: `fex_vulkan_split_x11_callback_probe.c`.

## What success would prove

If both current experiments pass, the evidence supports this narrower ownership rule:

> Immutable generated signature adapters should not be owned by a guest wrapper DSO merely because that DSO caused their instantiation.

For the tested paths, the natural lifetime is process/FEX-thunk-runtime lifetime.

That would remove the executable-UAF mechanism without requiring the full machinery needed to safely reclaim these adapters on every physical wrapper unload.

It would not prove that all thunk state should be process-resident.

## What remains generation-owned or otherwise stateful

A split runtime must not turn into a blanket rule that every guest address is immortal. Examples requiring separate reasoning include:

- actual guest callback targets whose owner can unload;
- per-instance or per-device state;
- wrapper constructors/destructors and loader-visible lifecycle;
- library namespace semantics;
- stateful custom repacking helpers;
- any bridge whose behavior closes over mutable wrapper-generation state.

For those cases, generation identity, explicit revocation, owner claims, quiescence, or another lifetime protocol may still be required.

## Relationship to full physical-unload reclamation

Generic experiments have separately demonstrated that true reclamation is a distributed protocol, not a map erase:

- replacing an `H -> T` registry entry without cache invalidation is insufficient;
- invalidation must cover every FEX thread;
- invalidation cannot revoke execution already committed to an old target;
- address reuse creates ABA and can turn a crash into silent cross-generation execution;
- failed `munmap()` requires transactional prepare/commit/abort behavior;
- one native `H` can have multiple simultaneous live guest owner claims.

The split-runtime contract is attractive precisely because immutable signature adapters may not need to participate in that reclamation protocol at all.

## Product-design question

If the signature-only model holds broadly, the clean architecture may be a process-owned FEX guest bridge runtime rather than a per-library `*-bridge.so` policy. Such a runtime could potentially provide stable `CallHostFunction<signature>` and `CallbackUnpack<signature>` code to multiple thunk libraries.

Before making that leap, experiments should establish:

1. several unrelated signatures survive real wrapper unload/reload;
2. both guest-to-host and host-to-guest directions survive with only adapter code resident;
3. identical signature hashes emitted by different thunk libraries are semantically interchangeable in practice;
4. namespace behavior does not require per-wrapper adapter identity;
5. bridge code has no hidden dependencies on wrapper-local TLS, static data, destructors, or relocation lifetime;
6. code-size and resident-memory cost are measured for a realistic cross-library signature set.

The central distinction for future work is:

```text
bridge executable identity != wrapper DSO identity
```

unless a specific bridge is proven to carry wrapper-generation state.
