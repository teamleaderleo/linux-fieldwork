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

The new `map-fixed-fail` mode does:

```text
map executable T with code returning 111
register H -> T
H() == 111
attempt mmap(T, page, PROT_READ, MAP_PRIVATE|MAP_FIXED, fd=-1, offset=0)
```

The request deliberately omits `MAP_ANONYMOUS` while using `fd=-1`, so Linux rejects the file-backed mmap. A failed mmap leaves the existing mapping at T intact.

Immediately after the syscall failure, before calling H, the probe executes T directly and requires:

```text
direct T() == 111
```

That is the key control. If direct T remains valid but H is revoked, the failure is specifically a lost thunk-claim transaction rather than destruction of guest code.

## Run 1 — rollback requirement reproduced

Actions run:

```text
31781044914
job:    94706681470
carrier: b03ca7f31da78531d0505a1f55992fe61d5d7574
product base: 71afe476751deac24adabd1adb575fd2337b6e0a
lifetime helper: 96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
job conclusion: success
```

Artifact:

```text
id:      9211850909
name:    map-fixed-failure-rollback-31781044914
sha256:  45deb9daa8068b91fa6d89b81c31871ed579715e59689406c606e821627ad5f5
```

Matrix:

```text
current-fail=0
pre-retire-no-rollback-fail=139
```

### Current lifetime candidate — failed mmap leaves H intact

The current candidate has no pre-MAP_FIXED retirement hook, so the rejected syscall does not change bridge state:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000
DIAG_MULTI_ACTIVE H=0x700000020000 T=0x7ffff7ec4000
VMA first H=0x700000020000 T=0x7ffff7ec4000 value=111
VMA failed-map-fixed result=MAP_FAILED errno=9 (Bad file descriptor) T=0x7ffff7ec4000 direct-value=111
VMA after-failed-map-fixed H-value=111
```

Exit: `0`.

This establishes the guest/kernel side of the control: the rejected operation leaves T mapped and executable with its original code.

### Pre-retire without rollback — old guest code survives, H is lost

The causal successful-replacement helper prepares the exact same one-page target range before the kernel sees the invalid mmap:

```text
DIAG_MAP_FIXED_PREPARE range=0x7ffff7ec4000+0x1000
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 range=0x7ffff7ec4000+0x1000
DIAG_MULTI_RETIRE H=0x700000020000 OLD=0x7ffff7ec4000 NEW=0
DIAG_LOCKED_DEFINITION H=0x700000020000 handler=1
DIAG_REVOKED_H_INSTALL H=0x700000020000
DIAG_LOCKED_RETIRE H=0x700000020000
```

The host mmap then fails with `EBADF`, and the direct guest target proves the old mapping is still valid:

```text
VMA failed-map-fixed result=MAP_FAILED errno=9 (Bad file descriptor) T=0x7ffff7ec4000 direct-value=111
```

But H remains tombstoned:

```text
DIAG_REVOKED_H_COMPILE H=0x700000020000
```

The process exits `139` when it calls H.

This isolates the failure cleanly:

```text
kernel/VMA state after failed syscall: generation 1 still live, T() == 111
bridge state after failed syscall:      generation-1 claim removed, H revoked
```

Therefore a pre-destructive retirement design requires rollback when the destructive syscall fails. This requirement is independent of mapping-owner identity: even perfect owner IDs would still lose a valid live claim if prepare is destructive and failure is not rolled back.

## Rollback requirement

Rollback must restore the complete affected claim state, not only the previously active target. For each affected H it needs the original ordered claim set plus active selection, because later owner retirement/promotion semantics depend on standby ordering.

It also needs to restore callback trampoline state if prepare tombstoned a bridge whose guest unpacker/target fell in the candidate range.

## Staged rollback helper

A serial diagnostic implementation is staged on the owned FEX branch:

```text
.github/fieldwork/add_map_fixed_rollback_transaction.py
commit: 5a9f56bbe63aee963229e61fdb20ecfcd14a25b3
```

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

## Run 2 — rollback transaction validation launched

Owned branch:

```text
ci/map-fixed-rollback-transaction-20260814
```

Workflow carrier:

```text
f890074f8a1d48931c9ff083101daf4ede5bd637
```

Actions run:

```text
31781459145
```

The final transaction candidate runs three controls:

```text
map-fixed-fail
map-fixed
map-fixed-reregister
```

Required result:

```text
failed replacement      -> rollback restores H -> 111, exit 0
successful replacement  -> commit keeps H revoked, must never execute generation 2
successful + new claim  -> commit then explicit LinkAddress reactivates H -> 222, exit 0
```

### Diagnostic concurrency boundary

This staged implementation is deliberately serial. If a new guest LinkAddress/callback claim appears between prepare and rollback, restoring the snapshot could overwrite that concurrent mutation. It emits a conflict diagnostic for H state but does not solve that race.

Production needs a transaction epoch or lock that excludes/merges claim mutations across prepare/commit/rollback, plus the separate in-flight dispatcher quiescence solution.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
