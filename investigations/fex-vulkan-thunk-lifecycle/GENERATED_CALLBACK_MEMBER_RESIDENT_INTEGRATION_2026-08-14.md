# Generated callback-member + resident bridge integration — 2026-08-14

## Scope

This note records observed results from owned FEX research branches. It separates callback ABI conversion, executable adapter lifetime, native object retention, guest callback-owner reclamation, and const-qualified repacking.

## DRM retained callback: generated conversion + resident adapter + retained object

Owned FEX branch: `ci/agent-b-drm-serverinfo-loadmodule-resident-20260814`

Successful run: `31791873613`

Result:

```text
native_precondition=0
wrapper_owned_unpacker_reference=139
handwritten_resident_reference=0
generated_loadmodule_resident=0
OUTCOME=generated_loadmodule_conversion_survived_retained_moved_reload
```

The successful lane generates `drmServerInfo::load_module` conversion through thunkgen `callback_member`, routes the guest-side callback allocation through the generated `NODELETE` DRM bridge, keeps the ordinary `libdrm.so.2` wrapper unloadable, and uses custom `drmSetServerInfo` host code only to retain a copy of the already-repacked containing object.

`drmServerInfo` also contains `debug_print(const char*, va_list)` and `get_perms`. Sending all three through the generic callback-member path exposed the `va_list` ABI boundary. The discriminator therefore used an explicit exceptional-member policy for the sibling callbacks while `load_module` stayed generated.

Observation: callback ABI conversion, executable adapter lifetime, and retained containing-object lifetime can be independent policies.

## Vulkan `VkAllocationCallbacks`: generated five-member conversion

Base full-derived Vulkan resident bridge head: `3288618bdb08cd46b1920d5772e376701e728f70`.

### Regular generated API control

Owned FEX branch: `ci/agent-b-vulkan-allocator-callback-member-resident-20260814`

Green head: `9a535085fc9e71c9cce9c3d9e653c7dc5a926194`

Run: `31792355051`

`VkAllocationCallbacks` was changed from opaque data to a repackable record with:

- `pUserData`: existing custom-member pointer translation
- `pfnAllocation`: `callback_member`
- `pfnReallocation`: `callback_member`
- `pfnFree`: `callback_member`
- `pfnInternalAllocation`: `callback_member`
- `pfnInternalFree`: `callback_member`

Generated signature receipts:

```text
raw_callback_entries=480
unique_callback_signatures=480
bridge_callback_signatures=480
```

The full Vulkan bridge previously contained 476 signatures. Adding five allocator callback members produced four additional canonical generated signatures; one allocator callback signature overlaps canonically.

Runtime through `vkCreateBuffer`:

```text
native=0
pristine_instance_reference=132
generated_buffer_candidate=0
OUTCOME=generated_vulkan_allocator_callbacks_crossed_resident_bridge
```

### Real `vkCreateInstance` retained allocator path

Owned FEX branch: `ci/agent-b-vulkan-instance-allocator-callback-member-resident-20260814`

Head: `4efe0461e7949daf760a652a8f312f0802cc0c0e`

Run: `31792882894`

The existing custom host implementation received the normal generated/repacked allocator as `a_1` but discarded it by calling native `vkCreateInstance(..., nullptr, ...)`. This lane changes only that forwarding decision to `vkCreateInstance(..., a_1, ...)` on top of the already-green generated callback-member experiment.

Generated-code checks passed for all five callback members. The normal guest wrapper contains 480 callback signatures; the generated resident bridge contains the same 480 signatures. `libvulkan-guest.so` has no `NODELETE` flag and depends on `libfex-vulkan-bridge.so`; the bridge has `FLAGS_1: NODELETE`.

Runtime:

```text
native=0
pristine_reference=132
generated_instance_candidate=0
OUTCOME=generated_vulkan_instance_allocator_callbacks_passed
```

Native callback counts:

```text
create-return: alloc=165 realloc=4 free=141
destroy-return: alloc=165 realloc=4 free=161 free_delta=20
```

FEX generated candidate callback counts:

```text
create-return: alloc=165 realloc=4 free=141
destroy-return: alloc=165 realloc=4 free=161 free_delta=20
```

Observation: the generated callback-member conversion reaches a real Vulkan retained allocator workload with the same callback counts observed by the native control.

## Const-qualified repacking

Owned FEX branch: `ci/thunkgen-preserve-const-repack-20260814`

Head: `6ef56dcedf9389816f7910667ef8ea99ae5a9c85`

Run: `31786991508`

The generic correction preserves pointee `const` qualification in generated `repack_wrapper<T>` types. The Vulkan allocator create/destroy trace then completes with `native=0 / FEX=0`, preserving the guest allocator values and host callback trampoline identities across entrypoints.

This belongs in the generic thunkgen implementation independently of the callback-member prototype.

## Deferred reclaim and in-flight guest callback execution

Fieldwork retained proof: `CALLBACK_DEFERRED_RECLAIM_LEASE_RESULT_2026-08-14.md`, commit `f8ef746cc8b0e49223e0356501bc5ed45880443a`.

Owned FEX branch: `ci/callback-deferred-reclaim-lease-20260814`, run `31792336176`.

Observed concurrent unload behavior:

```text
close-done-before-release=1
target-mapped-before-release=1
unpacker-mapped-before-release=1
worker return=70053
close return=0
target-mapped-after-release=0
unpacker-mapped-after-release=0
stale-first-callback exit=113
INFLIGHT DEFERRED_LEASE_PASS
```

Self-unload also returns successfully without waiting on its own callback lease.

Interpretation: retirement should deny future callback entry immediately, while physical reclamation of guest callback-owner code is delayed until existing execution leases drain. Production identity should be keyed by a non-reusable owner generation rather than a callback descriptor/address alone.

## Coherent implementation direction

The successful experiments now support these separate responsibilities:

1. **Declarative callback-bearing members.** Thunkgen generates temporary guest record copies, partial callback trampolines, and host finalization for ordinary typed callback fields.
2. **Per-library resident generated adapter sidecars.** Signature-derived executable callback/invoker adapters remain process-resident while ordinary API wrappers can unload and move.
3. **Retained-object ownership policy.** APIs that retain callback-bearing containing objects need an explicit copy/lease/ownership rule; this is separate from callback ABI conversion.
4. **Exceptional callback-member policy.** Callback ABIs such as `va_list` need an explicit special policy instead of raw guest-pointer escape.
5. **Const-qualified repack correctness.** Generated wrapper types preserve pointee constness so input-only guest records are not copied back into.
6. **Owner-generation tombstone + execution lease for reclamation.** When guest callback-owner mappings themselves are reclaimable, future entry is revoked immediately and in-flight execution holds the owner generation alive until return.

A process-lifetime resident sidecar avoids reclamation complexity for FEX-created adapters. Owner-generation leases address a different object: guest code/unpacker mappings whose lifetime can end while a native callback is already in flight.

## Immediate next integration work

- Forward generated `VkAllocationCallbacks` through remaining Vulkan custom host entrypoints that currently discard allocator parameters where Vulkan semantics require forwarding.
- Add focused thunkgen tests for callback-bearing records, canonical signature overlap, const-pointee repacking, and exceptional sibling callback policy.
- Keep retained-object ownership metadata distinct from callback-member ABI metadata.
- Treat adapter reclamation as optional; if added, use owner-generation identity and nonblocking retirement semantics proven by the lease fixture.
