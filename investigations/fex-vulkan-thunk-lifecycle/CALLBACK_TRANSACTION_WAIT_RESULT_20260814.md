# Callback acquisition during a draining unmap transaction — 2026-08-14

This checkpoint records a deterministic full-FEX A/B for a callback invocation that arrives while another thread is already draining the same callback generation for `munmap`.

## Run

Owned-fork workflow:

- repository: `teamleaderleo/FEX`
- branch: `ci/thunk-callback-transactional-retire-20260814`
- run: `31787688318`
- FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`

The test compares:

1. transactional callback retirement whose `TryAcquire()` immediately rejects `Draining`;
2. the same transaction refined so `TryAcquire()` waits while `Draining`, then resolves according to Commit versus Rollback.

## Deterministic three-thread fixture

Callback A acquires the descriptor and blocks inside a native host thunk.

A second thread starts an intentionally invalid unaligned `munmap` whose range covers the callback target. `BeginGuestRangeRetirement()` marks the descriptor `Draining` and waits because A is active.

While that transaction is unresolved, callback B invokes the already-retained host trampoline.

The controller verifies whether B completed, then releases A. The host `munmap` is required to fail with `EINVAL`, causing rollback. A second release byte is already queued so B can complete if rollback wakes it into `Live`.

## Immediate-reject baseline

Observed:

```text
TXWAIT A-entered-host-block
DIAG_CALLBACK_TX_DRAIN_BEGIN ... active=1
DIAG_CALLBACK_TX_DRAIN_WAIT ... active=1
DIAG_CALLBACK_DESCRIPTOR_REVOKED ... state=1 active=1
baseline=113
```

The callback arriving during the transient `Draining` state is immediately treated as dead. Because the underlying `munmap` has not even occurred yet—and later would fail—this is an unnecessary false failure.

## Wait-on-Draining refinement

Observed:

```text
TXWAIT A-entered-host-block
DIAG_CALLBACK_TX_DRAIN_BEGIN ... active=1
DIAG_CALLBACK_TX_DRAIN_WAIT ... active=1
TXWAIT before-release munmap-done=0 B-done=0
TXWAIT released-A-and-queued-B
DIAG_CALLBACK_TX_DRAIN_READY ... active=0
TXWAIT A-returned rv=70053
DIAG_CALLBACK_TX_ROLLBACK ... state=0
DIAG_CALLBACK_TX_ROLLBACK_RANGE ...
DIAG_CALLBACK_DESCRIPTOR_ACQUIRE ... active=1
TXWAIT munmap-returned rc=-1 errno=22
TXWAIT B-returned rv=70063
TXWAIT joined A=70053 B=70063 munmap=-1 errno=22
```

This proves callback B remained blocked while the transaction was unresolved. After the real host `munmap` failed with `EINVAL`, rollback changed the descriptor back to `Live`, woke B, and B acquired/executed normally.

A later valid final close still commits permanent revocation:

```text
DIAG_CALLBACK_TX_COMMIT ...
DIAG_CALLBACK_TX_COMMIT_RANGE ...
DIAG_CALLBACK_DESCRIPTOR_REVOKED ... state=2 active=0
TXWAIT stale-after-close-exit=113
TXWAIT PASS
```

A/B matrix:

```text
baseline=113
wait=0
```

## State-machine conclusion

For callbacks the evidence-backed transaction semantics are now:

```text
Live
  acquire -> Active++

BeginDrain
  Live -> Draining
  new acquisitions WAIT
  wait Active == 0

host munmap

success:
  Draining -> Revoked
  wake waiters -> they observe Revoked and reject

failure:
  Draining -> Live
  wake waiters -> they acquire and execute normally
```

The refinement also makes rollback defensive if an overlapping successful retirement already permanently revoked the descriptor, avoiding drain-request underflow in that case.

This leaves overlapping transactions and wider VM operations (`MAP_FIXED`, `mremap`) as future stress areas, but the observed `munmap` loader path now has executable coverage for identity, active execution, commit/rollback, and concurrent arrivals.
