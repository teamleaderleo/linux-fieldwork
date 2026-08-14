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

The generator `callback_member` prototype successfully copies a callback-bearing input structure, substitutes a generated host trampoline in the copy, and executes all three DRM callback signatures through the resident bridge. This proves nested callback generation; CUDA now supplies the moved-wrapper retained-callback proof for the same generated callback-member class.

### Direct thunkgen bridge output

The `-guest-bridge` research output is preferable to reverse-parsing generated guest C++. Real Vulkan passed hold/close/reload with the direct bridge output, and the generated bridge contained bridge thunks/symbol metadata while excluding ordinary API packers.

### CUDA retained callback A/B — decisive ownership result

The earlier sequential same-job run `31787029666` reported `local=139, resident=139`. That result is superseded by isolated-run traces; the exact source of the earlier harness contamination remains unspecified.

Final isolated A/B: run `31788360618`.

Both local and resident arms first execute the exact generated nested callback successfully while generation 1 is mapped:

```
MARK launch1-enter pre-close-control
CUDA_RETAINED_CALLBACK count=1 user=0x12345678
MARK launch1-return rc=0 callbacks=1
```

Then generation 1 is physically unloaded, all five old wrapper mappings are reserved, generation 2 is forced to a different guest address, and generation 2 invokes only the generation-1 retained native registration.

Local arm:

```
GuestUnpacker=0x7ffff7ea8040
GuestUnpacker_in_retired_wrapper=1
post-move retained callback -> exit 139
```

Resident arm:

```
GuestUnpacker=0x7ffff7e75610
GuestUnpacker_in_retired_wrapper=0
CUDA_RETAINED_CALLBACK count=2 user=0x12345678
post-move retained callback -> exit 0
```

This directly proves that the resident CUDA transform changes the concrete guest executable unpacker embedded in FEX's host trampoline. The local unpacker is retired with generation 1; the resident unpacker remains executable and the old native registration survives a moved wrapper reload without re-registration.

### Wayland first listener A/B — invalid lifetime discriminator

Run `31786909159` built both the unloadable local wrapper and the resident-`"u"` sidecar candidate successfully, but both runtime arms exited 139 **before the pre-close callback control completed**:

```
local=139
resident=139
```

The only guest-side receipt before the crash was the loaded `wl_proxy_add_listener` address. Neither arm printed the expected first guest callback (`value=41`) or the `WAYLAND_PRE_CLOSE` marker.

Therefore this run does not test unload lifetime. The arbitrary native `std::thread` callback path is not an acceptable control until it can call the guest successfully while the wrapper is still mapped. FEX's callback path explicitly depends on registered per-thread thunk state, so an arbitrary native thread is a confounder.

The revised Wayland discriminator avoids that confounder:

1. generation 1 registers a `"u"` listener and the host thunk retains the finalized FEX trampoline;
2. while generation 1 is still loaded, a normal thunked diagnostic trigger is called synchronously from the guest and invokes the retained trampoline; this must deliver `value=41`;
3. close generation 1, reserve its old mappings, and force generation 2 to a different guest load address;
4. generation 2 calls only the diagnostic trigger — it must **not** register the listener again;
5. the host thunk invokes the generation-1 retained trampoline synchronously on the existing FEX thread, delivering `value=42` only if the embedded guest unpacker remains executable.

This mirrors the now-validated CUDA retained-registration-only test and removes arbitrary host-thread attachment from the lifetime question.

## Callback trampoline anatomy

FEX host-to-guest callback trampolines embed four fields:

```
HostPacker
CallCallback
GuestUnpacker
GuestTarget
```

The trampoline cache key is `(GuestUnpacker, GuestTarget)`. Guest-side allocation supplies `GuestUnpacker` and `GuestTarget`; host-side finalization supplies only `HostPacker` and does not rewrite the guest unpacker.

Consequently a resident callback design is only successful if the `GuestUnpacker` embedded **at allocation time** resolves to resident guest code. CUDA now directly validates this invariant.

## What this proposal does not claim

This does not make arbitrary concurrent `dlclose` safe. Cache invalidation is not execution quiescence. If FEX intends supported concurrent retirement while threads may already be executing a retiring bridge, an execution lease/epoch/grace mechanism is a separate requirement.

This also does not solve native-PFN alias ownership or incompatible ABI collapse. A robust later PFN registry may still need owner/generation identity and alias stacks.

## Near-term sequence

1. Finish the Wayland synchronous generation-1/register → trigger → unload/move → generation-2/trigger-only A/B.
2. Compile and validate direct thunkgen bridge role provenance (`needs_caller`, `needs_unpacker`) on GL and Vulkan; specifically prove GL caller-only signatures do not instantiate callback unpackers.
3. Fold generated `callback_member` registrations into that same role-aware bridge output and rerun the CUDA retained callback ownership A/B without the text extractor.
4. Generalize the per-library CMake/build pattern only after those gates are green.
5. Measure bridge residency/RSS cost versus whole-wrapper NODELETE.
