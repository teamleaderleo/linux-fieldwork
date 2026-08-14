# Thunkgen resident bridge role contract — 2026-08-14

## Problem

The current research `-guest-bridge` emitter walks `thunked_funcptrs` as a flat set of canonical function-pointer signatures. That was sufficient to prove the Vulkan split, but it loses why a signature was registered.

GL demonstrated why this is wrong for a general emitter: a 23-argument signature was needed for an indirect guest call (native PFN -> guest caller), but the prototype also tried to instantiate callback-unpacker machinery for it. The callback path has different argument-packing constraints, so caller-only and unpacker-only roles cannot be inferred from signature shape.

## Analysis contract

Each function-pointer registration should carry two orthogonal requirements:

```
needs_caller
needs_unpacker
```

Registration rules:

| Source | needs_caller | needs_unpacker |
|---|---:|---:|
| explicit `fex_gen_type<function-pointer>` | 1 | 1 |
| ordinary callback parameter | 0 | 1 |
| generated nested `callback_member` | 0 | 1 |
| API in `indirect_guest_calls` namespace | 1 | 0 |
| explicit/custom library bridge request | as requested | as requested |

The explicit-type case remains conservative because existing interface files may use it for either direction.

When multiple registrations canonicalize to the same function signature, bridge generation must OR the requirements rather than selecting one registration arbitrarily.

## Bridge emission contract

For each unique canonical signature:

### `needs_caller`

Emit the guest->host runtime-PFN transition thunk required by `GetCallerForHostFunction`, plus a typed accessor that the unloadable wrapper can use when linking native PFN H to resident guest caller T.

### `needs_unpacker`

Instantiate `CallbackUnpack<Signature>::Unpack` in the resident bridge and emit a typed accessor returning that guest executable address.

Guest-side callback allocation must pass this resident unpacker address into `AllocateHostTrampolineForGuestFunction(GuestUnpacker, GuestTarget)` **at allocation time**. FEX embeds that address into `TrampolineInstanceInfo`; host-side finalization only fills `HostPacker` and cannot repair a stale `GuestUnpacker` later.

## Generated artifacts

A production-oriented generator interface should produce two consumable fragments rather than requiring a text parser:

1. `thunkgen_bridge_<lib>.inl`
   - resident definitions/instantiations;
   - caller thunks only for `needs_caller` signatures;
   - unpacker accessors only for `needs_unpacker` signatures.
2. `thunkgen_bridge_accessors_<lib>.inl`
   - declarations + typed specializations used by the unloadable wrapper;
   - no executable wrapper-owned fallback for an escaped bridge.

The ordinary `thunkgen_guest_<lib>.inl` continues to own normal API packers and public wrapper entrypoints.

## Library-specific bridge families

Role-aware generic output does not remove custom bridge code where runtime protocol information determines callback shape.

Wayland is the current example: callback signature is selected from protocol message descriptors at runtime, and some signatures require the special `wl_array` relocation path. The resident library may therefore expose a custom signature dispatcher while still using the same ownership invariant.

GL's wrapper-local allocator target is another example of an escaped executable address that does not originate from an annotated function-pointer API parameter.

## Validation gates

Before treating role-aware bridge emission as general:

1. Vulkan direct bridge: real PFN close/reload remains green.
2. GL: the 23-argument indirect-only signature produces a caller but no callback unpacker instantiation; PFN + GLX callback unload tests remain green.
3. CUDA: `callback_member` signature produces an unpacker; traced `TrampolineInstanceInfo.GuestUnpacker` is outside retired wrapper mappings; retained callback survives moved reload.
4. DRM: generated nested callback-member callback still executes without mutating caller-owned input.
5. Wayland: custom retained listener path survives moved reload once its synchronous control harness is established.

## Non-goals

This role contract does not define unload quiescence, PFN alias ownership, generation/tombstone policy, or ABI-compatible alias collapse. Those are separate lifetime/dispatch concerns.
