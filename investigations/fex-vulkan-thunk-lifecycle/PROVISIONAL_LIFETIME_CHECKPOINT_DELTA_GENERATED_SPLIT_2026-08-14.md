# Provisional lifetime checkpoint delta — generated split bridge

Date: 2026-08-14

This updates [`PROVISIONAL_LIFETIME_CHECKPOINT_2026-08-14.md`](./PROVISIONAL_LIFETIME_CHECKPOINT_2026-08-14.md). The older checkpoint is intentionally retained as history rather than rewritten.

## What changed

Two candidate directions received decisive new evidence.

### Runtime base-only NODELETE promotion was falsified as a general policy

Promoting only the base loader-namespace Vulkan wrapper with `RTLD_NOLOAD | RTLD_NODELETE` looked attractive because it avoided ELF-wide NODELETE retention of `dlmopen(LM_ID_NEWLM, ...)` copies.

The dynamic-PFN test survived, but that was not a complete discriminator: FEX-2608 keeps the existing H->T CustomIR route when the same native H is registered again with different guest target data.

The host->guest callback adversary failed. A NEWLM Vulkan wrapper republished X11 callback trampolines/unpackers into persistent host-side Vulkan/X11 state, then physically unloaded. The original base Vulkan Xlib PFN subsequently faulted when that persistent host helper attempted to use the dead NEWLM guest callback bridge.

Therefore base-only self-promotion is demoted. The negative runtime is retained in [`RUNTIME_NODELETE_PROMOTION_NEWLM_CALLBACK_NEGATIVE_2026-08-14.md`](./RUNTIME_NODELETE_PROMOTION_NEWLM_CALLBACK_NEGATIVE_2026-08-14.md).

### The split resident bridge moved from model to real generated Vulkan runtime

A thunkgen-produced `libfex-vulkan-bridge.so` now owns selected escaped bridge code while ordinary `libvulkan-guest.so` remains physically unloadable.

Real hosted ARM64/Lavapipe results now prove:

1. **Dynamic PFN after wrapper unmap** — `vkEnumerateInstanceVersion` remains callable after `libvulkan-guest.so` GIPA is physically unmapped. See [`GENERATED_VULKAN_SPLIT_BRIDGE_PFN_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_BRIDGE_PFN_RUNTIME_2026-08-14.md).
2. **Host->guest callback after wrapper unmap** — retained `vkGetPhysicalDeviceXlibPresentationSupportKHR` still enters native Vulkan and the persistent host X11 manager successfully invokes guest `XSync` / `XDisplayString` after the ordinary wrapper is gone. See [`GENERATED_VULKAN_SPLIT_BRIDGE_X11_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_BRIDGE_X11_RUNTIME_2026-08-14.md).
3. **Forced moved wrapper reload** — all former generation-1 wrapper mappings are reserved, generation 2 moves, native H remains identical, newly reacquired H works, and the old retained H also continues to work through the same resident bridge. See [`GENERATED_VULKAN_SPLIT_MOVED_RELOAD_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_MOVED_RELOAD_RUNTIME_2026-08-14.md).
4. **Bridge-only function-type generation** — thunkgen can emit required indirect signature thunks directly from `fex_gen_type<function-type>` with no fake companion API symbols. See [`GENERATED_BRIDGE_EXPLICIT_TYPE_BUILD_2026-08-14.md`](./GENERATED_BRIDGE_EXPLICIT_TYPE_BUILD_2026-08-14.md).

## Updated ranking

### Near-term smallest containment

**Whole shared-wrapper NODELETE** remains the smallest implementation change with strong real Vulkan evidence. It is still the practical containment candidate if process-lifetime guest thunk wrappers are an acceptable product contract.

### Strongest demonstrated unload-preserving architecture

**Per-library process-resident bridge + unloadable wrapper** is now the strongest demonstrated architecture when physical wrapper unload/reset is desired.

Its key ownership rule is:

> Executable guest bridge code whose address FEX intentionally publishes into process-owned or longer-lived host state must outlive the ordinary wrapper generation that performed the publication.

That includes:

- runtime host-function-pointer `CallHostFunction<signature>` adapters;
- generated or handwritten guest callback unpackers whose addresses enter host trampolines/helpers;
- library-specific bridge helpers whose executable addresses escape wrapper lifetime.

Ordinary API wrapper code can remain generation-owned and physically unload under normal application lifetime rules.

### Full bridge reclamation

**Owner/generation + revocation + execution lease/hazard/grace period** remains necessary only if FEX also requires reclamation of the escaped bridge executable code itself, or another FEX-created generation-owned executable target is allowed to outlive ordinary wrapper API lifetime.

The earlier 15/15 lease model remains valid for that stronger requirement. It is no longer the minimum mechanism required merely to reclaim the ordinary wrapper.

## Why the split changes the concurrency argument

The forced in-flight failure established that registry/cache retirement cannot revoke a host-code pointer that another emulation thread already selected before wrapper unmap.

The split design does not try to revoke that selected bridge pointer. It changes its owner:

```text
old design:
selected host code -> guest wrapper bridge bytes -> wrapper unmaps -> fault

split design:
selected host code -> process-resident bridge bytes -> wrapper unmaps -> selected bridge still valid
```

That is a lifetime fix at the publication boundary rather than a synchronization fix around every dynamic-PFN call.

## Generator boundary now looks tractable

Thunkgen already isolates the relevant pieces:

- `thunked_funcptrs` is the set used to emit signature-specific `MAKE_CALLBACK_THUNK` guest->host adapters;
- automatic guest callback parameters are wrapped through `AllocateHostTrampolineForGuestFunction`, which currently passes a wrapper-local `CallbackUnpack<T>::Unpack` address into FEX.

A production per-library bridge generator therefore needs to:

1. emit the library's indirect signature thunks into a resident bridge DSO;
2. expose stable resident invoker addresses by function/name or bridge identity;
3. make ordinary generated packers obtain resident callback-unpacker addresses rather than instantiating escaping unpackers in the unloadable wrapper;
4. keep custom library callback helpers resident where their addresses escape.

A separate third thunkgen output mode is plausible because the existing guest generation block already emits the signature-thunk loop separately from normal API packers/exports.

## Why per-library first

Thunkgen's callback hash is derived from canonical C function signature, but generated host wrappers can also apply per-parameter annotations such as passthrough or assumed-compatible layout.

Therefore textual signature alone should not yet be treated as a proven cross-library ABI/bridge identity.

A per-library resident sidecar preserves the original library's annotation context and is the safer first general implementation. Process-global cross-library signature deduplication can be considered after an explicit annotation-equivalence audit.

## What would disprove or demote the split direction

Useful counterexamples include:

1. a real generated callback or dynamic-PFN bridge whose executable dependency still remains in the unloadable wrapper after the proposed generator split;
2. a library-specific custom helper whose required mutable state cannot safely live in a resident bridge extension;
3. unacceptable bridge residency/metadata footprint once all signatures are generated;
4. a correctness dependency on bridge executable reclamation, which would restore the lease/hazard requirement;
5. a loader-namespace model requiring genuinely independent H/bridge identities rather than FEX's current process-global thunk state.

The design remains provisional and should be revised when such evidence appears.

All implementation and CI work referenced here remains in owned repositories/forks. Upstream FEX remains untouched.
