# Callback deferred-reclaim lease result

Date: 2026-08-14
Status: successful synthetic runtime proof
Scope: owned FEX/fieldwork surfaces only

## Result

A nonblocking callback execution lease closes both deterministic failure modes that defeated the earlier retirement designs:

1. an already-entered callback may continue after guest `dlclose` begins without executing unmapped guest code;
2. a callback may call `dlclose` on its own owner without synchronously waiting on its own active lease.

Exact hosted ARM64 receipt:

```text
branch:   ci/callback-deferred-reclaim-lease-20260814
head:     0f3e0e1fd41fc9cdb2442e2ac515daff2fbb2c15
run:      31792336176
job:      94741828611
result:   success
artifact: callback-deferred-reclaim-lease-31792336176
id:       9216076537
sha256:   c555861feae4db04284fa0431e51538037e5a0829b35ac33274242d0f0a5350d
```

The source baseline is exact FEX `71afe476751deac24adabd1adb575fd2337b6e0a` plus the established owner-retirement/tombstone research patches and the new diagnostic lease patch.

## Mechanism tested

Each retained callback uses a stable FEX-owned descriptor with:

```text
state: Live | Retired
active lease count
immutable GuestUnpacker
immutable GuestTarget
queued deferred unmap ranges
```

Callback entry performs `TryAcquire()` before reading/using the guest addresses. Retirement changes `Live -> Retired`, removes the future cache/registration path, and denies every later acquire.

When retirement intersects an active descriptor, the guest-facing `munmap` operation returns success without performing the physical host unmap. The descriptor records that range as deferred.

The already-entered callback is then allowed to finish. Its RAII lease release sees `Retired && active == 0` and replays the deferred guest unmap from FEX after guest callback execution has returned.

Future use of the old escaped host trampoline remains a controlled revoke (`113`).

## Concurrent in-flight unload gate

The fixture deliberately holds one callback active inside FEX while another guest thread closes the callback owner's DSO.

The successful run requires all of the following:

```text
close-done-before-release=1
target-mapped-before-release=1
unpacker-mapped-before-release=1
worker return = 70053
close return = 0
target-mapped-after-release=0
unpacker-mapped-after-release=0
stale-first-callback exit = 113
INFLIGHT DEFERRED_LEASE_PASS
```

The runtime receipt also requires the ordering evidence:

```text
DIAG_CALLBACK_LEASE_ACQUIRE ... active=1
DIAG_CALLBACK_DESCRIPTOR_RETIRE ... active=1 defer=1
DIAG_CALLBACK_DEFER_HOST_UNMAP
DIAG_CALLBACK_LEASE_RELEASE ... deferred=1
DIAG_CALLBACK_DEFERRED_RECLAIM_BEGIN
DIAG_CALLBACK_DEFERRED_RECLAIM_DONE ... result=0
```

This is the direct positive counterpart to the earlier v3 discriminator, where the same already-selected callback resumed after physical unmap and died with 139.

The important property is that **guest `dlclose` is allowed to finish before the active callback finishes, while the executable owner mapping remains physically present until the callback lease is released**.

## Callback self-unload gate

The second fixture invokes `dlclose(owner)` from the active guest callback itself.

The successful run requires:

```text
SELF_DRAIN returned rv=80053
SELF_DRAIN survived rv=80053
lease acquire active=1
retire active=1 defer=1
defer host unmap
lease release deferred=1
deferred reclaim done
process exit = 0
```

This is the positive replacement for the earlier synchronous-drain experiment, which deadlocked waiting for `Active == 0` while the retiring thread itself owned the only active callback lease.

The result demonstrates that retirement must be nonblocking with respect to active callback execution.

## What this proves

For the synthetic single-owner/single-descriptor case, the required lifecycle is workable:

```text
LIVE
  acquire callback execution lease

RETIRE
  deny future entry immediately
  let guest unload bookkeeping return
  keep physical executable owner mapped while active > 0

LAST RELEASE
  physically reclaim deferred owner mapping

STALE FUTURE ENTRY
  controlled FEX-owned revoke
```

This simultaneously satisfies the in-flight race and self-unload cases that contradicted the earlier strategies.

## Important diagnostic limitations

This branch is a mechanism proof, not a source-ready FEX implementation.

### 1. Deferral is descriptor/range based

The diagnostic stores deferred `munmap` ranges on the matching callback descriptor. A real owner generation may have multiple retained callback descriptors and multiple VMAs.

If two descriptors from the same owner are active, per-descriptor reclamation can reclaim a shared owner when one descriptor reaches zero while another is still active.

Production therefore needs **aggregate lease state on the owner generation**, not independent reclamation decisions per callback descriptor.

### 2. Owner identity is not yet wired into this branch

Existing research already supplies a non-reusable VMA `OwnerID` and a syscall-handler query:

```text
QueryGuestMappingOwner(Thread, address)
```

Same-address replacement changes OwnerID while protection-only transformations preserve it. Retained H->T claims have already been demonstrated as distinct `{T, OwnerID}` generations.

The next callback implementation should bind each descriptor to that OwnerID and move `active`, `retired`, and deferred mapping sets to a shared owner-generation object.

### 3. Successful guest unmap is acknowledged before physical reclaim

That is intentional for self-unload compatibility, but it creates a new ownership requirement: FEX must prevent the retired owner's physical address range from being destructively replaced while an execution lease still needs it.

A `MAP_FIXED`/replacement attempt cannot simply overwrite a leased retired generation. The owner-generation state machine must arbitrate replacement or defer it until lease release.

### 4. Reclaim executes synchronously on last release in the diagnostic

The prototype re-enters `GuestMunmap` directly from callback lease destruction. It works for the retained fixture, but production should make lock ordering, signal deferral, and execution context explicit. A queued reclamation operation may be cleaner if the product lock graph requires it.

## Next implementation step

Promote the mechanism from callback descriptor/range ownership to shared VMA owner-generation ownership:

```text
CallbackDescriptor
  -> OwnerGeneration(OwnerID)

OwnerGeneration
  state: Live | Retired
  aggregate callback active count
  deferred VMA/unmap set
  generation identity
```

Entry acquires the owner generation through the descriptor. Retirement tombstones every descriptor belonging to that owner, marks the owner retired, and records all physical reclaim operations. Last aggregate release reclaims the generation once.

Then rerun:

1. concurrent in-flight callback unload;
2. callback self-unload;
3. same-address reload/retained-old-pointer ABA;
4. MAP_FIXED replacement while an old generation is leased;
5. real retained-callback API: DRM first, CUDA second.

## Architectural consequence

The investigation can now distinguish three lifetime mechanisms cleanly:

- **resident generated bridge**: process-lifetime ownership for generated escaping callback/proc-address adapter code;
- **generation tombstone**: immediate rejection of future entries into a retired guest owner;
- **owner execution lease**: delayed physical reclamation only for guest owner generations that already have active execution.

This is narrower than making whole thunk wrappers permanently resident and avoids imposing reclamation machinery on generated bridge code that is intentionally process-resident.
