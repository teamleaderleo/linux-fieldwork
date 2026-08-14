# Resident guest bridge proposal — 2026-08-14

## Working deployment model

Use one small process-resident guest bridge DSO per thunk library that publishes guest executable addresses outside the lifetime of its ordinary guest wrapper.

The ordinary guest wrapper remains unloadable. The resident DSO owns only executable bridge code that may be retained by FEX/native state after wrapper `dlclose`.

This is deliberately **per library, per escaped bridge family**, not a process-wide immortal thunk blob.

Examples:

- Vulkan: dynamic PFN invokers plus persistent X11 callback unpackers.
- GL: dynamic PFN invokers, persistent X11 callback unpackers, and any ordinary wrapper-local executable callback target (the allocator target found by the GL experiment).
- CUDA: dynamic PFN invokers plus nested/deferred callback unpackers generated from callback-bearing structs.
- DRM: generated nested callback-member unpackers.
- Wayland: its custom protocol-signature listener unpackers; wrapper-owned proxy bookkeeping and callback-table heap storage do not need to move.

## Generic generator responsibility

Thunkgen should be able to emit a bridge-only guest output alongside its ordinary guest output.

The bridge-only output should contain only executable artifacts that may escape wrapper lifetime:

1. guest callers used as native-PFN CustomIR targets;
2. guest callback unpackers that host trampolines may retain;
3. symbol/accessor metadata needed by the unloadable wrapper to request those resident entrypoints.

It should not contain ordinary API packers (`fexfn_pack_*`) or wrapper state.

The direct `-guest-bridge` research output has already demonstrated this seam with real Vulkan unload/reload.

## Role provenance is required

A function-pointer signature is not sufficient to decide which bridge artifacts to instantiate.

GL exposed a 23-argument signature that is needed as an indirect caller but is not a callback unpacker. Treating every signature as both roles caused an invalid `CallbackUnpack` instantiation.

Thunkgen analysis already knows provenance. The bridge output therefore needs to preserve roles such as:

- indirect guest caller;
- ordinary callback parameter;
- nested `callback_member`;
- explicitly requested/custom callback family.

Deduplication may still happen by canonical signature inside a role, but role information must not be discarded before code generation.

## Library-specific responsibility

The generic generator cannot infer every escaped executable address.

Library-specific code remains appropriate when the API creates executable lifetime relationships outside normal function-pointer annotations. Examples:

- GL's allocator callback target;
- Wayland's protocol-signature-dependent listener trampoline finalization and special `wl_array` relocation path.

The rule for these hooks is simple: if native/FEX state can call a guest executable address after the ordinary wrapper can unload, that executable target belongs in the resident bridge (or must be routed through a resident entrypoint).

## Current evidence

### Vulkan

Real unload and moved reload succeed with an unloadable wrapper and a NODELETE bridge. Retained native PFNs continue to dispatch through resident guest invokers. Persistent X11 callback routing also survives wrapper unload.

### GL

Real `glXGetProcAddress("glGetError")` survives physical wrapper unload and moved reload with a resident bridge. GLX/X11 callback entry also survives. The experiment additionally showed that an ordinary wrapper-local callback target (`malloc_wrapper`) must move when its address escapes.

### DRM

The generator `callback_member` prototype successfully copies a callback-bearing input structure, substitutes a generated host trampoline in the copy, and executes all three DRM callback signatures through the resident bridge. This proves nested callback generation, but not yet a moved-wrapper retained-callback A/B.

### Direct thunkgen bridge output

The `-guest-bridge` research output is preferable to reverse-parsing generated guest C++. Real Vulkan passed hold/close/reload with the direct bridge output, and the generated bridge contained bridge thunks/symbol metadata while excluding ordinary API packers.

### CUDA retained callback A/B — important negative result

Run `31787029666` finally reached the intended moved-wrapper runtime discriminator.

Observed matrix:

```
native_deferred=0
local_unpacker=139
resident_unpacker=139
```

Both variants:

- registered the callback successfully in generation 1;
- physically unloaded the generation-1 CUDA wrapper;
- reserved its old mappings;
- loaded generation 2 at a different guest address;
- invoked only the previously retained callback registration from native code;
- retained the same host trampoline address (`0x7ffff7e5b000`);
- faulted before the guest callback body executed.

Therefore the current CUDA resident transform **does not yet move/rebind the actual guest executable target retained inside that host trampoline**. Matching the normal/generated signature set (364/364) and building a NODELETE sidecar are not sufficient proof that a nested callback is resident.

This is a falsifier of the implementation, not of the overall resident-bridge architecture. The next CUDA task is to trace the trampoline's final `GuestUnpacker` address and prove whether it points into the wrapper or bridge.

## Wayland discriminator

Wayland is a custom callback-family test rather than an indirect-PFN test.

The current experiment uses a synthetic proxy with one `"u"` event and a native thread that invokes the same finalized FEX listener trampoline before and after wrapper `dlclose`.

Required control:

- pre-close native-thread callback reaches guest.

Lifetime discriminator:

- local unpacker should fail after physical wrapper unload;
- resident `"u"` unpacker should still reach guest.

If the one-signature A/B succeeds, expanding the resident dispatcher across Wayland's existing finite protocol signature switch is mechanical. If it does not, inspect the retained trampoline's concrete `GuestUnpacker` target exactly as with CUDA before broadening the sidecar.

## What this proposal does not claim

This does not make arbitrary concurrent `dlclose` safe. Cache invalidation is not execution quiescence. If FEX intends supported concurrent retirement while threads may already be executing a retiring bridge, an execution lease/epoch/grace mechanism is a separate requirement.

This also does not solve native-PFN alias ownership or incompatible ABI collapse. A robust later PFN registry may still need owner/generation identity and alias stacks.

## Near-term sequence

1. Trace CUDA retained trampoline metadata and identify its actual `GuestUnpacker` mapping in local and resident variants.
2. Fix the resident CUDA path at that exact target, then rerun the moved-wrapper retained-registration-only A/B.
3. Finish the Wayland one-signature A/B and trace its concrete unpacker on either unexpected outcome.
4. Consolidate direct thunkgen bridge output with role provenance (`indirect`, callback parameter, `callback_member`, custom callback family).
5. Only after these pass, generalize the per-library CMake/build pattern and measure bridge residency/RSS cost versus whole-wrapper NODELETE.
