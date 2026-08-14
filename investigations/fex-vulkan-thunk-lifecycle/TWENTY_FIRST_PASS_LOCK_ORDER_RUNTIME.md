# Twenty-first pass — lock-order-safe integrated lifetime matrix

## Scope

This checkpoint reviews and retains a concurrent owned-fork experiment that addresses the lock-order hazard left open by the nineteenth-pass integrated lifetime candidate.

The nineteenth-pass candidate already combined:

- exact synthetic-H retirement;
- shared and all-live-thread lookup/cache invalidation;
- compatible same-H multi-owner promotion;
- callback tombstoning/revocation;
- callback cache-key removal;
- same-address ABA handling.

Its remaining structural concern was that retirement could nest `CustomIRMutex` and code-invalidation locking in an order opposite to compilation/invalidation paths.

This pass tests a revised diagnostic that imposes one retirement order and reruns the full reduced runtime matrix.

Owned-FEX branch: `ci/thunk-lifetime-integration-20260814`.
Successful carrier commit: `0436d8420084024043a60c86eef8316c94a0bce2`.
Lock-order implementation parent: `065f22c80de28dd2d3624031b42391c81ccd54a2`.
Workflow run: `31770676007`.
Job: `94675781219`.
Artifact: `9208068787`, `thunk-lifetime-integration-31770676007`.
Artifact digest: `sha256:7c94e0b2b23d9898f73b08fbc4f968a305ce69ed14b7018688ba71fb2234a104`.

This is owned-fork diagnostic engineering, not upstream contribution code.

## Revised retirement order

The diagnostic separates CustomIR definition removal from generic code invalidation and performs retirement under one explicit order:

```text
freeze thread creation / thread-list mutation
  -> acquire code-invalidation exclusion
    -> remove matching thunk CustomIR definition
       (CustomIR definition mutex is acquired inside this phase)
    -> erase/delink shared synthetic H code
    -> invalidate H from every live thread lookup cache
  -> release code-invalidation exclusion
-> release thread-list freeze
```

It also changes the generic single-entry CustomIR removal path so the CustomIR definition lock is released before the generic invalidation operation, avoiding the opposite `CustomIR -> code invalidation` nesting in that path.

The intended ordering is therefore consistent with the compilation/invalidation side rather than allowing both mutex orders to exist.

## Runtime matrix

The successful ARM64 run reports:

```text
force=0
aba=0
thread=0
multi=0
```

### Forced-different reload

The generation-1 owner is retired under the new locked sequence:

```text
DIAG_LOCKED_RETIRE H=<synthetic H> ...
```

The old Link/CallHost path is no longer usable, stale callback state is tombstoned, and the fresh generation remains callable.

### Same-address ABA

The same virtual-address reuse case also exits 0. The retired generation is not resurrected merely because a later guest image occupies the same address range.

### Cross-thread cache case

The worker preheats synthetic H, then quiesces. Retirement removes the H definition/shared entry and invalidates every live thread's lookup state under the revised order. The case exits 0.

### Same-H multi-owner promotion

Two compatible live owners claim one synthetic H. When the active owner unloads, the surviving compatible owner is promoted rather than losing the bridge. The case exits 0 under the revised lock order as well.

The callback-side diagnostics also continue to show the intended tombstone/revocation behavior.

## Conclusion

The lock-order repair is compatible with the ownership mechanisms already proven in the integrated reduced matrix.

This removes the specific concern that fixing the lifetime model necessarily introduces a `CustomIRMutex` / code-invalidation lock inversion. A coherent retirement order can coexist with:

- exact-H invalidation;
- all-thread cache coverage;
- ABA protection;
- same-H compatible-owner promotion;
- callback revocation.

The result does **not** make the integrated lifetime candidate complete.

## Separation from the in-flight execution gap

`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md` now proves on both `71afe476...` and `f3ab82...` that an emulation thread can select old-generation host code, release the lookup/invalidation guard, and then execute that selected transfer after exact-H retirement and owner unmap.

The lock-order matrix here uses a quiescent worker for its cross-thread case. Therefore:

```text
coherent retirement lock order != execution drain
```

Both are required.

The strongest next lifetime design should keep the successful lock order from this pass **and** add one of:

1. an execution lease acquired before a generation-dependent transfer becomes in-flight and drained before owner unmap;
2. stable process-lived revocable bridge state consulted after selection and immediately before entering unloadable guest-generation code;
3. process-lifetime guest invoker code that removes the unloadable target dependency from this bridge class.

A new candidate should be judged against the forced post-selection race, not only the quiescent force/ABA/thread/multi matrix.

## Evidence boundary

Demonstrated here:

- the revised diagnostic builds and executes on hosted ARM64;
- force/ABA/thread/multi all exit 0;
- exact retirement occurs under the new ordered diagnostic path;
- callback revocation and multi-owner promotion continue to function in the reduced matrix.

Not demonstrated here:

- safe execution draining for already-selected transfers;
- a production-ready locking API or upstream implementation;
- the original Apple M5 `vulkaninfo` teardown repaired by this lock-order change alone.

No upstream interaction was performed. The experiment and retention stayed in owned repositories/forks.
