# Twenty-third pass — failed-munmap retirement A/B

## Scope

The lifetime repair needs to retire guest-address dependencies before physical unmap. This checkpoint tests the obvious transaction hazard: what happens if FEX revokes bridges first and the guest `munmap` then fails?

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX branch: `ci/thunk-failed-munmap-20260814`.
Workflow run: `31771290850`.

Three variants use the same full-thunk fixture:

- `stock`: no lifetime retirement changes;
- `eager`: lock-clean pre-unmap retirement without syscall validity guard;
- `guarded`: same retirement logic, but only after basic `munmap` validity checks (nonzero length and page-aligned address).

The guest DSO is loaded, H -> T is registered and called successfully, then the guest intentionally issues an unaligned `munmap` whose range numerically contains T. Linux returns `EINVAL`; the physical DSO mapping remains executable. The fixture then calls H again in a child.

## Stock control

Artifact: `9208286764`, `thunk-failed-munmap-stock-31771290850`.

```text
failed-munmap pre-call           rv=1023 want=1023
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    0x00007ffff7da21b0 -> ... r-xp .../liblifetime-guest.so
failed-munmap child status       0
```

The failed syscall leaves both T and the existing H route live.

## Eager retirement negative control

Artifact: `9208283698`, `thunk-failed-munmap-eager-31771290850`.

The physical syscall fails identically and T remains executable:

```text
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    0x00007ffff7da21b0 -> ... r-xp .../liblifetime-guest.so
```

But the pre-unmap hook has already committed retirement against the numerically overlapping invalid range:

```text
DIAG_MULTI_DROP H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da2001+0x1000
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 ...
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 ...
```

The post-failure H call then dies:

```text
failed-munmap child status       139
```

This is a direct correctness bug in naive eager pre-unmap retirement: a failed guest memory operation can revoke a still-live thunk owner.

## Guarded positive variant

Artifact: `9208283937`, `thunk-failed-munmap-guarded-31771290850`.

The same invalid syscall again returns `EINVAL` and T remains executable:

```text
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    0x00007ffff7da21b0 -> ... r-xp .../liblifetime-guest.so
failed-munmap child status       0
```

No bridge-retirement trace occurs for the invalid unaligned range. The later legitimate DSO close still reaches the ordinary valid retirement path, which is why valid-range `DIAG_MULTI_DROP` / `DIAG_LOCKED_RETIRE` lines appear later in stderr.

## Conclusion

Pre-unmap retirement must be a real transaction, not an unconditional callback before the host memory operation.

At minimum, FEX must avoid committing retirement for guest `munmap` requests that are known invalid before the host call. The tested basic validity guard restores stock semantics for the unaligned `EINVAL` case while preserving later legal retirement.

A production design still needs to decide how it handles any failure that remains possible after prevalidation:

```text
validate / prepare
  -> block/revoke future bridge acquisition
  -> attempt physical mapping transition
  -> commit retirement if successful
  -> rollback or restore owner state if the mapping transition fails
```

If Linux/FEX can prove that all remaining failure modes are excluded by cheap prevalidation, rollback may be unnecessary; this checkpoint does not establish that broader claim.

The safety rule is now two-sided:

```text
never unmap live T while H/callback state can still reach it
AND
never retire H/callback state while T remains live because the mapping operation failed
```

No upstream FEX interaction was performed.