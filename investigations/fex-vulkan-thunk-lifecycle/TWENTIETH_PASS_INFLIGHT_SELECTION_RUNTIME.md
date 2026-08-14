# Twentieth pass — in-flight selected bridge survives cache retirement

## Scope

This checkpoint tests the concurrency gap intentionally left open by the earlier all-thread cache-retirement result.

The earlier result proved that retiring synthetic entry `H` from the shared compiled map and every live emulation thread's lookup cache is necessary. Its worker was quiescent during teardown. This pass instead forces a worker to have already selected the old guest target generation before unload begins.

Base FEX product source: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX carrier branch: `ci/thunk-inflight-selection-race-20260814`.
Carrier commit used by the successful run: `215d2c69aba63d7b3db3369c899e2bb5b4793d05`.
Workflow run: `31770286056`.
Job: `94674595643`.
Artifact: `9207922413`, `thunk-inflight-selection-race-31770286056`.
Runner: GitHub hosted `ubuntu-24.04-arm`.

The workflow checks out exact `71afe476...` product source in a separate tree, then applies two research diagnostics:

1. the already-proven all-thread exact-H retirement diagnostic;
2. an env-gated barrier in ARM64 `ExitFunctionLink` that pauses only after the old guest RIP has resolved to a host-code pointer and after the lookup/code-invalidation guard used for that selection has been released.

This is research instrumentation, not upstream contribution code.

## Why the barrier location matters

The barrier is deliberately outside the lookup/invalidation critical section. If it held the shared invalidation guard while paused, unload would be artificially serialized and the test could not distinguish cache retirement from execution draining.

The fixture writes the exact generation-1 guest invoker address `T1` into the barrier target file. Only `ExitFunctionLink` selection for that exact guest RIP can pause the worker.

The forced sequence is therefore:

```text
worker selects old guest RIP T1 -> HostCode1
worker releases lookup / invalidation guard
worker pauses
main retires H from shared + every thread cache
main final-dlcloses generation 1
main confirms T1 is unmapped
main resumes worker
worker attempts to continue with already-selected HostCode1
```

## Pin control

With the generation-1 DSO pinned, the same post-selection barrier executes and resumes normally:

```text
inflight target                  T1=0x00007ffff7da21b0 H=0x00007ffff7d80860 pin=1
inflight selected                T1=0x00007ffff7da21b0
DIAG_INFLIGHT_SELECTED guest=0x7ffff7da21b0 host=0x80006acc46b4
inflight pin keeps owner mapped before resume
DIAG_INFLIGHT_RESUME guest=0x7ffff7da21b0 host=0x80006acc46b4
inflight worker returned         rv=1023 want-old=1023 owner-was-mapped
```

Exit:

```text
pin=0
```

This proves that the diagnostic barrier itself does not invalidate the selected transfer.

## Forced unload race

The unmap case reaches the same selection boundary:

```text
inflight target                  T1=0x00007ffff7da21b0 H=0x00007ffff7d80860 pin=0
inflight selected                T1=0x00007ffff7da21b0
DIAG_INFLIGHT_SELECTED guest=0x7ffff7da21b0 host=0x80006b6446b4
```

While the worker is paused, the all-thread retirement diagnostic runs:

```text
DIAG_MT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff2300c01000
DIAG_MT_THREAD H=0x7ffff7d80860 thread=0xff2300c04000
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 thread=0xff2300c01000
```

The fixture then confirms the old owner is gone before the worker is resumed:

```text
inflight old invoker after dlclose 0x00007ffff7da21b0 -> unmapped
inflight owner unmapped before resume
```

Only then does the worker continue:

```text
DIAG_INFLIGHT_RESUME guest=0x7ffff7da21b0 host=0x80006b6446b4
```

The process immediately terminates with SIGSEGV:

```text
unmap=139
```

There is no successful worker return after resume.

## Conclusion

All-thread lookup/cache retirement is necessary but **not sufficient** for safe thunk-owner unload.

A thread that has already selected host code for old guest target generation `T1` can remain capable of transferring into that generation after:

- the CustomIR registration has been retired;
- the shared compiled synthetic `H` entry has been erased/delinked;
- every live emulation thread's H lookup cache has been invalidated; and
- the guest mapping containing T1 has been physically unmapped.

The remaining lifetime invariant therefore needs an execution-drain or revocable-selection mechanism. Merely deleting future lookup paths cannot revoke a host-code pointer already selected outside the invalidation critical section.

This experimentally validates the execution-lease requirement that previously appeared only in the synthetic design comparison.

## Design implications

The viable families remain:

1. **Execution lease / quiescence:** selecting a bridge acquires ownership that unload must drain before unmapping its guest target generation.
2. **Stable revocable bridge state:** an already-selected process-lived bridge consults a stable LIVE/REVOKED generation record at the final transition point, after lookup selection and before entering guest-generation code.
3. **Process-lifetime guest invoker implementation:** remove unloadable guest DSO addresses from this bridge class entirely.
4. **Pinning:** valid containment/control but does not resolve ownership semantics.

Exact cache eviction should remain part of any design, because it closes future lookups. This result shows it must be paired with a rule for already-acquired execution.

## Relationship to the integrated lifetime candidate

`NINETEENTH_PASS_INTEGRATED_LIFETIME_RUNTIME.md` demonstrates that exact-H retirement, all-thread cache invalidation, compatible same-H promotion, callback revocation, and same-address ABA handling coexist successfully in one reduced matrix. That matrix explicitly used a quiescent worker for the cross-thread case.

This pass supplies the missing negative control: the same all-thread retirement rule still loses when a worker has selected the outgoing generation before teardown.

A next integrated candidate should therefore preserve the successful mechanisms from the nineteenth pass while adding either execution draining or a stable revocable final-transfer state. Its lock-order fix and its execution-lifetime fix should be evaluated together rather than assuming one solves the other.

## Current-upstream confirmation

During this pass upstream FEX `main` advanced to `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`, whose first parent is `71afe476...`. The merge changes shared JIT/code-buffer allocation, so the forced race was rerun rather than inferred from source similarity.

Owned-FEX carrier branch: `ci/thunk-inflight-selection-race-f3ab-20260814`.
Carrier commit: `68ddf200b03a89e8b55c04ebb36a31c23d07bb96`.
Workflow run: `31770635557`.
Job: `94675657722`.
Artifact: `9208053017`, `thunk-inflight-selection-race-current-main-31770635557`.
Exact product checkout: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

The current-main pin control again selected old `T1`, resumed it while its owner remained mapped, and returned the expected old-generation value:

```text
inflight target                  T1=0x00007ffff7da21b0 H=0x00007ffff7d80860 pin=1
DIAG_INFLIGHT_SELECTED guest=0x7ffff7da21b0 host=0x80006bc046b4
inflight pin keeps owner mapped before resume
DIAG_INFLIGHT_RESUME guest=0x7ffff7da21b0 host=0x80006bc046b4
inflight worker returned         rv=1023 want-old=1023 owner-was-mapped
pin=0
```

The forced-unload case again retired the exact `H` registration and shared/per-thread cache entries while the worker was paused, proved the old `T1` mapping was gone, and only then resumed the already-selected transfer:

```text
DIAG_INFLIGHT_SELECTED guest=0x7ffff7da21b0 host=0x80006c1c46b4
DIAG_MT_MATCH H=0x7ffff7d80860 T=0x7ffff7da21b0 range=0x7ffff7da1000+0x5000
DIAG_MT_SHARED H=0x7ffff7d80860 erased=1
DIAG_MT_THREAD H=0x7ffff7d80860 thread=<thread-1>
DIAG_MT_THREAD H=0x7ffff7d80860 thread=<thread-2>
DIAG_MT_REMOVE_ALL H=0x7ffff7d80860 handler=1
DIAG_MT_RETIRE_ALL H=0x7ffff7d80860 thread=<calling-thread>
inflight old invoker after dlclose 0x00007ffff7da21b0 -> unmapped
inflight owner unmapped before resume
DIAG_INFLIGHT_RESUME guest=0x7ffff7da21b0 host=0x80006c1c46b4
unmap=139
```

Therefore the new shared-code-buffer allocation merge does **not** close this execution-lifetime gap. The same invariant is runtime-proven on both the reviewed parent snapshot and the upstream-current snapshot observed during this pass:

> future lookup retirement cannot revoke a transfer whose host-code selection already escaped the lookup/invalidation critical section.

## Evidence boundary

Demonstrated here:

- exact `71afe...` and exact `f3ab82...` product source in separate runs;
- worker paused after old T1 resolved to host code;
- barrier outside the relevant lookup/invalidation guard;
- exact H retired from shared and all observed live thread caches before resume;
- T1 confirmed unmapped before resume;
- pin controls return correctly;
- unmap cases resume then SIGSEGV.

Not demonstrated here:

- which production-grade lease/revocation mechanism is best;
- the terminal H/R11 identity in the original Apple M5 `vulkaninfo` teardown.

No upstream interaction was performed. All mutation and CI execution stayed in owned repositories/forks.
