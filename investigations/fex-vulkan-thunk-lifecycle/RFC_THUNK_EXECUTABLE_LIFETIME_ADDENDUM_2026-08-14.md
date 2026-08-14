# RFC addendum: callback execution leases and generation reclamation

Date: 2026-08-14
Status: evidence update to `RFC_THUNK_EXECUTABLE_LIFETIME.md`

## Why this addendum exists

The original lifetime RFC correctly separated future-dispatch identity from execution lifetime, but the required execution mechanism was still described as a design choice among quiescence/lease/hazard-style approaches.

The owned-fork evidence now narrows that choice substantially.

## Demonstrated retirement policy

For unloadable guest callback targets, the successful research state machine is:

```text
callback entry
  acquire generation execution lease

retirement
  mark generation retired
  revoke/tombstone every future entry immediately
  do not synchronously wait for active callbacks
  acknowledge guest unload while keeping required physical mappings pinned

last active release
  perform deferred physical reclamation

future stale retained entry
  controlled FEX-owned revoke
```

This policy has positive runtime evidence for both failure shapes that defeated the simpler alternatives.

### Concurrent unload after callback entry

OwnerID-backed receipt:

```text
branch: ci/callback-owner-generation-lease-20260814
head:   67587a709b6e287e5b861044b115eb3e7acf6000
run:    31793796583
job:    94746310166
```

One callback acquires owner `0x15`, another guest thread closes the owner, guest `dlclose` returns while target+unpacker remain physically mapped, the callback returns normally, and final release performs deferred reclaim. The old retained native callback pointer then exits through controlled revoke `113`.

### Callback unloads its own owner

The same runtime candidate handles the self-unload case under owner `0xf`. Retirement returns without waiting for the callback's own active lease; the callback returns `80053`; final release reclaims the deferred mapping.

This directly replaces the synchronous-drain prototype, which deadlocked waiting on the lease owned by the retiring callback thread.

Detailed receipt: [`CALLBACK_OWNER_GENERATION_LEASE_RESULT_2026-08-14.md`](./CALLBACK_OWNER_GENERATION_LEASE_RESULT_2026-08-14.md).

## Consequence for the RFC recommendation

For **future entry**, generation identity + tombstone/revocation is sufficient.

For **already-entered execution**, the research recommendation should now say **generation execution lease with nonblocking retirement and deferred reclamation** rather than leaving the mechanism unspecified.

This is still a research mechanism rather than a source-ready product patch because the ownership unit needs strengthening.

## Ownership unit still needs promotion

The current successful key is FEX's experimental VMA `OwnerID`. Same-address replacement already proves that OwnerID changes across successful generation replacement while protection-only transitions preserve it.

A VMA generation is not automatically equivalent to an ELF/load generation. Real callback execution may depend on several mappings from one load.

Product options:

```text
LoadGenerationID
  one non-reusable owner groups all mappings from one loader generation

OwnerDependencySet
  one execution lease pins every mapping-generation dependency needed by the callback
```

The first option is preferable if the guest loader/FEX mapping layer can provide a reliable grouping primitive.

## Resident bridge interaction

A callback transition has at least two executable guest dependencies:

```text
GuestUnpacker  -- generated thunk code
GuestTarget    -- application callback code
```

The resident-companion proposal intentionally gives `GuestUnpacker` process lifetime. Once that split is used, reclaimable execution leasing is focused on the actual application callback target/load generation.

This is a useful architectural simplification and another reason to keep resident generated adapters separate from application callback-target lifetime.

The generated DRM `drmServerInfo::load_module` proof now demonstrates the resident half on a real API while the public libdrm guest wrapper physically unloads/reloads:

```text
wrapper-owned unpacker control = 139
generated resident bridge      = 0
```

See [`DRM_RETAINED_LOAD_MODULE_GENERATED_RESIDENT_2026-08-14.md`](./DRM_RETAINED_LOAD_MODULE_GENERATED_RESIDENT_2026-08-14.md).

## New critical boundary: destructive replacement while leased

Deferred reclamation means guest unload bookkeeping can finish before host mappings are physically removed. Therefore destructive address-space replacement must participate in the lease state machine.

A `MAP_FIXED` operation must not overwrite executable code still required by an active retired generation.

A dedicated discriminator is now running from:

```text
ci/callback-lease-map-fixed-discriminator-20260814
```

The gate deliberately attempts `MAP_FIXED` over the active callback's executable page after guest `dlclose` has returned but before the callback lease releases. The first run is observational: establish whether the current owner-lease prototype allows destructive overwrite before adding replacement arbitration.

A safe candidate must reject, defer, or otherwise serialize the destructive replacement at the **mapping-owner** level without synchronously draining the callback thread.

## Separate thunkgen correctness fix

The Vulkan allocator investigation also found a generic repack bug unrelated to executable reclamation: thunkgen stripped pointee `const`, allowing converted host state to be copied back into caller-owned `const T*` input.

Clean candidate:

```text
linux-fieldwork/thunkgen-preserve-const-repack
715ff36bff2fd9f2353ab31613dc41ae106f3938
```

Validation is now complete at the investigation level:

```text
hosted Vulkan allocator runtime: PASS
targeted StructRepacking regression: PASS (28 assertions)
broader hosted-x86 failure delta vs exact parent: none observed
```

See [`THUNKGEN_CONST_POINTEE_REPACK_RESULT_2026-08-14.md`](./THUNKGEN_CONST_POINTEE_REPACK_RESULT_2026-08-14.md).

This should remain a standalone thunkgen correctness proposal, not part of the lifetime mechanism patch.

## Updated proposal order

1. selective NODELETE remains the smallest containment option;
2. resident per-library generated companion remains the preferred wrapper-unload-preserving architecture;
3. generated callback/proc-address directions must be typed separately;
4. actual unloadable callback targets use immediate generation retirement plus nonblocking execution leases;
5. promote VMA OwnerID to a load-generation/dependency abstraction;
6. make destructive replacement lease-aware;
7. prove the combination on a real retained callback API with the target in a separately unloadable plugin DSO;
8. keep cross-library bridge deduplication and resident-code reclamation as later optimizations.

## Current strongest pitch

> FEX has two distinct escape-lifetime problems. Generated callback/PFN adapters that intentionally escape wrapper lifetime should live in a resident generated companion. Actual application callback targets remain owned by their load generation: retirement must revoke future entry immediately, while already-entered callbacks hold a generation execution lease until they return. Physical reclamation is deferred, not synchronously drained. The remaining product work is to promote VMA identity into load-generation ownership and make destructive mapping replacement respect active leases.
