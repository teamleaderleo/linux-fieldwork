# FEX thunk lifetime: old-H redirect versus target-generation reuse — 2026-08-14

## Question

After an H -> T dynamic thunk bridge has already begun executing from a compiled H block, can destructive replacement retire H's generation-1 claim yet allow that old H block to resolve the same numeric T after T belongs to generation 2?

This is distinct from the already-measured raw selected-code lifetime case. Native Linux also faults when one thread has already selected/entered DSO code and another thread unmaps that DSO. The experiment here stops before T selection so the only stale decision carried across the boundary is FEX's generated H redirect to the numeric T address.

Synthetic constants:

```text
H = 0x700000020000
T generation 1 returns 111
T generation 2 at the same VA returns 222
```

No explicit H re-registration occurs after replacement.

## Carrier

`teamleaderleo/FEX` branch `ci/thunk-inflight-selected-race-20260814`

The owner-aware candidate includes:

- pre-destructive MAP_FIXED retirement;
- transactional rollback on failed replacement;
- VMA owner IDs preserved by permission-only mprotect and renewed by destructive reuse;
- retained H claims keyed by `{Target, OwnerID}`;
- ACTIVE / REVOKED synthetic-H definitions;
- multi-owner claim promotion.

## Placement attempts retained

### Run 31785024613 — probe compile failure

Base FEX built. The x86-64 probe failed under `-Werror` before candidate application or execution because the included FEX guest helper emitted a missing-field warning and the fixture ignored a `write()` result. Both errors were retained as harness evidence and repaired.

### Run 31785476861 — dispatcher-L2 placement miss

Candidate compiled and ran. Matrix:

```text
selected-race=124
```

Observed:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=... owner=0xe new=1
INFLIGHT warm H=0x700000020000 T=... value=111
INFLIGHT worker-return value=111
```

No selection marker appeared. The worker completed before the controller observed the barrier, so this said nothing about the target-generation race. The pause had been installed only on the main dispatcher L2-hit path.

### Run 31786010825 — ExitFunctionLink(H) placement miss

Base, probe, candidate build, and race step all completed. The expected-result assertion failed. Artifact: `thunk-inflight-selected-31786010825`.

Matrix:

```text
selected-race=124
```

Key lines again show warm=111 and worker=111 with no `DIAG_INFLIGHT_SELECTED` marker.

Reason: the translated bridge H is itself custom IR. H's body performs `_ExitFunction(T)`. The exit linker therefore sees T when H redirects; it does not receive H as the `GuestRip` at the desired point.

## Current deterministic boundary

The fixture now publishes T to host `/tmp/fex-thunk-inflight-target` after the warm call and only then arms the diagnostic.

The JIT diagnostic hooks `Arm64JITCore::ExitFunctionLink` at function entry:

1. H generation-1 compiled block begins executing;
2. H performs its generated `_ExitFunction(T)` redirect;
3. `ExitFunctionLink` receives `GuestRip == T`;
4. before lookup/compilation of T, the hook recognizes the published target and writes the selected marker;
5. worker waits;
6. controller performs destructive MAP_FIXED over T;
7. owner-aware retirement removes H's generation-1 claim and revokes future H lookup;
8. T is rewritten as generation 2 returning 222;
9. worker resumes inside the old H redirect before T selection;
10. no H re-registration occurs.

Discriminator:

```text
worker = 222
```

means an old compiled H redirect can cross into a different target mapping generation even after H's retained claim was retired. Exact H eviction then protects future H callers while leaving a stale in-flight FEX-created redirect alive.

A fault/revocation before 222 means another existing invalidation boundary already blocks this crossing.

Current runs from the corrected carrier:

- `31786652570` from fixture/script update;
- `31786680880` with assertions updated for `stage=before-target-selection`.

## Repair direction if 222 reproduces

A global guest-code lifetime rendezvous is unnecessary for native equivalence; native selected/entered DSO code has already been shown to fault after concurrent unload on both x86-64 and ARM64.

The candidate repair should stay local to FEX-created dynamic bridges:

- retain owner identity beyond registration and compilation;
- carry a stable H-claim token into the H -> T transition;
- validate that token after H has begun executing and before T selection;
- reject a token whose owner entered retirement;
- allow fresh explicit registration to install a new token for generation 2;
- preserve multi-owner promotion by selecting the token associated with the active claim.

A diagnostic implementation may use the existing H marker as a shortcut, but a production implementation should use hidden per-thread/bridge metadata instead of guest-visible architectural state.

After a first validation repair succeeds, add a second pause between validation and T transfer. If retirement can still occur in that gap and cross generations, the transition needs a narrow lease/epoch spanning validation through target selection. That lease applies only to FEX-created H claims, not arbitrary guest code pointers.
