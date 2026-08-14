# Per-library resident bridge ownership inventory — 2026-08-14

This inventory is the current implementation-oriented view of the resident-bridge proposal. The unit of ownership is not “all thunk code” and not one process-global bridge. It is **the guest executable families from a particular thunk library that may escape the lifetime of that library's ordinary guest wrapper**.

| Library | Escaped executable family | Generic role | Current evidence | Resident scope |
|---|---|---|---|---|
| Vulkan | dynamic PFN invokers returned via `vkGet*ProcAddr` | caller | real close + moved reload passes | generated per-signature callers |
| Vulkan | persistent X11 callback unpackers | unpacker/custom | host→guest callback path survives wrapper unload | small fixed callback set |
| GL | dynamic PFN invokers returned via `glXGetProcAddress` | caller | real close + moved reload passes | 736 caller-only signatures in current generator analysis |
| GL | GLX/X11 callback unpackers | unpacker/custom | retained callback survives wrapper unload | small fixed callback set |
| GL | ordinary allocator callback target | custom escaped target | wrapper-local target failed until moved | one library-specific executable target |
| DRM | nested callback fields in `drmEventContext` | unpacker via `callback_member` | generated nested callbacks execute; caller input is copied | generated callback-member unpackers |
| CUDA | dynamic PFN invokers | caller | generator/signature path builds; PFN architecture matches Vulkan/GL | generated callers |
| CUDA | deferred nested callback in `CUDA_HOST_NODE_PARAMS` | unpacker via `callback_member` | isolated pre-close + moved-reload ownership A/B passes | generated callback-member unpacker |
| Wayland | runtime protocol listener signatures | custom unpacker family | retained-registration-only moved-reload A/B passes; full 41-signature 64-bit dispatcher builds and preserves `"u"` runtime proof | one per-library finite signature dispatcher |

## Generator ownership classes

The common generator should understand two orthogonal executable roles:

```
needs_caller
needs_unpacker
```

A canonical signature may require one or both. Current research evidence:

- stock GL: 736 caller-only signatures;
- stock Vulkan: 476 caller-only signatures;
- ordinary callback parameter: unpacker-only;
- nested `callback_member`: unpacker-only;
- same signature appearing as callback + indirect API: both after role OR-ing.

The resident companion should instantiate only the roles actually required. In particular, caller-only signatures must not instantiate `CallbackUnpack` merely because they share the same C++ function type representation.

## Library-specific hooks are intentional

Not every escaped executable address originates in a normal annotated function-pointer parameter. Library-specific resident helpers remain the right fit when lifetime is determined by API semantics that thunkgen cannot infer from the type alone.

Current examples:

- GL allocator callback target;
- Wayland runtime protocol-signature dispatcher.

For 32-bit Wayland, signatures containing `wl_array` (`"a"`, `"iia"`, `"uoa"`) use a special **host-side packer** (`CallGuestPtrWithWaylandArray`) selected during trampoline finalization. That packer relocates the host array onto guest stack memory and then calls the trampoline's existing `GuestUnpacker`. It is not a separate guest unpacker ownership class. The resident guest-unpacker rule remains the same; a future 32-bit test must validate the resident unpacker together with this process-lived host packer.

This is not a failure of the generic generator. The generator owns typed bridge primitives; the library owns the semantic fact that a particular executable target escapes.

## Runtime invariant for callbacks

For a host→guest callback that may survive wrapper unload, the decisive object is FEX's host trampoline metadata:

```
HostPacker
CallCallback
GuestUnpacker
GuestTarget
```

The resident boundary is correct only when the `GuestUnpacker` embedded at trampoline allocation time belongs to resident guest code. CUDA directly proves this with address-to-retired-mapping classification.

## Deployment proposal

For each affected thunk library:

1. build the ordinary guest wrapper normally and keep it unloadable;
2. build `libfex-<library>-bridge.so` (or equivalent library-local name) with `DF_1_NODELETE`;
3. make the wrapper depend on that companion only when it publishes escaped executable addresses;
4. route generated caller/unpacker allocation through direct thunkgen bridge/accessor output;
5. keep custom escaped targets in the same library-local companion;
6. do not put ordinary API packers, mutable wrapper state, loader state, or unrelated library code in the companion.

## Still outside this inventory

The companion split does not define:

- concurrent unload quiescence;
- native-PFN owner generations / alias stacks;
- incompatible ABI aliases resolving to one native H;
- retirement of the companion itself (the current model treats it as process-resident);
- 32-bit Wayland host-packer + resident-unpacker compatibility;
- the separate Vulkan pNext const-memory issue.
