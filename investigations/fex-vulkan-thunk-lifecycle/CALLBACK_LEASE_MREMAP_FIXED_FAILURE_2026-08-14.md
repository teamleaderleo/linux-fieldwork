# Active callback lease vs MREMAP_FIXED

Date: 2026-08-14
Status: reproduced lifetime violation; repair candidate running
Scope: owned FEX/fieldwork surfaces only

## Result

`GuestMremap` is another destructive memory path that can invalidate an already-entered callback generation before its execution lease releases.

The existing OwnerID callback lease successfully pins the retired guest thunk owner against ordinary `munmap`/`dlclose`. The discriminator then performs a forced one-page `MREMAP_FIXED` of the callback target page while owner `0x15` still has `active=1`.

Observed sequence:

```text
DIAG_CALLBACK_OWNER_CREATE owner=0x15
DIAG_CALLBACK_OWNER_ACQUIRE owner=0x15 active=1
INFLIGHT callback-entered-host-block
DIAG_CALLBACK_OWNER_RETIRE owner=0x15 active=1 defer=1 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_OWNER_DEFER_HOST_UNMAP range=0x7ffff7da1000+0x5000
INFLIGHT dlclose-returned rc=0
INFLIGHT close-done-before-release=1 target-mapped-before-release=1 unpacker-mapped-before-release=1

LEASE_MREMAP start source=0x7ffff7da2000 destination=0x7ffff7ec4000 target=0x7ffff7da2270 unpacker=0x7ffff7da2190
LEASE_MREMAP returned rv=0x7ffff7ec4000 errno=0 source-mapped=0 destination-mapped=1

INFLIGHT released-host-block
process exit = 139
```

The host `mremap()` succeeds before any lease arbitration, removes the source page, and the paused callback later resumes into an address whose executable generation has been moved away.

## Exact receipt

```text
FEX branch: ci/callback-lease-mremap-discriminator-20260814
head:       39dac0aa770fa540f66147f2837d6d7ae2616b1e
run:        31795808445
job:        94752555092
workflow:   success (observational discriminator)
process rc: 139
artifact:   callback-lease-mremap-31795808445
artifact id: 9217406870
sha256:     23762111e2c2e6b1bcee5d74f283c51f3e753b3d40b54d6d1ac7caae22574919
```

## Interpretation

Execution leases must arbitrate every operation that can physically remove, move, replace, or make unusable the leased executable generation. Protecting only the guest `munmap` path is insufficient.

For `mremap`, the conservative first policy is:

```text
old_size != 0
AND operation may remove/move source (no MREMAP_DONTUNMAP)
AND source OwnerID has active execution lease
    -> return temporary EBUSY before host mremap
```

`MREMAP_DONTUNMAP` needs a separate semantic audit because the source mapping remains present.

## Repair candidate

A separate branch keeps this 139 discriminator immutable and tests the memory-layer policy:

```text
branch: ci/callback-lease-mremap-reject-20260814
head at launch: 195f53d98534efbefba1ad4f45b2ceeac73b1c49
run: 31796804562
```

The candidate requires:

1. leased destructive `mremap` returns `EBUSY` before the host syscall;
2. source mapping remains present and destination remains absent;
3. callback completes normally and final release reclaims the retired owner;
4. stale callback still takes controlled revoke (`113`);
5. an unrelated anonymous `MREMAP_FIXED` succeeds in the same process, proving the guard is scoped to active owner leases.

## Related memory-layer audit

The same audit identified `shmdt` and protection-destructive `mprotect` as additional paths that currently change host memory state before callback-owner lifetime arbitration. Those should be tested independently after the mremap policy is established.
