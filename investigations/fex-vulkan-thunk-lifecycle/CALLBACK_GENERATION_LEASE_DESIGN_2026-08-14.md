# FEX callback generation lease design

Date: 2026-08-14
Status: active research design
Scope: owned FEX/fieldwork surfaces only

## Problem now isolated

The callback lifetime investigation has separated **future entry** from **already-entered execution**.

Future entry can be retired safely by tombstoning the stable FEX-owned host trampoline before guest executable mappings disappear. The same-address ABA carrier demonstrates that an old retained native callback pointer reaches a controlled FEX-owned revoked path (`113`) while a freshly registered callback at the same guest addresses remains usable.

That does not protect a callback that has already entered FEX and captured its raw `GuestUnpacker` and `GuestTarget` before retirement.

The deterministic v3 in-flight carrier proves the missing interval:

```text
DIAG_CALLBACK_INFLIGHT_SELECTED entry=2
... owner retirement / tombstone ...
DIAG_CALLBACK_POST_UNMAP_RELEASE
DIAG_CALLBACK_INFLIGHT_RESUME
... stale guest execution -> 139
```

Run:

```text
branch: ci/callback-inflight-unmap-race-v3-20260814
head:   5c1eda9f08786101451877bc3a59616f58a63431
run:    31787836044
result: success as discriminator; pin=0, unmap=139
```

The ordering assertion in the carrier requires selected -> tombstone -> post-host-unmap release -> resumed stale execution.

## Blocking drain is not the answer

A descriptor prototype added `TryAcquire`/`Release`, a `Draining` state, and synchronous `DrainAndRevoke()` before physical unmap.

A self-unload fixture then invoked `dlclose` from inside the active callback itself. The active callback owned the only lease while the same thread entered retirement and waited for `Active == 0`.

Observed outcome:

```text
descriptor-only path -> non-timeout crash
blocking drain path   -> timeout / self-deadlock
```

Run:

```text
branch: ci/thunk-callback-selfdrain-20260814
head:   85922a6e663ee56d1377ecab48fcbd669a7aea30
run:    31786449265
```

The drain trace reaches `DIAG_CALLBACK_DESCRIPTOR_ACQUIRE active=1`, `DRAIN_BEGIN active=1`, and `DRAIN_WAIT active=1`, with no drain completion before timeout.

Therefore callback retirement cannot synchronously wait for a lease that may be owned by the retiring thread.

## Required state machine

The next runtime prototype should model each retained callback generation with a stable FEX-owned descriptor.

Conceptually:

```text
Live
  new leases allowed
  active count may increase/decrease

Retired
  no new leases
  stable escaped trampoline routes future entries to controlled revoke
  existing leases may finish
  physical owner reclamation is pending while active != 0

Reclaimed
  active == 0
  queued executable mappings may be physically unmapped
```

### Entry

```text
1. resolve stable descriptor
2. atomically acquire only if state == Live
3. after successful acquire, use descriptor's immutable generation-owned
   GuestUnpacker / GuestTarget
4. release on every return path
```

The acquire operation must close the acquire-vs-retire race. A mutex-based first research implementation is acceptable; production may use atomics if justified by profiling.

### Retirement

```text
1. transition generation Live -> Retired
2. erase future registration/cache key
3. keep stable native trampoline executable but make new entry fail/revoke
4. if active == 0, reclaim immediately
5. if active != 0, queue physical reclamation and return without waiting
```

The retirement caller must not block for active callbacks.

### Last release

```text
active--
if state == Retired && active == 0:
    perform or schedule queued reclamation
```

The first diagnostic implementation may perform deferred reclaim directly from the releasing FEX-managed guest thread. A production design should make the execution context and lock ordering explicit.

## Mapping ownership requirement

The final product mechanism must defer the **owner generation**, not merely the page containing the raw callback address. A callback can execute helper code elsewhere in its DSO after entry.

The existing owner-ID research provides the identity primitive:

```text
{guest executable target, OwnerID}
```

Same-address replacement already proves that numeric address alone cannot identify the generation (`0xe -> 0xf`). The callback lease should bind to that non-reusable generation identity once the diagnostic behavior is proven.

For the first synthetic proof, a narrowly scoped deferred-unmap hook around the fixture's callback-owned mappings is acceptable as long as the receipt labels that limitation explicitly.

## Acceptance matrix for the next prototype

### A. Concurrent in-flight unload

```text
callback entry acquires lease
retirement tombstones future entry
loader asks to unmap owner
host unmap is deferred while active=1
callback resumes and returns successfully
last release performs deferred unmap
mapping check proves owner finally disappeared
process exits 0
```

This should replace the current v3 `unmap=139` arm with a clean result while retaining the pin control.

### B. Self-unload

```text
callback acquires lease
callback itself calls dlclose(owner)
retirement marks retired and returns without waiting
callback completes
last release performs deferred reclaim
no timeout, no stale execution
```

This directly rejects the earlier synchronous-drain deadlock.

### C. Same-address reload / retained old pointer

The old escaped native callback pointer remains a controlled revoke (`113`). A freshly registered callback from the new owner generation works even if guest numeric addresses are reused.

### D. Real API follow-up

After the synthetic state machine works:

1. DRM retained callback first;
2. CUDA host-node callback second;
3. Wayland only after the carrier invokes from a FEX-managed guest thread rather than an unrelated native-created thread.

## Relationship to resident bridges

The resident bridge and callback generation lease solve different ownership layers.

A resident companion gives generated escaping `CallbackUnpack<signature>::Unpack` code process lifetime, so ordinary thunk-wrapper unload cannot invalidate that generated helper.

The **actual guest callback target** still belongs to the guest mapping/load generation that supplied it. If that owner is unloadable while native state retains the callback, generation retirement + execution lease is still required.

Keeping these mechanisms separate avoids putting full reclamation machinery on process-resident generated bridge adapters.

## Non-goals of the first lease prototype

- no cross-library bridge deduplication;
- no attempt to reclaim resident bridge code;
- no claim that page/range matching is sufficient product-level owner identity;
- no synchronous wait in `dlclose`/`munmap`;
- no machine callback trampoline ABI change unless evidence forces one.

## Next implementation move

Start from the proven descriptor/tombstone path. Reuse `TryAcquire` + RAII release, remove synchronous `DrainAndRevoke`, and add a diagnostic deferred-unmap queue. Run the in-flight and self-unload carriers unchanged except for their expected outcomes and additional ordering/mapping checks.

Only after both are green should the deferred range be promoted from a diagnostic callback-range association to the existing non-reusable VMA OwnerID generation model.
