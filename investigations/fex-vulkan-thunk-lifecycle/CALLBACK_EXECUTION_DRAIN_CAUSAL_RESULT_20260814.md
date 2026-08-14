# Host→guest callback execution-drain causal A/B — 2026-08-14

This checkpoint records the first full-FEX deterministic proof that callback revocation alone is insufficient once a host→guest callback is already executing, and that an execution drain closes that race.

## Run

Owned-fork workflow:

- repository: `teamleaderleo/FEX`
- branch: `ci/thunk-callback-descriptor-drain-20260814`
- run: `31785643435`
- FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`
- retained synthetic thunk pair from this Fieldwork investigation, checksum-verified

The workflow built two FEX variants from the same source and fixture:

1. **descriptor-only baseline** — stable callback descriptor with `Live/Revoked`, raw-cache retirement, all-thread lookup/cache invalidation, but no active execution ownership;
2. **descriptor + drain candidate** — adds `Live/Draining/Revoked`, active execution count, acquire/release around the complete `CallCallbackDescriptor → HandleCallback → return` scope, and waits for active callbacks only after releasing the global thunk registry lock.

## Deterministic race

The guest callback target performs a thunk call into native host code. The native host thunk:

1. signals that the callback has entered the host block;
2. waits on a pipe while the guest callback frame remains active;
3. returns only when the controller releases it.

A second guest thread performs final `dlclose()` while the callback is blocked. The controller waits 300 ms before releasing the host thunk and records whether `dlclose()` has already returned.

This deterministically recreates the dangerous lifetime window: native host code will eventually return into guest callback/unpacker code owned by the DSO whose final loader reference is being removed.

## Descriptor-only baseline

Observed:

```text
INFLIGHT callback-entered-host-block
DIAG_CALLBACK_DESCRIPTOR_RETIRE ...
INFLIGHT dlclose-returned rc=0
INFLIGHT close-done-before-release=1
INFLIGHT released-host-block
baseline=139
```

The final `dlclose()` completed while the callback was still active. When the blocked host call was released, execution had to return into unmapped guest code and the FEX process terminated with SIGSEGV / exit 139.

This directly falsifies "revocation + cache invalidation is enough" for an already-active host→guest callback.

## Descriptor + execution drain candidate

Observed:

```text
DIAG_CALLBACK_DESCRIPTOR_ACQUIRE ... active=1
INFLIGHT callback-entered-host-block
DIAG_CALLBACK_DESCRIPTOR_DRAIN_BEGIN ... active=1
DIAG_CALLBACK_DESCRIPTOR_DRAIN_WAIT ... active=1
INFLIGHT close-done-before-release=0
INFLIGHT released-host-block
DIAG_CALLBACK_DESCRIPTOR_DRAIN_COMPLETE ... active=0
INFLIGHT worker-returned rv=70053
INFLIGHT dlclose-returned rc=0
INFLIGHT joined worker=70053 close=0
DIAG_CALLBACK_DESCRIPTOR_REVOKED ... active=0
INFLIGHT child stale-first-callback exit=113
INFLIGHT DRAIN_PASS
drain=0
```

The candidate enforced the required ordering:

```text
callback lease acquire
    → retirement marks descriptor Draining
    → new callback acquisitions rejected
    → final unload waits while Active=1
    → already-active callback returns normally
    → Active becomes 0
    → retirement completes / descriptor becomes Revoked
    → dlclose may finish and owner may unmap
    → escaped old trampoline remains safely rejected
```

## Regression coverage

A separate descriptor+drain matrix run (`31785267928`) remained green for:

- forced-different-address reload;
- same-address ABA reload;
- thread-cache reuse;
- multiple callback owners.

Thus the active-drain state machine did not regress the already-proven descriptor generation/revocation behavior.

## Design conclusion

For host→guest callbacks whose `GuestUnpacker` or `GuestTarget` belongs to an unloadable guest mapping, the minimum complete lifetime mechanism now has executable support for all three requirements:

1. **stable identity** — an escaped host trampoline carries a stable FEX-owned descriptor, so same-address reload cannot ABA into a new owner generation;
2. **revocation** — retirement rejects new uses of an old descriptor and leaves escaped old host pointers safely tombstoned;
3. **execution quiescence** — final unmap must wait until callbacks that acquired the descriptor before retirement have left the complete FEX callback scope.

The descriptor object itself is sufficient as a generation token for this callback design; a separate `MappedResource` generation counter is not required for the first implementation so long as retirement reliably maps guest address ranges to all descriptors that depend on them.

## Remaining production requirement: transactional unmap

Current research retirement begins before the host `munmap`, which is necessary to close the select→unmap race. A separate failed-`munmap` A/B has already shown that irrevocable eager retirement is wrong if the syscall fails.

Production ordering therefore needs a transaction:

```text
BeginDrain(range)
  mark affected descriptors Draining
  reject new acquisitions
  wait Active == 0

host munmap(...)

if success:
  CommitRevoke()
  erase raw cache entries / finalize tombstones
else:
  RollbackLive()
  restore registrations needed for the still-valid mapping
```

Waiting must not hold the global thunk registry mutex because an already-active callback may itself invoke another thunk while draining.
