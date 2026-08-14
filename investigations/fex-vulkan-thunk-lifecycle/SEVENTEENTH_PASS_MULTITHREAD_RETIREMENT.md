# Seventeenth pass — multithread exact-retirement runtime proof

## Scope

This checkpoint asks whether exact retirement of a synthetic native entrypoint `H` must invalidate only the thread performing guest unload, or every emulation thread that may have cached `H` in its private L1/L2 lookup state.

The test deliberately keeps the second guest thread quiescent during `dlclose()` and guest-range retirement. It therefore isolates cache coverage from the harder selected-bridge / concurrent-unmap problem.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier branch: `ci/thunk-lifetime-race-20260814`.

Carrier head: `96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2`.

Workflow run: `31768898015`.

Two otherwise-identical variants were executed:

- `local`: remove the CustomIR definition, erase the shared compiled `H` mapping, and clear `H` only from the unloading/calling thread's L1/L2.
- `all`: remove the CustomIR definition, erase the shared compiled `H` mapping/direct links, and clear `H` from every live emulation thread's L1/L2 through the existing ThreadManager-wide invalidation pattern.

## Fixture

The retained full-thunk reproducer was extended with `--thread-cache`.

1. Generation 1 loads and registers stable native host address `H -> T1`.
2. Worker thread B calls `H` successfully once, intentionally heating B's private lookup cache.
3. B becomes quiescent and waits.
4. Main thread A closes generation 1.
5. The outgoing guest span is reserved with `PROT_NONE|MAP_FIXED_NOREPLACE`, forcing the reload to a different guest address.
6. Generation 2 loads and registers the same stable native `H -> T2`.
7. B resumes and calls `H` again.

No worker call is executing while generation 1 is physically unmapped.

## Passing all-thread variant

Job: `multithread-retire (all)`, job id `94670469931`.

Artifact: `9207437594`, `thunk-multithread-retire-all-31768898015`.

Observed fixture trace:

```text
native host A                   0x00007ffff7d80860
native host B                   0x00007ffff7d80860 (SAME)
thread-cache preheat             rv=1023 want=1023
thread-cache old invoker           0x00007ffff7da21b0 -> unmapped
thread-cache reserved old span   0x7ffff7da1000 len=0x5000
thread-cache reload invoker      old=0x00007ffff7da21b0 new=0x00007ffff7d4c1b0 DIFFERENT
thread-cache post-reload         rv=1001035 want=1001035
```

Retirement trace includes two distinct local-cache invalidations before generation 2 is published:

```text
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff93c0c01000
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff93c0c04000
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 thread=0xff93c0c01000
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7d4c1b0
```

`run.exit = 0`.

The worker's post-reload call therefore misses its retired generation-1 private cache state and resolves the generation-2 bridge.

## Failing local-only control

Job: `multithread-retire (local)`, job id `94670470022`.

Artifact: `9207443333`, `thunk-multithread-retire-local-31768898015`.

The diagnostic successfully removes the owner definition and reports that the shared H mapping existed and was erased:

```text
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7da21b0
DIAG_MT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MT_RETIRE_LOCAL H=0x7ffff7d80860 thread=0xff7fc0c01000 shared=1
DIAG_MT_OWNER H=0x7ffff7d80860 T=0x7ffff7d4c1b0
timeout: the monitored command dumped core
```

`run.exit = 139`.

The worker never prints the expected generation-2 result. The intended difference from the passing job is that worker B's private L1/L2 entry for H is not invalidated.

## Conclusion

All-thread exact invalidation is runtime-required for this lifetime class.

The required retirement set is now directly demonstrated as:

```text
CustomIR definition for H
+ shared compiled H mapping/direct links
+ H in every live emulation thread's L1/L2
```

Removing the handler and shared mapping while invalidating only the unloading thread is insufficient even when every other guest thread is quiescent during physical unmap.

This complements the earlier controls:

- handler removal/re-add alone fails;
- exact shared-map erase without the hot local cache fails;
- exact single-thread retirement works in a single-thread fixture;
- exact all-thread retirement works in this cross-thread fixture.

## Product transaction

The final implementation should batch retiring synthetic H keys under the existing global thread/code-invalidation discipline rather than calling the current `RemoveCustomIREntrypoint()` sequence unchanged.

The intended lock/order direction is:

```text
ThreadCreationMutex
  -> CodeInvalidationMutex UNIQUE
    -> CustomIRMutex
      -> revoke/remove outgoing synthetic H definitions
      -> exact shared GuestToHostMap::Erase(H), including inbound-link delinking
      -> exact H invalidation from every live thread's L1/L2
  -> permit physical guest unmap
```

Compilation already holds `CodeInvalidationMutex` shared before consulting `CustomIRMutex`. The current remover takes `CustomIRMutex` first and then routes into code invalidation, so simply nesting the current remover inside a new all-thread transaction would create an undesirable lock-order inversion. The production primitive should implement one coherent transaction with a single lock order.

## Evidence boundary

This test intentionally keeps worker B quiescent while retirement and unmap occur. It proves thread coverage, not atomic safety of invalidating an L1 entry while that other thread is concurrently reading it.

Current `LookupCache` source explicitly describes cross-thread L1 invalidation as a soft guarantee without atomics and notes that it has not been thoroughly vetted. A final concurrency design should therefore distinguish:

1. removing every thread's future ability to select the retired block; and
2. handling an execution that already selected or is concurrently reading the old block.

The second problem remains the selected-bridge / unload quiescence question.

No third-party upstream interaction was performed. All code and CI work stayed in owned repositories.