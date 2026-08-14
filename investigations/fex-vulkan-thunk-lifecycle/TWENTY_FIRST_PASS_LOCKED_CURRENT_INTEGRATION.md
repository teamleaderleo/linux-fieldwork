# Twenty-first pass — current FEX lock-clean integrated runtime

## Scope

This checkpoint repeats the combined lifetime repair matrix on current reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a` after replacing the earlier diagnostic lock inversion with one coherent retirement transaction.

Owned-FEX branch: `ci/thunk-lifetime-integration-20260814`.
Carrier commit: `0436d8420084024043a60c86eef8316c94a0bce2`.
Workflow run: `31770676007`.
Artifact: `9208068787`, `thunk-lifetime-integration-31770676007`.

The same binary executes forced-different reload, same-address ABA, cross-thread hot-cache retirement, and simultaneous same-H owner promotion.

## Result

All four cases exit 0:

```text
force.exit=0
aba.exit=0
thread.exit=0
multi.exit=0
```

The forced-different case exercises both independent lifetime directions:

```text
DIAG_INTEGRATED_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c000 ...
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 ...
child retained callback reload exit=113
child Link after re-register rv=1001035
child Link after re-register exit=0
child current callback after new rv=10010093
child current callback after new exit=0
```

The cross-thread case invalidates H from both live guest threads before generation 2 is used and returns the expected generation-2 result.

The simultaneous-owner case retains B as a compatible standby claim, exact-retires A, promotes B, and reaches B through the unchanged native H.

The same-address callback case also remains green, so old callback pointers stay revoked while new callback state survives numeric guest-address reuse.

## Lock-order result

Unlike integrated v1, this run uses the refined transaction:

```text
ThreadCreationMutex
  -> CodeInvalidationMutex UNIQUE
    -> CustomIR definition removal
    -> exact shared H erase/direct-link delink
    -> exact H invalidation in every live emulation thread
```

The transformed FEX/FEXServer build completed and the runtime matrix exercised `DIAG_LOCKED_DEFINITION` / `DIAG_LOCKED_RETIRE`, so the lock-order refinement is not compile-only.

Together with `TWENTIETH_PASS_FEX2608_LOCKED_INTEGRATION.md`, the same integrated mechanism is now runtime-green on both exact FEX-2608 and the current reviewed source snapshot.

## Research baseline

This lock-clean integrated candidate supersedes the earlier integrated v1 as the current owned-fork research baseline.

It remains diagnostic/research code rather than an upstream-submittable patch. The next product-semantic experiment is a revoked synthetic-H state so a stale native host pointer remains recognized as synthetic instead of falling through to ordinary x86 decoding at a native host address.

No upstream FEX interaction was performed.