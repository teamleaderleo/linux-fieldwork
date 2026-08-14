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

## Serial rollback helper

A serial diagnostic implementation is retained in the owned FEX fork:

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

The snapshot stays inside `ThunkHandler_impl` and contains:

```text
for each affected H:
  complete ordered claim vector
  active target

for each affected host->guest callback trampoline:
  cache key {GuestUnpacker, GuestTarget}
  trampoline pointer
  complete embedded TrampolineInstanceInfo
```

For `GuestMmap`, early mmap errors are deferred until after the VMA-tracking lock is released. Then:

```text
host mmap success -> CommitGuestRangeRetirement(token)
host mmap failure -> RollbackGuestRangeRetirement(Thread, token)
```

Rollback restores full claim vectors/active selections and callback trampoline contents, then reactivates each old H through the existing exact H state transition.

## Run 2 — rollback transaction validated

Owned branch:

```text
ci/map-fixed-rollback-transaction-20260814
```

Actions run:

```text
31781459145
job:    94707941815
carrier: f890074f8a1d48931c9ff083101daf4ede5bd637
product base: 71afe476751deac24adabd1adb575fd2337b6e0a
lifetime helper: 96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
job conclusion: success
```

Artifact:

```text
id:      9211977567
name:    map-fixed-rollback-transaction-31781459145
sha256:  ee1399429abeb4efc0ce835a9da7439bcf9819fc1810532a55aa6af9004ddb07
```

Matrix:

```text
rollback-map-fixed-fail=0
rollback-map-fixed=139
rollback-map-fixed-reregister=0
```

### Failed replacement rolls the claim back

The transaction snapshots the live H claim before retirement:

```text
DIAG_ROLLBACK_PREPARE token=0x1 range=0x7ffff7ec4000+0x1000 hosts=1 callbacks=0
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 ...
DIAG_REVOKED_H_INSTALL H=0x700000020000
```

The kernel rejects the replacement. Before returning the syscall error, rollback removes the tombstone/retired definition and restores the old active claim:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000
DIAG_ROLLBACK_RESTORE H=0x700000020000 T=0x7ffff7ec4000 claims=1
DIAG_ROLLBACK_DONE token=0x1 hosts=1 callbacks=0
```

The guest then proves both paths are live:

```text
VMA failed-map-fixed result=MAP_FAILED errno=9 (Bad file descriptor) T=0x7ffff7ec4000 direct-value=111
VMA after-failed-map-fixed H-value=111
```

Exit: `0`.

### Successful replacement commits retirement

For a valid same-address replacement, prepare performs the same retirement and the transaction is committed:

```text
DIAG_ROLLBACK_PREPARE token=0x1 ... hosts=1 callbacks=0
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 ...
DIAG_REVOKED_H_INSTALL H=0x700000020000
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
```

Generation 2 is installed at the same T, but H remains revoked and the run exits `139`. This preserves the successful pre-retire causal result.

### Fresh claim after commit reactivates generation 2

The explicit fresh LinkAddress control commits generation-1 retirement, then registers the new generation:

```text
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
VMA explicit-reregister H=0x700000020000 T=0x7ffff7ec4000 generation=2
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000
DIAG_MULTI_ACTIVE H=0x700000020000 T=0x7ffff7ec4000
VMA after-map-fixed value=222 reregister=1
```

Exit: `0`.

### Resulting transaction invariant

The controlled implementation now demonstrates the desired state transitions:

```text
prepare old mapping destruction
  -> snapshot complete bridge state
  -> retire exact affected H/callback dependencies

syscall succeeds
  -> commit snapshot deletion
  -> old H remains revoked until a fresh claim arrives

syscall fails
  -> restore complete old bridge state
  -> old H resumes the still-live old target
```

This proves transaction integrity separately from owner identity.

## Production concurrency boundary

The serial helper still has a registration race: it snapshots under `ThunksMutex`, releases that lock, then calls the existing retirement path. A new claim can theoretically arrive between snapshot and retirement or before rollback.

Production prepare therefore needs to publish the affected owner/generation as **retiring** atomically with claim mutation. Commit/rollback must validate the same transaction epoch/generation before mutating claims. This is distinct from the peer dispatcher already executing translated H, which still needs quiescence or a generation check at dispatch/bridge entry.

The remaining production layers are now separable:

```text
1. mapping-generation identity       -> owner_id + exact target
2. transaction integrity             -> prepare/commit/rollback + claim-mutation exclusion/epoch
3. future lookup correctness         -> exact H invalidation + revoked/active state (already demonstrated)
4. already-in-flight execution       -> quiescence or generation validation (still open)
```

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
