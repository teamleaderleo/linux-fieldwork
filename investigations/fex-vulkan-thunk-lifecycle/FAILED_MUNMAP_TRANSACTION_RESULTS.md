# Failed-munmap retirement transaction result

## Purpose

A true guest-thunk physical-unload design needs to retire every bridge that can still reach the retiring guest code *before* the code disappears. That sounds like a straightforward ordering fix until the underlying mapping operation itself fails.

This experiment tests that failure boundary directly.

The result adds a separate correctness requirement to generation identity, translated-cache coherence, and execution quiescence:

> **bridge retirement must participate in the success/failure transaction of the physical owner teardown.**

An attempted `munmap()` is not proof that the owner is going away.

## Carrier and exact source under test

Owned FEX carrier branch:

`ci/thunk-failed-munmap-20260814`

Carrier commit:

`48b5cb33a49f0b3af70c1743fec016ff196e933e`

Workflow:

`.github/workflows/thunk-failed-munmap-arm64.yml`

Actions run:

`31771290850`

FEX source under test:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Runner:

GitHub-hosted `ubuntu-24.04-arm` / AArch64.

The workflow constructs the generic full-thunk lifetime fixture and deliberately attempts a `munmap()` that fails with `EINVAL`. The old guest invoker mapping remains present and executable. A child then calls the already-established native-H bridge again.

Three modes are compared:

1. **stock** — no pre-unmap bridge retirement;
2. **eager** — retire bridges before knowing whether the underlying mapping operation will succeed;
3. **guarded** — reject the deliberately invalid unmap request before bridge retirement, preserving the live owner.

## Common physical result

All modes verify the same kernel-level outcome:

```text
failed-munmap pre-call           rv=1023 want=1023
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    <T1> -> ... r-xp .../liblifetime-guest.so
```

So the key experimental condition is unambiguous:

```text
munmap request failed
AND
old guest bridge code T1 remains executable/mapped
```

The question is solely whether the bridge layer incorrectly commits logical retirement anyway.

## Stock control

Observed:

```text
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    0x00007ffff7da21b0 -> ... r-xp .../liblifetime-guest.so
failed-munmap child status       0
```

The retained native-H bridge remains usable because neither the mapping nor the bridge ownership was retired.

Result:

```text
stock -> child Link after failed munmap exits 0
```

## Eager pre-unmap retirement

The eager diagnostic sees the attempted range and retires the matching owner claim before the kernel result is known.

Representative diagnostic lines:

```text
DIAG_MULTI_ACTIVE H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MULTI_DROP H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da2001+0x1000
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=<thread>
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 ...
```

But the kernel rejects the unmap:

```text
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    0x00007ffff7da21b0 -> ... r-xp .../liblifetime-guest.so
```

The subsequent child bridge call gets SIGSEGV / status 139.

Result:

```text
eager -> child Link after failed munmap => 139
```

This is an especially important negative control because the guest bridge code is still physically valid. The failure was created entirely by committing bridge retirement for a teardown that never happened.

## Guarded preflight

The guarded variant adds a basic validity check before the pre-unmap retirement path. The deliberately invalid mapping request is rejected as a retirement trigger.

Observed:

```text
failed-munmap pre-call           rv=1023 want=1023
failed-munmap syscall            rc=-1 errno=22 (Invalid argument)
failed-munmap invoker remains    0x00007ffff7da21b0 -> ... r-xp .../liblifetime-guest.so
failed-munmap child status       0
```

Result:

```text
guarded -> child Link after failed munmap exits 0
```

Later valid owner teardown can still run ordinary retirement diagnostics; the crucial point is that the failed request does not destroy the still-live bridge before the child reuses it.

## Exact A/B matrix

```text
                           kernel result        T1 mapping       later retained Link
stock                      EINVAL / no unmap    still r-xp       exit 0
eager pre-retirement       EINVAL / no unmap    still r-xp       exit 139
guarded preflight          EINVAL / no unmap    still r-xp       exit 0
```

## Design conclusion

A raw pre-`munmap` hook has an unavoidable commit problem if it performs irreversible bridge retirement:

```text
retire first
    -> safe if unmap succeeds
    -> WRONG if unmap fails: live code loses its bridge

unmap first
    -> outcome is known
    -> TOO LATE for safe retirement: another thread can select/execute old code after physical destruction
```

The earlier in-flight experiments already prove that physical destruction cannot simply happen first and be cleaned up afterward. This failed-munmap experiment proves that irreversible bridge destruction cannot blindly happen first either.

Therefore true physical reclamation needs a transaction with at least two conceptual phases.

## Two-phase owner teardown model

A stronger conceptual protocol is:

```text
PREPARE owner generation G
    -> mark G draining
    -> prevent new bridge acquisitions for G
    -> tombstone escaped callbacks in a reversible/stable way
    -> prepare H claim retirement/rebind
    -> invalidate future translated acquisitions
    -> drain already-selected/already-entered G executions

COMMIT physical teardown
    -> perform/complete the actual mapping teardown
    -> only once owner destruction is guaranteed, finalize G retirement

ABORT / ROLLBACK
    -> if physical teardown cannot proceed, restore/re-enable G's bridge availability
       without changing G identity or silently promoting the wrong generation
```

A real implementation may choose different internal mechanics, but it needs equivalent semantics.

## Why a simple syscall-level guard is only a discriminator

The guarded diagnostic proves one narrow point: a known-invalid request can be screened before destructive retirement.

It is not a complete unload implementation. Real owner teardown can fail or become partial for reasons more complex than the synthetic invalid-range request, and a DSO can own multiple mappings/segments. A production physical-unload design therefore needs owner-level transaction semantics rather than a growing list of syscall-shape checks.

## Where the ownership event should live

This result weakens the idea that raw guest `munmap()` is the ideal primary lifecycle owner.

`munmap()` knows about address ranges. It does not inherently know:

- which guest thunk generation owns the range;
- whether this is the final mapping for that logical owner;
- which H claims and callback trampolines belong to that generation;
- whether another loader namespace has an independent owner;
- whether teardown is committed or will abort;
- whether all in-flight bridge executions have drained.

A dynamic-loader/guest-thunk ownership layer has more semantic information and can begin a drain before physical mapping removal. The actual mapping operation then becomes the commit boundary rather than the owner-discovery mechanism.

## Effect on the design choice

This result raises the cost of Contract B (true physical unload/reload) again.

A correct Contract B now needs at least:

1. generation/epoch identity to defeat ABA;
2. owner-aware bridge claims rather than raw addresses;
3. coherent invalidation of shared and every-thread translated H routes;
4. stable/tombstonable escaped host callbacks;
5. execution quiescence for already-selected/already-entered calls;
6. transactional prepare/commit/abort semantics around physical teardown;
7. likely multi-owner claim promotion when the same stable H has more than one live guest owner.

Contract A (`DF_1_NODELETE`) avoids this transaction because the generated guest bridge owner never reaches the dangerous physical-unmap state during process lifetime.

Contract C (stable resident bridge runtime + unloadable wrapper-specific state) also avoids making escaped/generated executable bridge identities part of the wrapper's reclamation transaction, while preserving physical reset for state that genuinely needs it.

## Next discriminators

1. **Multi-owner promotion:** two simultaneously live guest owner generations/contexts claim the same stable native H with different guest targets; retire one and verify the surviving claim is promoted rather than H being globally revoked.
2. **Loader namespaces:** repeat equivalent ownership collisions through `dlmopen()` namespaces and determine whether current process-global H-key state conflates logically independent owners.
3. **Already-entered execution:** block a worker while physically executing in old guest bridge code and try to retire/unmap its owner from another thread.
4. **Partial owner teardown:** model an owner containing multiple relevant mapped ranges and fail teardown after some preparatory work, testing rollback semantics beyond a single invalid range.
5. **FEX-native split bridge runtime:** move generated signature-adapter execution into stable process-owned code and test real H reuse, changed-base reload, same-address reload, callbacks, and concurrency.

## Current interpretation

The generic evidence now says true thunk reclamation is not an `erase()` problem and not merely an invalidation problem. It is a distributed lifetime transaction spanning loader ownership, escaped bridge objects, translated code, every executing FEX thread, and the eventual physical mapping commit.

That is a much higher implementation burden than the original teardown crash suggested, and it is a strong reason to demand a concrete compatibility requirement before choosing physical bridge-code reclamation over residency.