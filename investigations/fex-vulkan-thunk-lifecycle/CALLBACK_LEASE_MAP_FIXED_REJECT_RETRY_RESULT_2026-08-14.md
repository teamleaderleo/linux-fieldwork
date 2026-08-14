# Callback execution lease vs MAP_FIXED: reject/release/retry result

Date: 2026-08-14
Status: successful synthetic runtime proof
Scope: owned FEX/fieldwork surfaces only

## Result

The deterministic destructive-replacement failure is closed by a narrow memory-transaction guard: while an intersecting callback owner generation has an active execution lease, guest `MAP_FIXED` is rejected with `EBUSY`; after the final lease releases and deferred owner reclamation completes, the exact same replacement succeeds and receives a fresh OwnerID.

Exact hosted ARM64 receipt:

```text
branch:   ci/callback-lease-map-fixed-reject-20260814
head:     7cce0a27515c84c37d4aef5d5642d4e8dfc1130b
run:      31794845810
job:      94749556547
result:   success
artifact: callback-lease-map-fixed-reject-31794845810
id:       9217045905
sha256:   7708617ea5de5222f825adf007096230ee7065527358142f044f00644b894529
runtime:  exit 0
```

Product baseline remains exact FEX:

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

## Before the destructive replacement

The retained callback is associated with owner generation `0x15`:

```text
DIAG_CALLBACK_OWNER_CREATE owner=0x15
DIAG_CALLBACK_OWNER_ACQUIRE owner=0x15 active=1
INFLIGHT callback-entered-host-block
```

Guest `dlclose` retires that generation without physically removing it while the callback is active:

```text
DIAG_CALLBACK_OWNER_RETIRE owner=0x15 active=1 defer=1 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_OWNER_DEFER_HOST_UNMAP range=0x7ffff7da1000+0x5000
INFLIGHT dlclose-returned rc=0
INFLIGHT close-done-before-release=1 target-mapped-before-release=1 unpacker-mapped-before-release=1
```

The target and unpacker are both inside the still-pinned owner mapping:

```text
target   = 0x7ffff7da2270
unpacker = 0x7ffff7da2190
```

## Replacement is denied while the lease is active

The test requests one-page `MAP_FIXED` over `0x7ffff7da2000`, the page containing both executable addresses.

The lifetime query finds owner `0x15` with one active lease:

```text
DIAG_CALLBACK_LEASE_REPLACE_BLOCK owner=0x15 active=1 range=0x7ffff7da2000+0x1000
DIAG_CALLBACK_LEASE_MAP_FIXED_REJECT range=0x7ffff7da2000+0x1000 errno=16
LEASE_MAP_FIXED returned rv=0xffffffffffffffff errno=16
LEASE_MAP_FIXED done-before-release=1 rv=0xffffffffffffffff errno=16
```

The rejection happens before `PrepareGuestRangeRetirement` and therefore before physical destructive replacement.

This is the direct positive counterpart to the prior hazard run, where the same request succeeded immediately, changed owner `0x15 -> 0x1a`, and the callback later resumed into overwritten code and died with `139`.

## Final lease release and physical reclaim

The callback then resumes normally:

```text
INFLIGHT released-host-block
DIAG_CALLBACK_OWNER_RELEASE owner=0x15 active=0 deferred=1
DIAG_CALLBACK_OWNER_RECLAIM_BEGIN owner=0x15 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_OWNER_RECLAIM_DONE owner=0x15 range=0x7ffff7da1000+0x5000 result=0
INFLIGHT worker-returned rv=70053
```

The mapping check confirms the old callback executable state is gone only after the active execution lease ends:

```text
INFLIGHT mapped-after-release target=0 unpacker=0
```

## Exact replacement succeeds after release

The fixture retries the same one-page `MAP_FIXED` at the same address after deferred reclaim:

```text
DIAG_MAP_FIXED_PREPARE range=0x7ffff7da2000+0x1000
DIAG_OWNER_MAP_FIXED addr=0x7ffff7da2000 old=0 new=0x1a success=1
LEASE_MAP_FIXED retry-after-release rv=0x7ffff7da2000 errno=0 mapped=1
```

So the lease guard is temporary lifetime protection rather than permanent address reservation.

The retained old native callback pointer remains associated with the retired owner and reaches controlled revoke:

```text
DIAG_CALLBACK_OWNER_REVOKED owner=0x15 ... state=1 active=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DEFERRED_LEASE_PASS
```

## What this proves

For the synthetic single-OwnerID case, the complete destructive-replacement sequence is now demonstrated:

```text
active callback lease
  -> guest unload retires owner and defers physical unmap
  -> destructive MAP_FIXED is rejected with EBUSY
  -> active callback returns safely
  -> last release physically reclaims retired owner
  -> same MAP_FIXED retry succeeds
  -> new mapping gets fresh OwnerID
  -> retained old callback remains revoked
```

The memory-transaction layer therefore has enough information to preserve an active executable generation without blocking the callback or reintroducing the self-unload drain deadlock.

## Research-policy boundary

`EBUSY` is a deliberately simple discriminator policy, not yet an upstream ABI recommendation.

Possible product policies include:

```text
reject with a documented errno
queue/defer replacement until the generation is reclaimable
other loader-integrated serialization
```

The key invariant is independent of that policy:

> No destructive address-space operation may physically overwrite a mapping generation while active execution leases still require it.

## Important implementation limitation

The current guard resolves one OwnerID from the start address of the requested replacement range.

That is enough for this one-page discriminator but not a general range-overlap implementation. A production query must inspect **every intersecting owner generation** for a destructive range and reject/defer if any required generation is actively leased.

This becomes more important once owner identity is promoted from VMA generation to `LoadGenerationID` or an explicit owner dependency set.

## Next memory-lifetime audit

Audit every path that can physically destroy/replace guest mappings, not just explicit `munmap` and `MAP_FIXED`. Candidates include:

- other fixed-mapping variants;
- `mremap` paths that can move/replace mappings;
- any internal VMA replacement helper used by the loader/emulation layer;
- rollback paths that can restore or discard a generation.

Each should use the same owner-generation lease arbitration contract rather than adding callback-specific checks.

## Real-API follow-up

A separate DRM control now proves the resident generated unpacker/application-target split on a real retained callback:

```text
GuestUnpacker -> NODELETE generated DRM bridge
GuestTarget   -> unloadable callback plugin DSO
plugin dlclose while callback active -> target unmapped -> 139
```

The next real integration attaches the lease to `TargetOwnerID` while allowing the resident unpacker to have a different owner. That test is running on:

```text
ci/drm-loadmodule-plugin-target-owner-lease-20260814
```

If pinning the callback target's single VMA is insufficient, the result will directly motivate the already-anticipated promotion from VMA OwnerID to load-generation/dependency-set ownership.
