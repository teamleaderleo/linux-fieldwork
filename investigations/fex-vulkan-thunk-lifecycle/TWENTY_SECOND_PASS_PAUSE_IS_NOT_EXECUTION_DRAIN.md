# Twenty-second pass — thread pause is not execution draining

## Scope

This checkpoint reviews whether FEX's existing thread pause/idle machinery can serve as the execution-drain mechanism required by the forced in-flight thunk-selection failure.

Reviewed product revision: `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`.

Conclusion: the existing pause API is **not** a valid substitute for a bridge execution lease or revocable final-transfer state.

## Existing external-control pause API

`ThreadManager::Pause()` begins with an assertion that it is not called from an emulation thread. It then sends `SignalEvent::Pause` to each emulation thread and waits for the global idle reference count to reach zero.

Guest `munmap` / thunk-owner retirement runs on an emulation thread. Calling the existing global `Pause()` from that path therefore violates the API's own execution-context invariant and would also include the calling thread in the requested pause set.

`WaitForIdle()` has the same all-threads interpretation: completion means `IdleWaitRefCount == 0`. From inside a live guest syscall, the current emulation thread necessarily remains active unless teardown attempts to suspend itself.

So the existing `Pause()` + `WaitForIdle()` combination is external-control machinery, not an in-guest teardown primitive.

## Lower-level pause semantics preserve the interrupted execution

`SignalDelegator::HandleSignalPause()` handles `SignalEvent::Pause` by:

1. saving the interrupted thread state;
2. redirecting the host PC to FEX's thread-pause handler;
3. retaining enough state to restore the interrupted execution later.

The corresponding pause-return path restores the saved thread state.

This is exactly the wrong semantic operation for the failure proven in `TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md`.

That experiment proves a worker can already have selected old-generation host code for guest target `T1` after leaving the lookup/invalidation critical section. Suspending that worker does not make the selection cease to exist; it freezes the interrupted host context and later restores it.

If teardown unmaps T1 while such a paused context still owns the selected transfer, resuming the thread can continue from the stale selection. Suspension therefore does not establish:

> no execution capable of reaching generation T1 remains in flight before T1 is unmapped.

## Why `PauseOthers(current)` would still be insufficient

A new diagnostic could mechanically signal every other emulation thread and wait for `IdleWaitRefCount == 1`, leaving only the calling teardown thread active. That might be useful for unrelated stop-the-world operations.

It would **not** solve the forced selected-before-unmap race by itself.

For the critical sequence:

```text
worker selects T1 -> HostCode1
worker leaves lookup/invalidation guard
worker is paused
teardown retires future H lookups
teardown unmaps T1
worker is resumed
```

the pause operation preserves rather than drains the already-selected host context. Exact-H cache retirement still cannot revoke it.

Therefore a successful `PauseOthers` experiment before *any* thread selects the bridge would only prove a stop-before-acquisition policy. It would not satisfy the harder race where acquisition has already happened.

## What execution draining must guarantee instead

The runtime evidence now requires one of these stronger semantics:

1. **Lease/reference draining** — selecting or entering a generation-dependent bridge acquires a lease; owner retirement blocks new leases and waits until every existing lease is released before physical unmap.
2. **Stable revocable final-transfer state** — already-selected process-lived code must revalidate an owner generation at a point after ordinary lookup selection and immediately before entering unloadable guest-generation code.
3. **Process-lifetime invoker code** — eliminate the unloadable guest-code dependency from the dynamic bridge itself.

A broad stop-the-world mechanism could only be sufficient if it also rewrites/restarts every suspended context that may already contain a selected generation-dependent destination. FEX's existing pause API does not provide that property.

## Relationship to lock-order work

`TWENTY_FIRST_PASS_LOCK_ORDER_RUNTIME.md` shows that exact-H retirement can use a coherent order across thread-list, code-invalidation, CustomIR-definition, shared-cache, and per-thread-cache state.

This note keeps that solved problem separate from execution draining:

```text
safe lock order       -> prevents retirement deadlock/inversion
all-thread cache erase -> prevents future stale lookup
execution lease/revoke -> prevents already-selected stale transfer
thread pause           -> preserves interrupted execution; not equivalent to drain
```

## Evidence boundary

Source-proven on `f3ab82...`:

- `ThreadManager::Pause()` is forbidden from an emulation thread;
- global idle wait expects all emulation threads to sleep;
- pause handling saves the interrupted host/guest state and later restores it.

Runtime-proven in the adjacent twentieth pass:

- a selected T1 transfer can outlive exact-H shared/per-thread retirement and owner unmap;
- resuming that selected transfer after T1 unmap faults.

Not demonstrated here:

- a production execution-lease implementation;
- whether a new targeted context-rewrite/quiescence facility could be designed safely;
- the original Apple M5 terminal H/R11 identity.

No upstream interaction was performed. This review and all related experiments remain in owned repositories/forks.
