# FEX thunk lifetime: old-H redirect crosses target owner generation — 2026-08-14

Carrier: `teamleaderleo/FEX` branch `ci/thunk-inflight-selected-race-20260814`

Run: `31786964845`

Artifact: `thunk-inflight-selected-31786964845`

Digest: `sha256:a22fffe7e184d9b75009fffa11283abd5798d8e7c7c0ecd0fee50bb1151ccabb`

## Result

```text
selected-race=0
```

The assertion requires a no-reregister worker result of `222`; the workflow completed successfully.

## Exact ordering

Synthetic bridge:

```text
H = 0x700000020000
T generation 1 returns 111
T generation 2 reuses the same VA and returns 222
```

Key receipt lines:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000 thread=...
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0xe new=1
INFLIGHT warm H=0x700000020000 T=0x7ffff7ec4000 value=111
INFLIGHT relink-reset H=0x700000020000 T=0x7ffff7ec4000 sentinel=111 owner-preserved
INFLIGHT armed H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
DIAG_INFLIGHT_SELECTED H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
INFLIGHT old-H-redirect-pending H=0x700000020000 T=0x7ffff7ec4000
DIAG_MAP_FIXED_PREPARE range=0x7ffff7ec4000+0x1000
DIAG_ROLLBACK_PREPARE token=0x1 range=0x7ffff7ec4000+0x1000 hosts=1 callbacks=0
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 owner=0xe range=0x7ffff7ec4000+0x1000
DIAG_MULTI_RETIRE H=0x700000020000 OLD=0x7ffff7ec4000 NEW=0
DIAG_REVOKED_H_INSTALL H=0x700000020000
DIAG_LOCKED_RETIRE H=0x700000020000 thread=...
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
INFLIGHT replacement-committed H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
DIAG_INFLIGHT_RESUME H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
INFLIGHT worker-return value=222
INFLIGHT final worker-value=222 reregister=0
```

## What the barrier proves

The warm call can directly link H's generated `_ExitFunction(T)` transition. Before arming the race, the fixture uses RX -> RW -> RX on T and rewrites the same `111` body. This invalidates the warmed target/link while preserving T's VMA owner ID, a compatibility behavior already proven by the owner-transition tests.

The worker then begins the old compiled H block. H has already committed to its generated numeric T redirect when the diagnostic pauses at `ExitFunctionLink(T)`, before lookup or compilation of T. The controller destructively replaces T, retires H's generation-1 claim, installs the revoked H definition, and commits the new T mapping generation. No H registration follows. Resuming the old redirect resolves the same numeric T against generation 2 and executes `222`.

This separates the bug from the native raw-code lifetime baseline. The stale decision carried across replacement is FEX's generated H -> numeric-T redirect, not an already-selected generation-1 T host block.

## Design consequence

Owner identity currently survives in the retained H claim table, while active/custom-IR H eventually reduces the claim to a naked numeric T. Exact H eviction protects later H lookups but cannot retract an H block that has already begun executing.

A production repair needs owner-generation identity in the H -> T transition itself. Two viable forms are:

1. a stable bridge/claim descriptor referenced by compiled H, carrying `{H, T, OwnerID, state}`;
2. hidden per-thread transition metadata written by H before its exit and validated before T selection.

The descriptor form has a cleaner lifetime story because old compiled H keeps referencing the old claim object. Retirement marks that object revoked; fresh registration creates or activates a current claim object. Same-address reuse therefore cannot make an old H block silently inherit a new owner.

The validation must run on every synthetic H transition. A check that exists only in `ExitFunctionLink` is insufficient once H -> T has been directly linked.

## Next repair experiment

Build a deliberately narrow owner-token bridge candidate:

- compiled H retains the owner ID captured at registration;
- every H -> T transition validates that owner token before selecting/executing T;
- owner mismatch/revocation redirects through H's current definition;
- no-reregister replacement must reach the revoked H path and must never execute `222`;
- explicit generation-2 registration must execute `222`;
- same-owner RX -> RW -> RX must preserve the token and continue to work;
- multi-owner promotion must allow a new H invocation to use the promoted live claim while an old selected claim remains tied to its old owner token.

After that candidate works, insert a second deterministic pause between token validation and target transfer. If retirement can cross that smaller gap, extend the claim token into a narrow transition lease/epoch. Arbitrary guest code keeps the native lifetime behavior already measured separately.
