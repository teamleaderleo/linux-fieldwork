# Active callback lease vs destructive MAP_FIXED

Date: 2026-08-14
Status: deterministic failure; replacement arbitration required
Scope: owned FEX/fieldwork surfaces only

## Result

The first OwnerID-backed callback execution lease successfully delays physical `munmap`, but it does **not** yet protect the pinned mapping from a later destructive `MAP_FIXED` replacement.

Exact hosted ARM64 discriminator:

```text
branch:   ci/callback-lease-map-fixed-discriminator-20260814
head:     a9b44afa3af458fd676305e0a8c0f54fb8fa9c56
run:      31794336952
job:      94747982264
artifact: callback-lease-map-fixed-31794336952
id:       9216849834
sha256:   24e6e8a2a7b0fba207a42d982d5a6359a53c68e87265d55ab68473fe72a290cf
observed runtime exit: 139
```

The Actions job is green because this is an observational discriminator and the workflow records the process result rather than requiring application success.

## Exact ordering

The callback registers against owner generation `0x15`:

```text
DIAG_CALLBACK_OWNER_CREATE owner=0x15
DIAG_CALLBACK_OWNER_ACQUIRE owner=0x15 active=1
INFLIGHT callback-entered-host-block
```

A second guest thread closes the callback DSO. The lease mechanism behaves as designed so far:

```text
DIAG_CALLBACK_OWNER_RETIRE owner=0x15 active=1 defer=1 range=0x7ffff7da1000+0x5000
DIAG_CALLBACK_OWNER_DEFER_HOST_UNMAP range=0x7ffff7da1000+0x5000
INFLIGHT dlclose-returned rc=0
INFLIGHT close-done-before-release=1 target-mapped-before-release=1 unpacker-mapped-before-release=1
```

The callback target and unpacker are still physically present, and the active callback remains blocked inside its host transition.

The test then requests one-page `MAP_FIXED` over the page containing both guest executable addresses:

```text
LEASE_MAP_FIXED start page=0x7ffff7da2000 target=0x7ffff7da2270 unpacker=0x7ffff7da2190
DIAG_MAP_FIXED_PREPARE range=0x7ffff7da2000+0x1000
DIAG_OWNER_MAP_FIXED addr=0x7ffff7da2000 old=0x15 new=0x1a success=1
LEASE_MAP_FIXED returned rv=0x7ffff7da2000 errno=0
LEASE_MAP_FIXED done-before-release=1 rv=0x7ffff7da2000 errno=0
```

So destructive replacement wins while the old owner still has `active=1`.

After the controller releases the callback:

```text
INFLIGHT released-host-block
timeout: the monitored command dumped core
exit=139
```

The callback resumes into executable state that was overwritten after its lease was acquired.

## What this proves

A lease that protects only explicit `munmap` is incomplete.

The protection contract must be attached to **physical destructive replacement of the owner generation**, including at least `MAP_FIXED` and any other path that can replace/unmap leased executable pages.

The runtime invariant should be:

> Once a callback execution lease has successfully acquired generation G, no destructive mapping operation may physically replace any required mapping of G until that lease releases.

This is separate from future-entry retirement. Future entry was already revoked correctly before this replacement occurred.

## Required transaction extension

The existing MAP_FIXED research stack already has prepare/commit/rollback semantics and non-reusable OwnerIDs. The next patch belongs there.

Before physical replacement commits:

```text
PrepareDestructiveReplace(range)
  identify every intersecting owner generation
  ask lifetime owner state whether physical replacement is currently permitted
```

For an active retired generation, acceptable research policies include:

```text
- fail/reject the destructive mapping operation with a defined errno; or
- defer the physical replacement until the final lease releases.
```

Blocking the replacing thread is also mechanically possible, but a product choice should account for loader/syscall expectations. The first candidate should prefer a deterministic nonblocking rejection because it cannot deadlock an active callback that needs the replacing thread to make progress.

The key requirement is that replacement cannot silently overwrite the leased generation.

## Interaction with guest unload acknowledgement

The current callback lease intentionally lets guest `dlclose`/`munmap` bookkeeping return before host physical reclaim so self-unload can succeed.

That means FEX temporarily owns a **retired-but-physically-pinned** mapping that the guest believes it has released.

This state must be represented explicitly in address-space arbitration. Otherwise the next guest `mmap(MAP_FIXED)` sees the range as available from the guest's perspective and can destroy the physical lease backing, as this test demonstrates.

This is a strong argument for moving from callback-local lifetime state to a mapping/load-generation object visible to both thunk retirement and memory syscalls.

## Next gate

Implement one narrow lease-aware MAP_FIXED policy on the synthetic stack:

```text
active owner lease + destructive MAP_FIXED
  -> physical replacement denied/deferred
  -> callback resumes and returns 70053
  -> final lease release reclaims old generation
  -> replacement can then be retried successfully
  -> replacement receives a fresh OwnerID
```

The test should include a retry after lease release so the policy demonstrates temporary lifetime protection rather than permanent address reservation.

After that, extend the same owner-generation arbitration to every destructive transition used by FEX's guest memory layer.
