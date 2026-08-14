# OwnerID-backed callback generation lease result

Date: 2026-08-14
Status: successful synthetic runtime proof
Scope: owned FEX/fieldwork surfaces only

## Result

The callback deferred-reclamation mechanism remains successful after moving callback execution state from an individual descriptor to shared VMA owner-generation identity.

Exact hosted ARM64 receipt:

```text
branch:   ci/callback-owner-generation-lease-20260814
head:     67587a709b6e287e5b861044b115eb3e7acf6000
run:      31793796583
job:      94746310166
result:   success
artifact: callback-owner-generation-lease-31793796583
id:       9216627457
sha256:   0e74a03c03ed170d49ab1b3de848368bd566f434a30f1430d4299c261869af32
```

Runtime matrix:

```text
inflight=0
selfdrain=0
CALLBACK_OWNER_GENERATION_LEASE_OK
```

The candidate composes the callback lease with the previously proven transaction and identity stack:

```text
multi-owner retirement
callback tombstone
retirement lock-order repair
revoked-H state
pre-MAP_FIXED retirement
MAP_FIXED rollback transaction
VMA OwnerID
{T, OwnerID} retained claims
stable callback descriptor
shared callback owner-generation lease
```

A dedicated source-composition workflow also passed before the runtime build, so the result is not relying on a silently skipped identity layer.

## Owner-generation model exercised

For this diagnostic, a stable callback descriptor points to a `GuestCallbackOwnerGeneration` keyed by the VMA `OwnerID` returned by:

```text
QueryGuestMappingOwner(Thread, address)
```

The owner object carries:

```text
OwnerID
state: Live | Retired
aggregate Active callback count
deferred guest-unmap operations
```

Registration resolves both executable guest dependencies before entering the thunk-map lock:

```text
GuestUnpacker OwnerID
GuestTarget   OwnerID
```

This first gate deliberately requires them to be equal and non-zero. That keeps the synthetic proof scoped to one owner generation while the dependency-set design remains explicit future work.

Entry acquires the shared owner rather than an individual callback. Retirement marks that owner retired and removes every callback descriptor associated with it from future lookup. Guest-facing unmap returns success while the owner has an active lease, and physical unmap is replayed when the final owner lease releases.

## Concurrent in-flight unload

The exact owner summary is:

```text
owner=0x15
unpacker=0x7ffff7da21b0
target=0x7ffff7da2290
```

Observed ordering:

```text
DIAG_CALLBACK_OWNER_CREATE owner=0x15
DIAG_CALLBACK_OWNER_ACQUIRE owner=0x15 active=1
INFLIGHT callback-entered-host-block
DIAG_CALLBACK_OWNER_RETIRE owner=0x15 active=1 defer=1
DIAG_CALLBACK_OWNER_DEFER_HOST_UNMAP
INFLIGHT dlclose-returned rc=0
INFLIGHT close-done-before-release=1 target-mapped-before-release=1 unpacker-mapped-before-release=1
INFLIGHT released-host-block
DIAG_CALLBACK_OWNER_RELEASE owner=0x15 active=0 deferred=1
DIAG_CALLBACK_OWNER_RECLAIM_BEGIN owner=0x15
DIAG_CALLBACK_OWNER_RECLAIM_DONE owner=0x15 result=0
INFLIGHT worker-returned rv=70053
INFLIGHT mapped-after-release target=0 unpacker=0
DIAG_CALLBACK_OWNER_REVOKED owner=0x15 state=1 active=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DEFERRED_LEASE_PASS
```

This proves all three desired properties in one run:

1. guest `dlclose` returns without synchronously waiting for an already-entered callback;
2. the executable owner remains physically mapped until the active owner lease releases;
3. after final release the physical mapping disappears and every future entry through the retained old native callback reaches controlled revoke instead of stale guest execution.

## Callback self-unload

The self-unload fixture resolves a distinct owner generation:

```text
owner=0xf
unpacker=0x7ffff7ebd1b0
target=0x7ffff7ebd290
```

Observed ordering:

```text
SELF_DRAIN configured ...
DIAG_CALLBACK_OWNER_CREATE owner=0xf
DIAG_CALLBACK_OWNER_ACQUIRE owner=0xf active=1
DIAG_CALLBACK_OWNER_RETIRE owner=0xf active=1 defer=1
DIAG_CALLBACK_OWNER_DEFER_HOST_UNMAP
DIAG_CALLBACK_OWNER_RELEASE owner=0xf active=0 deferred=1
DIAG_CALLBACK_OWNER_RECLAIM_BEGIN owner=0xf
DIAG_CALLBACK_OWNER_RECLAIM_DONE owner=0xf result=0
SELF_DRAIN returned rv=80053
SELF_DRAIN survived rv=80053
```

This is the positive replacement for synchronous draining, which previously deadlocked because the callback's own thread waited for the lease it was holding.

The resulting policy is now executable evidence rather than only a design preference:

> Retirement must revoke future entry immediately and must not synchronously wait for an active callback. Physical owner reclamation can occur after the final active generation lease releases.

## What this advances over the descriptor-level proof

The earlier successful prototype put `Active` and deferred unmaps on each callback descriptor independently. That is unsafe when several callbacks share the same executable generation: one descriptor could reach zero and reclaim code another descriptor still needs.

This result demonstrates the same successful runtime behavior with the activity counter and retirement state shared by callbacks that resolve to the same non-reusable VMA owner identity.

It also composes with the already-proven same-address ABA identity work rather than creating a second unrelated generation model.

## Important remaining ownership gap: VMA is not necessarily load generation

The current `OwnerID` identifies a mapping generation. A normal ELF DSO can contain several VMAs: executable text, read-only data, writable state, RELRO, and related mappings.

A callback that begins in one executable VMA can subsequently execute or read another mapping from the same DSO. Protecting only the particular VMA that contained `GuestTarget` or `GuestUnpacker` is therefore not automatically sufficient as a product load-lifetime contract.

Production needs one of these stronger representations:

```text
A. LoadGenerationID
   one non-reusable identity groups every VMA belonging to one loader generation

or

B. OwnerDependencySet
   a callback lease pins every mapping-generation identity its execution may require
```

A loader/load-generation identity is likely the cleaner abstraction if FEX can obtain or maintain it reliably.

## Two executable dependencies per callback

A FEX thunk callback carries at least two executable guest addresses:

```text
GuestUnpacker
GuestTarget
```

They are semantically different owners.

With the proposed resident generated bridge:

```text
GuestUnpacker -> process-resident generated bridge
GuestTarget   -> application/plugin load generation
```

That simplifies runtime reclamation: the generated unpacker no longer participates in unloadable generation leasing, leaving the actual callback target owner as the reclaimable dependency.

Without a resident bridge, a general callback lease cannot assume the two addresses have the same OwnerID. It needs a dependency set or load-generation grouping.

## Replacement hazard is now the next critical discriminator

The successful mechanism intentionally acknowledges guest `munmap`/`dlclose` before physical host unmap when a generation is leased.

That creates a new rule for destructive address-space operations:

> A `MAP_FIXED` or equivalent destructive replacement must not overwrite a retired generation whose executable mappings are still physically pinned by active execution leases.

The current transaction work knows how to retire/rollback mapping claims, but the new lease must participate in replacement arbitration.

Next synthetic test:

```text
1. enter callback and acquire owner lease;
2. guest dlclose retires owner and returns while physical mapping remains;
3. another thread attempts MAP_FIXED replacement over that leased executable range;
4. observe current behavior before adding policy;
5. safe candidate must reject, block, or defer destructive replacement without corrupting the active callback;
6. after lease release, old generation is reclaimed and replacement may proceed with a fresh OwnerID.
```

Do not silently serialize this through a synchronous callback drain; that would reintroduce the already-proven self-unload deadlock class.

## Real-API integration target

The generated DRM `drmServerInfo::load_module` resident-bridge proof now supplies the preferred real callback family.

That result already demonstrates:

```text
wrapper-owned unpacker control = 139
generated resident bridge      = 0
wrapper physically unloads
reload forced to move
old native retained callback state invokes successfully after reload
```

The next real integration should put the **actual guest `load_module` target** in a separately unloadable guest plugin DSO while leaving the generated DRM unpacker resident. Then apply this owner-generation lease to the plugin target during concurrent unload/self-unload/reload.

## Product-shape recommendation after this proof

Keep the architecture separated into three mechanisms:

```text
resident generated companion
  process lifetime for generated executable helpers that intentionally escape

generation tombstone
  immediate rejection of every future entry into a retired guest generation

execution lease
  physical reclamation delay only for unloadable guest generations already executing
```

The next design work should promote VMA OwnerID into a true load-generation/dependency abstraction and make destructive mapping replacement lease-aware before attempting source-ready cleanup.
