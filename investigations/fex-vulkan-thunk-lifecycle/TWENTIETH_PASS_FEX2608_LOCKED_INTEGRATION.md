# Twentieth pass — exact FEX-2608 lock-clean integrated runtime

## Scope

This checkpoint runs the combined thunk-lifetime research candidate against the exact FEX-2608 source revision used by the original Apple M5 workload:

```text
e869aa644a16e4332cdc15c1ea0b4d13d482385d
```

The candidate combines pre-unmap ownership retirement, exact synthetic-H definition retirement, coherent ThreadManager lock ordering, exact shared H erase/direct-link delinking, exact H invalidation from every live emulation thread's L1/L2, compatible same-H claim retention/promotion, and host-callback tombstoning plus callback-cache-key removal.

Executed owned-FEX workflow run: `31770578034`.
Artifact: `9208037085`, `thunk-lifetime-integration-fex2608-31770578034`.

## Result matrix

Every reduced case exited 0 on exact FEX-2608:

```text
force.exit=0
aba.exit=0
thread.exit=0
multi.exit=0
```

### Forced-different reload

```text
reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff4fb0c01000
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 thread=0xff4fb0c01000
child retained callback reload exit=113
child Link after re-register rv=1001035
child Link after re-register exit=0
child current callback after new rv=10010093
child current callback after new exit=0
```

The old escaped callback was tombstoned before its guest target/unpacker disappeared, while generation 2 rebound the same native H to its new guest invoker successfully.

### Cross-thread hot-cache retirement

Worker B preheated its H cache on generation 1. Generation 1 then retired and generation 2 moved.

```text
thread-cache preheat rv=1023 want=1023
thread-cache old invoker 0x00007ffff7da21b0 -> unmapped
thread-cache reload invoker old=0x00007ffff7da21b0 new=0x00007ffff7d4c1b0 DIFFERENT
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff0f80c01000
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff0f80c04000
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 thread=0xff0f80c01000
thread-cache post-reload rv=1001035 want=1001035
```

This directly validates all-thread exact retirement on the exact FEX-2608 source.

### Simultaneous same-H owners

Two live same-signature guest DSOs claimed the same native H with distinct guest invokers.

```text
DIAG_MULTI_ACTIVE H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MULTI_STANDBY H=0x7ffff7d80860 T=0x7ffff7d7c1b0
multi-owner active A rv=1023 want=1023
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d7c1b0
DIAG_LOCKED_DEFINITION H=0x7ffff7d80860 handler=1
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff94e0c01000
DIAG_LOCKED_RETIRE H=0x7ffff7d80860 thread=0xff94e0c01000
DIAG_MULTI_PROMOTE H=0x7ffff7d80860 T=0x7ffff7d7c1b0
multi-owner promoted B rv=2001035 want=2001035
```

A was unmapped while B remained executable, and unchanged H reached the promoted B claim.

### Same-address ABA

The same binary also passed the normal same-address reload case (`aba.exit=0`), so callback cache-key removal/tombstoning remains correct when guest numeric addresses are reused.

## Lock-order conclusion

The executed dynamic-PFN retirement path uses the global ThreadManager invalidation discipline rather than the old CustomIRMutex-then-invalidation sequence. The effective transaction is:

```text
ThreadCreationMutex
  -> CodeInvalidationMutex UNIQUE
    -> CustomIR definition removal
    -> exact shared H erase/delink
    -> exact H invalidation in every live thread
```

Runtime `DIAG_LOCKED_DEFINITION` and `DIAG_LOCKED_RETIRE` receipts prove this path executed.

## Implication

The complete reduced repair mechanism is now directly validated on the same FEX source revision as the original Apple M5 teardown investigation. Exact FEX-2608 can support, in one binary, moved-generation dynamic-PFN recovery, same-address callback ABA protection, cross-thread hot-cache retirement, same-H compatible owner promotion, controlled old-callback revocation, and coherent global retirement locking.

This does not by itself prove that the original M5 vulkaninfo terminal transfer was initiated by the dynamic-PFN H path. The original saved fault proves execution reached the old unmapped Vulkan guest-thunk image; the immediate surviving caller remains uncaptured.

## Remaining design work

- Keep a revoked synthetic H recognizable as synthetic instead of falling through to ordinary guest decoding of a native host address.
- Carry a stable signature/ABI identity before generic same-H promotion; this fixture deliberately used same-signature claims.
- Prefer a stable callback descriptor with atomic LIVE/REVOKED state over unsynchronized mutation of raw trampoline fields.
- Treat in-flight/concurrent execution during final retirement separately from the quiescent cross-thread cache case.
- Capture the original M5 final caller if practical.

No upstream FEX interaction was performed. All code and CI work remained on owned repositories.