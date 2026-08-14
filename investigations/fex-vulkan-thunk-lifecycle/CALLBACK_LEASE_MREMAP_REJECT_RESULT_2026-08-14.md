# Lease-aware destructive mremap result

Date: 2026-08-14
Status: green runtime proof
Scope: owned FEX/fieldwork surfaces only

## Result

The active-callback `MREMAP_FIXED` failure is repaired by applying the same memory-layer arbitration policy already proven for `MAP_FIXED`.

Before the host `mremap()` syscall, FEX asks whether the source guest range belongs to an OwnerID with an active callback execution lease. If so, the destructive remap returns temporary `EBUSY` and leaves both source and destination mappings unchanged.

Observed active-leased path:

```text
owner=0x15 active=1
LEASE_MREMAP start source=0x7ffff7da2000 destination=0x7ffff7ec4000
DIAG_CALLBACK_LEASE_REPLACE_BLOCK owner=0x15 active=1 range=0x7ffff7da2000+0x1000
DIAG_CALLBACK_LEASE_MREMAP_REJECT ... flags=0x3 errno=16
LEASE_MREMAP returned rv=MAP_FAILED errno=16 source-mapped=1 destination-mapped=0
LEASE_MREMAP ACTIVE_REJECT_OK
```

The callback then resumes normally. Final release reclaims the retired owner generation, and the stale callback still follows controlled revoke:

```text
DIAG_CALLBACK_OWNER_RELEASE owner=0x15 active=0 deferred=1
DIAG_CALLBACK_OWNER_RECLAIM_DONE owner=0x15 ... result=0
INFLIGHT worker-returned rv=70053
INFLIGHT joined worker=70053 close=0
INFLIGHT mapped-after-release target=0 unpacker=0
DIAG_CALLBACK_OWNER_REVOKED owner=0x15 ... state=1 active=0
INFLIGHT child stale-first-callback exit=113
```

The same process performs a destructive `MREMAP_FIXED` on an unrelated anonymous mapping and it succeeds:

```text
LEASE_MREMAP control rv=0x7ffff7ec3000 errno=0 destination=0x7ffff7ec3000
LEASE_MREMAP UNLEASED_CONTROL_OK
```

This proves the guard is scoped to active callback owner leases rather than disabling guest remap globally.

## Exact receipt

```text
FEX branch: ci/callback-lease-mremap-reject-20260814
head:       195f53d98534efbefba1ad4f45b2ceeac73b1c49
run:        31796804562
job:        94755562775
result:     success
artifact:   callback-lease-mremap-reject-31796804562
artifact id: 9217782046
sha256:     c9b532ce14896c458e0ada34c0fd0abeb8116312d91c8c2328bdb0cfdc1cfa20
process rc: 0
marker:     CALLBACK_LEASE_MREMAP_REJECT_OK
```

## Policy demonstrated

For the current research model:

```text
mremap source has active execution lease
AND old_size != 0
AND operation may remove/move source (no MREMAP_DONTUNMAP)
    -> reject before host syscall with EBUSY
```

`MREMAP_DONTUNMAP` remains a separate semantic case because Linux retains the source mapping.

## Architectural consequence

Execution lifetime is now demonstrably a memory-management contract, not merely a thunk-registry contract.

The same shared range/owner query is sufficient to arbitrate two independently reproduced destructive operations:

- `MAP_FIXED` replacement;
- destructive `mremap` / `MREMAP_FIXED` source removal.

The next direct executable hazard is protection-destructive `mprotect`, especially removal of `PROT_EXEC` from a page while a callback generation has an active lease. `shmdt` remains another physical-removal path to test separately.
