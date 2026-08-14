# Multithread cache and execution-quiescence results

## Why this note exists

The generic thunk-lifetime experiments now separate two failure modes that can look identical at the final SIGSEGV:

1. another FEX thread still has translated execution state for an old `H -> T1` bridge;
2. another FEX thread already selected `T1` before retirement began.

Those are different synchronization problems. The first is solved by invalidating every relevant translated cache. The second is not.

## A/B 1 — local-thread invalidation versus all-thread invalidation

Owned FEX carrier branch:

`ci/thunk-lifetime-race-20260814`

Carrier commit:

`96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2`

Exact FEX source under test:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Workflow:

`.github/workflows/thunk-multithread-retire-arm64.yml`

Actions run:

`31768898015`

The fixture preheats the dynamic native-H thunk route on a worker thread, then the owner guest DSO is closed and forced to reload at a different guest address. The native host address remains stable while the guest invoker changes.

Representative addresses:

```text
H  = 0x00007ffff7d80860
T1 = 0x00007ffff7da21b0
T2 = 0x00007ffff7d4c1b0
```

### Mode `local`

The retirement diagnostic removes shared bridge metadata but invalidates only the unloading/current thread's execution state.

Observed key lines:

```text
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MT_RETIRE_LOCAL H=0x7ffff7d80860 thread=<unloading-thread> shared=1
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7d4c1b0
```

The process then exits `139`.

The important point is that the worker had already compiled/cached the old H-keyed redirect. Removing the global registration and invalidating only the current thread does not remove another thread's executable copy of that decision.

### Mode `all`

The stronger retirement mode removes the shared H bridge and invalidates translated state for every known FEX thread.

Observed key lines:

```text
native host A                   0x00007ffff7d80860
native host B                   0x00007ffff7d80860 (SAME)
thread-cache preheat             rv=1023 want=1023
thread-cache old invoker         0x00007ffff7da21b0 -> unmapped
thread-cache reload invoker      old=0x00007ffff7da21b0 new=0x00007ffff7d4c1b0 DIFFERENT

DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=<thread-1>
DIAG_MT_THREAD H=0x7ffff7d80860 thread=<thread-2>
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 ...

thread-cache post-reload         rv=1001035 want=1001035
```

The process exits `0`.

### Result

```text
local-thread invalidation -> 139
all-thread invalidation   ->   0
```

**Conclusion:** translated dynamic-thunk routes are effectively a cross-thread lifetime domain. A retirement operation that invalidates only the thread performing `dlclose()` is insufficient.

## A/B 2 — all-thread invalidation versus an already-selected target

A separate deterministic in-flight fixture moves the barrier later.

Instead of merely preheating a worker's translated cache, the worker is stopped **after it has selected old target `T1`** and before it resumes execution there.

Owned diagnostic branch:

`ci/thunk-inflight-selection-race-20260814`

Actions run:

`31770286056`

The retiring thread performs the stronger sequence:

```text
DIAG_INFLIGHT_SELECTED guest=T1
DIAG_MT_MATCH H=<H> T=<T1> range=<old-owner>
DIAG_MT_SHARED H=<H> erased=1
DIAG_MT_THREAD H=<H> thread=<thread-1>
DIAG_MT_THREAD H=<H> thread=<thread-2>
DIAG_MT_REMOVE_ALL H=<H> handler=1
DIAG_MT_RETIRE_ALL H=<H> ...
```

### Pin control

The old bridge owner remains mapped while the already-selected worker resumes:

```text
DIAG_INFLIGHT_RESUME guest=T1
inflight worker returned rv=1023 want-old=1023
```

Exit: `0`.

### Physical-unmap case

The old owner is physically unmapped after all-thread retirement/invalidation but before the selected worker resumes:

```text
inflight old invoker after dlclose T1 -> unmapped
inflight owner unmapped before resume
DIAG_INFLIGHT_RESUME guest=T1
```

Exit: `139`.

### Result

```text
pin old owner after selection  ->   0
unmap old owner after selection -> 139
```

**Conclusion:** all-thread invalidation removes stale future selection paths, but it cannot revoke a transfer already selected by a running thread. Invalidation is prospective; physical unmap needs an execution grace period / lease / quiescence protocol.

## Combined model

These two A/Bs produce a useful staged model:

```text
Stage 1: old H -> T1 registration exists
Stage 2: a thread compiles/caches H -> T1
Stage 3: a thread selects/commits to T1
Stage 4: thread executes inside/through T1
```

Retirement capabilities observed so far:

```text
remove registry only
    prevents some future metadata lookups
    DOES NOT remove already-compiled H -> T1 execution

remove registry + invalidate unloading thread
    still leaves another thread's translated H -> T1 state

remove registry + invalidate all threads
    fixes the cross-thread cached-route case
    DOES NOT retract a target selected before retirement

keep owner mapped until selected execution finishes
    avoids the post-selection fault
```

That gives a cleaner conceptual split:

### Cache coherence

Every thread/shared cache that can execute a derived bridge route must participate in retirement.

### Execution quiescence

After new acquisition is blocked and caches are invalidated, retirement still needs to know when no thread can be carrying an old-generation execution commitment.

These are separate requirements and should be tested separately in any future design.

## Implication for a true-unload protocol

A minimally credible physical-reclamation sequence is now:

```text
mark owner generation draining
    -> stop new H/callback acquisitions
    -> retire/tombstone escaped callback bridges
    -> remove H-key bridge metadata
    -> invalidate shared translated H route
    -> invalidate every thread's translated H route
    -> wait for already-selected / already-entered old-generation executions
    -> physically unmap guest owner
    -> permit later generation registration
```

The last wait is not optional if physical unmap is allowed while other guest threads execute.

## Why NODELETE and split residency remain attractive

A process-resident guest thunk policy avoids this entire physical-owner transition: old translated routes and in-flight executions continue to point at executable bridge code.

A split resident bridge-runtime design attempts to retain that property only for escaped/generated bridge code while allowing library-specific wrapper state to unload and reset.

The multithread results therefore strengthen the architectural case for stable bridge ownership. They also raise the implementation cost bar for any design that promises true physical reclamation.

## Next discriminator

The strongest remaining race test is to move the barrier one stage later again:

> block the worker while it is actually executing inside old guest bridge code, then initiate owner retirement/unmap from another thread.

If physical unmap can complete while that worker's PC/execution lease is inside the retiring generation, resumption should fail unless the unload path waits for that execution to leave. This would directly test whether the required lease covers the full bridge execution interval rather than only target selection.

A second useful check is to reproduce the post-selection race on exact FEX-2608 (`e869aa644a16e4332cdc15c1ea0b4d13d482385d`) so the concurrency result sits on the same source revision as the original Vulkan failure.