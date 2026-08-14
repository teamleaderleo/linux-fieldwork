# Failed `MAP_FIXED` retirement rollback log

Date: 2026-08-14

## Starting point

[`MAP_FIXED_PRE_RETIRE_LOG.md`](./MAP_FIXED_PRE_RETIRE_LOG.md) proved the required successful-replacement order:

```text
retire H dependency before MAP_FIXED destroys generation 1
-> leave H revoked
-> same-address generation 2 cannot inherit H
-> explicit fresh LinkAddress claim can reactivate H
```

The causal pre-retire helper intentionally has no rollback if the kernel rejects the replacement. This log tests that transactional gap directly.

## Failed-syscall discriminator

Owned FEX branch:

```text
ci/map-fixed-failure-rollback-20260814
```

Probe commit:

```text
c800b31ec4970881e7566724e459b916e6aceed3
```

Workflow carrier:

```text
b03ca7f31da78531d0505a1f55992fe61d5d7574
```

Actions run:

```text
31781044914
```

The new `map-fixed-fail` mode does:

```text
map executable T with code returning 111
register H -> T
H() == 111
attempt mmap(T, page, PROT_READ, MAP_PRIVATE|MAP_FIXED, fd=-1, offset=0)
```

The request deliberately omits `MAP_ANONYMOUS` while using `fd=-1`, so Linux should reject the file-backed mmap. A failed mmap must leave the existing mapping at T intact.

Immediately after the syscall failure, before calling H, the probe executes T directly and requires:

```text
direct T() == 111
```

That is the key control. If direct T remains valid but H is revoked, the failure is specifically a lost thunk-claim transaction rather than destruction of guest code.

## Expected discriminator

Current integrated lifetime candidate, without the pre-MAP_FIXED helper:

```text
kernel rejects replacement
old mapping remains
H remains active
H() == 111
exit 0
```

Current candidate + pre-MAP_FIXED retirement without rollback:

```text
prepare retires H
kernel rejects replacement
old mapping remains and direct T() == 111
H remains revoked because no rollback exists
H call faults / cannot return 111
```

A green discriminator establishes that production prepare/commit/rollback is required independently of mapping-generation identity.

## Rollback requirement

Rollback must restore the complete affected claim state, not only the previously active target. For each affected H it needs the original ordered claim set plus active selection, because later owner retirement/promotion semantics depend on standby ordering.

A controlled diagnostic rollback can snapshot this state in the single-thread test. Production needs synchronization so new claims cannot race between prepare and rollback.

## Staged rollback helper

A serial diagnostic implementation is staged on the owned FEX branch:

```text
.github/fieldwork/add_map_fixed_rollback_transaction.py
commit: 5a9f56bbe63aee963229e61fdb20ecfcd14a25b3
```

It is intentionally not wired into run `31781044914`; that run remains a clean no-rollback discriminator.

The helper adds an opaque transaction-token API to `ThunkHandler`:

```text
PrepareGuestRangeRetirement(Thread, Base, Length) -> token
CommitGuestRangeRetirement(token)
RollbackGuestRangeRetirement(Thread, token)
```

The snapshot is kept inside `ThunkHandler_impl` and contains:

```text
for each affected H:
  complete ordered claim vector
  active target

for each affected host->guest callback trampoline:
  cache key {GuestUnpacker, GuestTarget}
  trampoline pointer
  complete embedded TrampolineInstanceInfo
```

`PrepareGuestRangeRetirement()` snapshots this state, then calls the already-proven `RetireGuestRange()` path. Therefore successful retirement semantics stay exactly the same.

For `GuestMmap`, the helper converts the early mmap-failure returns into a deferred result so the VMA-tracking lock is released first. Then:

```text
host mmap success -> CommitGuestRangeRetirement(token)
host mmap failure -> RollbackGuestRangeRetirement(Thread, token)
```

Rollback restores the full claim vectors/active selections and callback trampoline contents, then reactivates each old H through the existing exact H state transition.

### Diagnostic concurrency boundary

This staged implementation is deliberately serial. If a new guest LinkAddress/callback claim appears between prepare and rollback, restoring the snapshot could overwrite that concurrent mutation. It emits a conflict diagnostic for H state but does not solve that race.

Production needs a transaction epoch or lock that excludes/merges claim mutations across prepare/commit/rollback, plus the separate in-flight dispatcher quiescence solution.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
