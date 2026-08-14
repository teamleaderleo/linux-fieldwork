# Transactional callback retirement across failed `munmap` — 2026-08-14

This checkpoint records the causal A/B proving that callback retirement must be transactional around the real host `munmap` syscall.

## Run

Owned-fork workflow:

- repository: `teamleaderleo/FEX`
- branch: `ci/thunk-callback-transactional-retire-20260814`
- run: `31786855535`
- FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`

The fixture uses the same stable callback descriptor and execution-drain machinery as the earlier active-callback proof.

It deliberately calls an **unaligned** `munmap` range that still covers the registered guest callback address from FEX's retirement point of view. Linux rejects that syscall with `EINVAL`, so the guest callback mapping remains valid.

## Eager irreversible retirement baseline

The earlier eager pre-unmap implementation retires the descriptor before the host syscall result is known.

Observed:

```text
DIAG_CALLBACK_DESCRIPTOR_DRAIN_BEGIN ... active=0
DIAG_CALLBACK_DESCRIPTOR_DRAIN_COMPLETE ... active=0
TXFIX failed-munmap ... rc=-1 errno=22
DIAG_CALLBACK_DESCRIPTOR_REVOKED ...
TXFIX child after-failed-munmap exit=113
TXFIX callback-after-failed-munmap-exit=113
```

The mapping is still present and Linux reported `EINVAL`, but the retained host trampoline has already been tombstoned. This is a false revocation caused solely by the failed syscall.

A later real `dlclose` also leaves the old callback revoked, as expected.

## Transactional candidate

The transaction candidate separates retirement into three phases:

```text
BeginGuestRangeRetirement
    mark affected descriptors Draining
    prevent new Live descriptors from escaping the draining range
    wait for Active == 0 outside the global thunk registry lock

host munmap(...)

success -> CommitGuestRangeRetirement
failure -> RollbackGuestRangeRetirement
```

Observed on the same real `EINVAL`:

```text
DIAG_CALLBACK_TX_BEGIN ...
DIAG_CALLBACK_TX_DRAIN_BEGIN ... active=0
DIAG_CALLBACK_TX_DRAIN_READY ... active=0
DIAG_CALLBACK_TX_ROLLBACK ... state=0
DIAG_CALLBACK_TX_ROLLBACK_RANGE ...
TXFIX failed-munmap ... rc=-1 errno=22
DIAG_CALLBACK_DESCRIPTOR_ACQUIRE ... active=1
TXFIX child after-failed-munmap rv=70063
TXFIX child after-failed-munmap exit=0
TXFIX callback-after-failed-munmap-exit=0
```

The still-mapped callback returns to Live and remains callable after the failed syscall.

A later successful final `dlclose` then commits retirement:

```text
DIAG_CALLBACK_TX_BEGIN ...
DIAG_CALLBACK_TX_COMMIT ...
DIAG_CALLBACK_TX_COMMIT_RANGE ...
DIAG_CALLBACK_DESCRIPTOR_REVOKED ...
TXFIX child after-real-close exit=113
TXFIX RESULT after-failed=0 after-close=113
```

## Conclusion

Pre-unmap quiescence and post-unmap revocation are both required, but they cannot be one irreversible operation before the kernel result is known.

For host→guest callback lifetime, the evidence-backed transaction is now:

```text
BeginDrain
    descriptor Live -> Draining
    stop new acquisitions
    wait already-active callbacks

attempt host munmap

if success:
    CommitRevoke
    erase raw callback-cache ownership
    keep escaped old host trampoline as permanent Revoked tombstone

if failure:
    RollbackLive
    preserve raw cache entry
    allow the still-valid mapping/callback generation to continue
```

## Remaining concurrency refinement

The first transaction prototype treats a callback invocation arriving while `Status == Draining` as an immediate rejection. That is safe for successful unmap but unnecessarily observable on a failed transaction.

The stronger semantics are:

- invocation arriving during `Draining` waits for transaction resolution;
- commit wakes it into `Revoked`, so it rejects safely;
- rollback wakes it into `Live`, so it acquires and executes normally.

Commit and rollback must notify these waiters. This should be covered by a deterministic three-thread fixture before calling the callback transaction implementation complete.

Overlapping retirement transactions also need defensive handling so rollback of one transaction cannot underflow a descriptor already permanently Revoked by another successful overlapping transaction.
