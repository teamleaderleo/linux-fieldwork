# Nineteenth pass — integrated lifetime repair runtime matrix

## Scope

This checkpoint combines the independently proven thunk-lifetime mechanisms in one FEX binary and asks whether they coexist without breaking each other.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier branch: `ci/thunk-lifetime-integration-20260814`.

Carrier head for this run: `bc015d56b3b0c4bbfde07e11c23ef15ad3779a48`.

Workflow run: `31769979468`.

Artifact: `9207813972`, `thunk-lifetime-integration-31769979468`.

All four reduced regression cases ran against the same compiled FEX executable.

## Integrated diagnostic

The build combines:

1. exact synthetic-H retirement from the CustomIR definition, shared compiled map/direct links, and every live emulation thread's L1/L2;
2. pre-unmap H-to-guest-target ownership tracking;
3. retained same-H live claims with promotion of a compatible standby claim when the active owner retires;
4. callback trampoline revocation in the same guest-range retirement hook;
5. callback cache-key removal so same-address guest reload cannot ABA-reuse a revoked host trampoline.

This is still research/diagnostic code. It is not presented as an upstream-submittable patch.

## Result matrix

Every case exited 0:

```text
force.exit=0
aba.exit=0
thread.exit=0
multi.exit=0
```

### Forced-different unload/reload

Generation 1 and generation 2 guest invokers were forced to different addresses:

```text
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7d781b0 DIFFERENT
```

The outgoing callback dependency and dynamic H claim were retired before the old guest mapping disappeared:

```text
DIAG_INTEGRATED_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c000 unpacker=0x7ffff7da2190 target=0x7ffff7da2170 range=0x7ffff7da1000+0x5000
DIAG_MULTI_DROP H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xffd760c01000
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
```

The old escaped callback pointer reached the controlled FEX-owned revoked path:

```text
child retained callback reload    exit=113
DIAG_INTEGRATED_CALLBACK_REVOKED invoked
```

Generation 2 then registered the same stable native H against its new guest target and worked:

```text
child Link after re-register      rv=1001035
child Link after re-register      exit=0
```

The fresh generation-2 callback also worked:

```text
child current callback after new  rv=10010093
child current callback after new  exit=0
```

### Same-address reload / ABA

The guest loader reused the same numeric invoker address:

```text
reload invoker                    old=0x00007ffff7da21b0 new=0x00007ffff7da21b0 SAME
```

The old callback pointer nevertheless remained revoked:

```text
child retained callback reload    exit=113
```

A fresh/current callback worked:

```text
fresh/current callback            rv=10010053 want=10010053
child current callback after new  rv=10010093
child current callback after new  exit=0
```

The integrated callback key-removal rule therefore continues to defeat same-address guest generation reuse when combined with dynamic-PFN retirement.

### Cross-thread hot-cache retirement

A worker thread preheated its private H lookup cache on generation 1:

```text
thread-cache preheat             rv=1023 want=1023
```

Generation 1 was then unloaded and generation 2 moved:

```text
thread-cache old invoker           0x00007ffff7da21b0 -> unmapped
thread-cache reload invoker      old=0x00007ffff7da21b0 new=0x00007ffff7d4c1b0 DIFFERENT
```

The integrated retirement explicitly invalidated H in both live guest threads:

```text
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff4c70c01000
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff4c70c04000
```

The worker then reached generation 2 correctly:

```text
thread-cache post-reload         rv=1001035 want=1001035
```

### Simultaneous same-H owners

Two live same-signature guest DSOs claimed the same native H with different guest invokers:

```text
multi-owner A invoker           0x00007ffff7da21b0
multi-owner B invoker           0x00007ffff7d7c1b0
DIAG_MULTI_ACTIVE H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MULTI_STANDBY H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

A was initially active:

```text
multi-owner active A            rv=1023 want=1023
```

When A retired, the integrated exact-H retirement ran and B was promoted:

```text
DIAG_MULTI_RETIRE H=0x7ffff7d80860 OLD=0x7ffff7da21b0 NEW=0x7ffff7d7c1b0
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff5a20c01000
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MULTI_PROMOTE H=0x7ffff7d80860 T=0x7ffff7d7c1b0
```

A was unmapped while B remained executable, and the unchanged native H reached B:

```text
multi-owner old A after close      0x00007ffff7da21b0 -> unmapped
multi-owner live B                 0x00007ffff7d7c1b0 -> ... r-xp .../liblifetime-guest-b.so
multi-owner promoted B          rv=2001035 want=2001035
```

## Conclusion

The previously isolated lifetime mechanisms are mutually compatible in one real-FEX build across the retained reduced regression suite.

The integrated research candidate simultaneously supports:

```text
moved-generation H rebind
same-address ABA callback safety
cross-thread H cache retirement
same-H compatible alternate-owner promotion
controlled stale callback revocation
```

This materially strengthens the repair direction. The remaining blocker before treating this as the best research baseline is the lock ordering inside exact H retirement.

## Known lock-order defect in this diagnostic

This v1 candidate still routes exact retirement through the diagnostic `RemoveCustomIREntrypoint()` path. Compilation can hold `CodeInvalidationMutex` shared before consulting `CustomIRMutex`, while the existing remover acquires `CustomIRMutex` and then enters code invalidation.

That inversion is not acceptable as a final concurrent implementation even though the controlled regression matrix passes.

The next refinement is therefore mechanical rather than conceptual:

```text
ThreadCreationMutex
  -> CodeInvalidationMutex UNIQUE
    -> CustomIR definition removal/revocation
    -> exact shared H erase/delink
    -> exact H invalidation from every live thread cache
```

The same integrated matrix must pass after that ordering change.

## Evidence boundary

- This run tests current FEX source `71afe...`; exact FEX-2608 has already passed the dynamic-PFN exact-rebind mechanism separately, but the full integrated candidate has not yet been rerun on `e869aa...`.
- Multi-owner promotion is safe in this fixture because both claims deliberately use the same function signature. Generic promotion still needs a signature/ABI identity.
- Cross-thread cache retirement uses a quiescent worker during owner teardown. It does not prove atomic safety for an execution already selected or concurrently reading the retired block.
- Callback revocation uses a diagnostic tombstone in mutable trampoline instance storage; a production implementation should prefer a stable descriptor with an atomic LIVE/REVOKED state.
- The immediate final caller in the original Apple M5 `vulkaninfo` teardown remains uncaptured.

No upstream FEX interaction was performed. All code and CI work remained on owned repositories.