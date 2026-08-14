# Generated Vulkan split resident bridge — real PFN runtime

Date: 2026-08-14

## Result

A real thunkgen-produced Vulkan guest bridge can remain process-resident while the ordinary generated Vulkan guest wrapper physically unloads, and a retained real Vulkan dynamic PFN continues to call native ARM64 Lavapipe successfully afterward.

This is the first generated-Vulkan integration proof of the split resident bridge design. It does not modify FEX core lifetime handling.

## Owned-fork carrier

Repository: `teamleaderleo/FEX`

Branch: `diagnostic/generated-vulkan-split-bridge`

Reviewed stock base: `71afe476751deac24adabd1adb575fd2337b6e0a`

Workflow head: `b909e95682e77ae91c53550e3e42e6f30165f8bb`

Workflow: `.github/workflows/generated-vulkan-split-bridge-arm64.yml`

Run: `31777233297`

Job: `94695132100`

Artifact: `generated-vulkan-split-bridge-31777233297`

Artifact ID: `9210414273`

Artifact zip SHA-256:

```text
d4b11e744da80c8ee43201ebd762527f85e774138ccb09e1657e3c9320491d39
```

## Prototype shape

The ordinary generated `libvulkan-guest.so` remains unloadable.

A small generated guest DSO, `libfex-vulkan-bridge.so`, owns the escaped executable bridge code and is linked `NODELETE`.

For this first discriminator only one real dynamic Vulkan signature is migrated:

```text
vkEnumerateInstanceVersion : VkResult(uint32_t*)
```

Thunkgen emits the signature-specific special callback thunk into the resident sidecar. The sidecar returns the address of the exact corresponding `CallHostFunction<signature>` instantiation. The Vulkan wrapper's `HostPtrInvokers` map uses that resident address for `vkEnumerateInstanceVersion`.

The sidecar also already exports resident generic X11 callback unpackers for `XSync`, `XGetVisualInfo`, and `XDisplayString`; their full real callback path is a separate follow-up discriminator.

No ordinary C forwarding wrapper is inserted around `CallHostFunction`: the native H value reaches the selected guest adapter through FEX's custom r11/mm0 ABI, so the published address must be the actual adapter implementation.

## ELF lifetime proof

The ordinary Vulkan wrapper has its normal SONAME and a dependency on the resident bridge:

```text
NEEDED: libfex-vulkan-bridge.so
SONAME: libvulkan.so.1
```

It has **no** `FLAGS_1: NODELETE`.

The bridge DSO has:

```text
SONAME: libfex-vulkan-bridge.so
FLAGS_1: NODELETE
```

Thus wrapper residency is not responsible for the passing result.

## Runtime trace

FEX links the actual native Vulkan PFN to an invoker in the resident bridge:

```text
Linking address 0x7ffff76c80f4 to host invoker 0x7ffff7e712e0
```

Before close:

```text
SPLIT_BEFORE gipa=0x7ffff7ea2360 H=0x7ffff76c80f4 version=4206867 bridge_maps=5
```

After ordinary guest `dlclose(libvulkan.so.1)`:

```text
SPLIT_AFTER_CLOSE gipa_mapped=0 bridge_maps=5
```

The guest `vkGetInstanceProcAddr` address was therefore physically unmapped, while the resident bridge remained mapped.

The exact retained native PFN is then called again:

```text
SPLIT_RETAINED_PFN result=0 version=4206867
GENERATED_VULKAN_SPLIT_PFN_OK
```

Process exit: `0`.

## Meaning

This validates the core split-runtime ownership claim on a real generated Vulkan H->T path:

```text
native Vulkan PFN H
    -> process-global FEX synthetic dispatch
    -> resident generated bridge adapter Tbridge
    -> native Vulkan special thunk
```

The wrapper that originally performed name lookup and bridge publication can disappear without invalidating Tbridge.

This directly avoids the already-proven selected-before-wrapper-unmap race for wrapper-owned bridge bytes: an execution path selected into the resident adapter cannot become invalid merely because the ordinary wrapper is reclaimed.

## What remains open

This run migrated only one dynamic Vulkan function signature. It does not yet prove:

- the real retained Vulkan/X11 host->guest callback direction after wrapper physical unload;
- all Vulkan dynamic PFN signatures;
- moved wrapper reload with the generated sidecar;
- generic thunkgen integration rather than the current Vulkan-specific companion target;
- cross-library signature deduplication.

The X11 callback unpackers are already resident in the sidecar, but the Vulkan Xlib PFN's own guest->host adapter must also move there before the post-unload callback test is valid.

A further design caveat is that thunkgen's special callback hash is based on C function signature, while generated host wrappers also carry per-parameter thunk annotations. A future process-global deduplicated bridge runtime must prove annotation-equivalent sharing or use a richer bridge identity. A per-library resident sidecar does not have that ambiguity.

## Current implication

Whole-wrapper NODELETE remains the smallest near-term containment.

The split resident bridge has now advanced from synthetic/runtime architecture evidence to a real generated-Vulkan proof and is the strongest demonstrated direction when physical wrapper unload/reset semantics are desired.

All code and CI work here stayed on owned repositories/forks. No upstream FEX interaction occurred.
