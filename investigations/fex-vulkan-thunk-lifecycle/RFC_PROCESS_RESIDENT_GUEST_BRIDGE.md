# RFC: Process-resident guest bridge runtime

Status: Exploratory design with successful Vulkan prototypes

Date: 2026-08-14

## Summary

This proposal gives immutable generated thunk bridge code process lifetime while preserving ordinary loader lifetime for public guest wrapper DSOs.

The model is:

```text
process-lived private guest bridge runtime
    generated signature adapters
    generated callback unpackers

ordinary guest wrapper DSO
    API entrypoints
    constructors/destructors
    mutable wrapper state
    custom stateful repacking

owner-lived guest callback target
    application/library callback function
```

The key claim is narrow:

> Signature-only executable bridge identity can be broader than wrapper DSO identity.

Real Vulkan experiments now support that claim for multiple guest-to-host signatures and for a bidirectional Vulkan/X11 path.

## Motivation

Current thunk generation places several kinds of executable adapters in the guest wrapper that happens to request them. FEX or native libraries can retain addresses to those adapters after the wrapper closes.

Whole-wrapper NODELETE repairs the lifetime mismatch by extending every wrapper mapping. Full physical-unload reclamation repairs it by revoking and invalidating every escaped address safely.

A third option is available for immutable generated adapters: give the adapter itself a process-lived owner while leaving the public wrapper unloadable.

## Evidence

### Three independent Vulkan PFN signatures

A resident bridge successfully hosted adapters for:

- `vkEnumerateInstanceVersion`;
- `vkEnumerateInstanceLayerProperties`;
- `vkEnumerateInstanceExtensionProperties`.

All three retained native PFNs remained callable with zero guest Vulkan-wrapper mappings. The wrapper was then forced to reload at a different base while the native PFNs and resident adapter addresses stayed stable. Both fresh and retained-old PFNs succeeded.

### Bidirectional Vulkan/X11 path

A resident bridge successfully hosted:

- the guest-to-host adapter for `vkGetPhysicalDeviceXlibPresentationSupportKHR`;
- the callback unpackers for `XSync`, `XGetVisualInfo`, and `XDisplayString`.

The ordinary Vulkan wrapper physically unloaded to zero mappings. The retained native Vulkan PFN was then called again and re-entered the still-owned guest X11 targets through the resident unpackers. The guest process exited 0.

### Generator identity already favors signature ownership

Thunkgen callback identity is derived from a canonical callback signature hash. Library identity is absent from that hash. Equal callback signatures are already deduplicated within generated output.

The current placement model therefore mixes two concepts:

- signature identity;
- wrapper-image lifetime.

This RFC proposes aligning lifetime with the first concept when the generated code is immutable and independent of wrapper state.

## Proposed component

Introduce a private guest bridge runtime for each supported guest bitness.

Working names could be:

```text
libfex-thunk-bridge.so
libfex-thunk-bridge-32.so
```

The public name is unimportant; it should remain an internal FEX component rather than an application-facing ABI.

The bridge is linked with `DF_1_NODELETE` or otherwise given process lifetime by FEX.

## Generated bridge contents

Thunkgen should emit a deduplicated set of process-lived bridge primitives required by enabled thunk libraries.

### Guest-to-host dynamic adapters

For each required signature:

```text
CallHostFunction<fexthunks_invoke_callback<signature>, Result, Args...>
```

plus its signature-specific special thunk marker.

Wrappers obtain the stable adapter address when binding a native PFN:

```text
H -> bridge_adapter(signature)
```

### Host-to-guest callback unpackers

For each required signature:

```text
CallbackUnpack<signature>::Unpack
```

Wrappers pass the stable unpacker address when asking FEX for a host callback trampoline:

```text
GuestUnpacker = bridge_unpacker(signature)
GuestTarget   = owner-specific guest callback target
```

The bridge owns only the unpacker. The target retains its original owner relationship.

## Wrapper interface

A wrapper needs a generated way to resolve stable bridge addresses.

Possible generated forms:

```cpp
uintptr_t GetHostCallerBridge(SignatureId id);
uintptr_t GetCallbackUnpackerBridge(SignatureId id);
```

or direct generated symbols:

```cpp
fex_bridge_call_<signature_hash>
fex_bridge_unpack_<signature_hash>
```

Direct symbols are simpler for link-time dependency tracking. A generated lookup table may reduce wrapper symbol volume and ease deduplication.

The choice should preserve one invariant: wrappers never synthesize process-lived adapter addresses from wrapper-local code.

## Packaging and loading

FEX's thunk database already supports dependency declarations and recursively overlays dependencies from the private GuestThunks directory.

That suggests a clean deployment model:

1. install the private bridge beside guest thunks;
2. add it as a dependency for wrappers that require process-lived bridge code;
3. let the existing thunk overlay/dependency path make the bridge visible to the guest loader;
4. keep the bridge internal to FEX rather than installing it as a normal rootfs library.

This should be tested before relying on `$ORIGIN` or ad hoc `dlopen()` calls in wrappers.

## Ownership classification

Every generated or handwritten guest executable helper should fall into one of three categories.

### Category A: signature-only immutable bridge

Examples currently supported by experiments:

- `CallHostFunction<signature>` dynamic PFN adapters;
- `CallbackUnpack<signature>::Unpack`.

Candidate owner: process-lived bridge runtime.

### Category B: wrapper-generation helper

Examples:

- helper reads mutable wrapper static data;
- helper depends on wrapper TLS;
- helper closes over per-instance/device state;
- helper relies on wrapper constructor/destructor ordering;
- helper uses relocations into wrapper-local objects.

Owner: wrapper generation.

If an address in this category escapes, physical unload requires explicit revocation/quiescence, or the wrapper needs a pinning policy.

### Category C: external guest callback target

Examples:

- application callback;
- guest X11 callback target;
- callback belonging to another unloadable guest library.

Owner: callback target's DSO/application lifetime.

A process-lived unpacker does not change that ownership. Persistent native users need unregister/revocation, target pinning, generation tracking, or a stable rejecting indirection.

## State audit requirement

Before moving a helper into the bridge, verify:

- no wrapper-local TLS access;
- no wrapper-local mutable globals;
- no destructor-owned resource;
- no direct relocation to unloadable wrapper code/data;
- no hidden dependence on wrapper load order;
- ABI determined by the canonical signature and guest bitness;
- special thunk hash semantics match the host thunk dispatch already registered in FEX.

The allocator/type-level Vulkan work is a useful warning case: custom callback handling can carry API semantics beyond a generic signature adapter.

## Cross-library deduplication

The strongest version of this design uses one adapter per canonical signature across all thunk libraries in a process.

That follows naturally from current signature hashing, but still needs a real cross-library proof.

Required experiment:

1. choose two unrelated thunk libraries that emit the same canonical callback signature;
2. bind both through one resident bridge adapter/unpacker;
3. unload/reload each wrapper independently;
4. confirm the same resident code address is semantically interchangeable;
5. exercise both directions where possible.

Until this passes, an implementation can use one private bridge DSO per thunk family while retaining the same lifetime model.

## Namespace behavior

`DF_1_NODELETE` applies per loader namespace. A private bridge loaded independently into many disposable `dlmopen()` namespaces can accumulate resident copies.

Open design choices:

### Per-namespace bridge

Simple loader semantics. Each namespace gets a bridge copy and retains it.

Cost: disposable namespace accumulation.

### Base-namespace bridge for ordinary application use

Use the bridge only in the main namespace. Other namespaces retain wrapper-local adapters or another explicit policy.

Cost: two paths and more classification logic.

### FEX-owned executable bridge outside guest loader DSO lifetime

FEX creates stable guest executable bridge memory directly and shares addresses across namespaces.

This could eliminate DSO namespace pinning, but it becomes a larger runtime/JIT-adjacent feature and needs ABI, unwind, security, and executable-memory review.

Recommendation for the first implementation: keep the DSO model and document namespace scope. Revisit only if real applications demonstrate a namespace regression.

## 32-bit support

The bridge must preserve FEX's guest thunk ABI differences between 64-bit and 32-bit modes, including the host-address carrier convention used by `CallHostFunction`.

The bridge should therefore be generated separately per bitness even if the canonical signature registry is shared conceptually.

Required tests:

- at least one 32-bit dynamic host-function adapter;
- at least one 32-bit callback unpacker;
- load/close/reload with stable bridge addresses;
- interaction with the existing 32-bit Wayland path.

## Relation to host thunk registration

The bridge does not need a second host library registration for the tested callback-special-thunk mechanism.

The guest special thunk embeds the signature hash. FEX's process-owned host thunk dispatch already knows the registered hash and routes it to the host packer. The successful split Vulkan experiments validate that a byte-equivalent special thunk can live in another guest DSO and still hit the existing host dispatch.

## Relation to JIT/cache lifetime

For H-to-T routing where `T` lives in the process bridge, wrapper unload no longer invalidates `T`.

That removes the confirmed executable-UAF trigger for that class without requiring immediate CustomIR/JIT retirement.

JIT/cache invalidation remains relevant for:

- mappings to genuinely reclaimable guest targets;
- stale callback targets;
- any future feature that retargets the same host address to generation-owned executable code.

## Persistent callback targets

The bridge handles stable unpacker code. Actual targets remain owner-governed.

A general persistent-callback helper could pair:

```text
process-lived unpacker
owner token / generation
current target
revoked flag
```

The host trampoline would call a stable guest/FEX indirection that validates the owner before reaching the target.

That is a separate RFC-sized problem. The current DRM `drmSetServerInfo` experiments should inform it.

## Migration plan

### Phase 1: generator proof

Teach thunkgen to emit a bridge artifact for Vulkan with the signatures already proven experimentally.

Use the normal thunk dependency mechanism to install/load it.

Keep Vulkan NODELETE during bring-up as a safety belt, then add a test that fails if the wrapper still contributes escaped adapter addresses.

### Phase 2: Vulkan complete classification

Classify every dynamic PFN adapter and persistent callback unpacker.

Move Category A code to the bridge.

Leave Category B code in the wrapper and document its lifetime.

Remove Vulkan NODELETE once the audit and physical-unload tests are green.

### Phase 3: GL, CUDA, Wayland

Repeat the classification and migrate signature-only bridge code.

Use common generator machinery instead of library-specific handwritten bridge loaders.

### Phase 4: cross-library deduplication

After real proof, collapse duplicate canonical signatures into one process bridge instance per bitness.

## Acceptance criteria

A bridge implementation should demonstrate:

- public wrapper has ordinary unload semantics;
- exact wrapper mappings reach zero after close;
- retained host PFNs remain callable while wrapper is absent;
- callback unpackers remain callable while wrapper is absent;
- forced moved reload preserves stable bridge addresses;
- several materially different signatures pass;
- actual callback target unload is either rejected safely or governed by a separate owner policy;
- existing `glxinfo` and `vulkaninfo` thunk functional tests pass;
- 32-bit path passes;
- resident code size is measured;
- namespace behavior is documented and tested.

## Open questions

1. One global bridge per bitness or one bridge per thunk family during initial rollout?
2. Generated direct symbols or generated lookup table?
3. How should target-owner revocation integrate with existing host trampoline caching?
4. Can the bridge remain effectively libc-free to reduce dependency and namespace behavior?
5. Which custom Vulkan allocator/repacking helpers qualify as Category B?
6. Which other thunk libraries already have persistent host-held callback addresses?
7. Should thunkgen emit an explicit lifetime annotation in generated metadata so audits become machine-checkable?

## Recommendation

Proceed with a first-class generated bridge prototype after the selective NODELETE containment is review-ready.

The experiments now justify treating process-lived immutable signature adapters as a product design candidate. The implementation should stay deliberately narrow until cross-library reuse, 32-bit behavior, namespace scope, and stateful-helper classification have their own proofs.
