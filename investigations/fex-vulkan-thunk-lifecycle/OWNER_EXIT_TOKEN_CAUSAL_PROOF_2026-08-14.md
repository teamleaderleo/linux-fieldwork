# FEX synthetic-H VMA-owner exit-token causal proof — 2026-08-14

Internal real-FEX ARM64 Actions experiment. Pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`.

This is the successful narrow follow-up to the iterations recorded in `OWNER_EXIT_TOKEN_ITERATIONS_2026-08-14.md`.

## Carrier

- FEX branch: `ci/thunk-owner-exit-token-repair-20260814`
- carrier head: `c6465d4112e5bdb43183f20465073460daef5f95`
- Actions run: `31793615862`
- job: `94745754309`
- artifact: `thunk-owner-exit-token-31793615862`
- artifact ID: `9216651304`
- artifact digest: `sha256:cae34511185712e0a2a936151eadb342a4b854a75ce4feb21466dc2854db2b3f`

## Mechanism under test

The active synthetic H definition carries the target VMA OwnerID into the ARM64 exit-link record. OwnerID transport is kept outside post-RA IR operands: Context metadata keyed by H is read at H compilation time and copied into the emitted exit-link record.

When the old H exit enters `ExitFunctionLink(T)`, the linker compares:

```text
expected target OwnerID recorded by old H
vs
current VMA OwnerID at numeric T
```

A mismatch redirects resolution through current H state. The old record never consumes the replacement target directly.

This is a deliberately narrow causal experiment for the witnessed `MAP_FIXED` same-address owner-generation transition.

## Matrix

```text
baseline=0
repair-no-reregister=139
repair-reregister=0
```

## Baseline: old H crosses to generation 2

The owner-aware lifetime baseline again reproduces the existing bug:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0xe new=1
INFLIGHT warm H=0x700000020000 T=0x7ffff7ec4000 value=111 reregister=0
...
DIAG_INFLIGHT_SELECTED H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
...
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 owner=0xe ...
DIAG_REVOKED_H_INSTALL H=0x700000020000
DIAG_OWNER_MAP_FIXED addr=0x7ffff7ec4000 old=0xe new=0x11 success=1
...
DIAG_INFLIGHT_RESUME H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
INFLIGHT worker-return value=222
INFLIGHT final worker-value=222 reregister=0
```

Future H lookup is revoked, yet the already-running H redirect consumes generation-2 T.

## Repaired no-registration control

Warm H first accepts its owner token:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0xe new=1
DIAG_OWNER_EXIT_ACCEPT H=0x700000020000 T=0x7ffff7ec4000 owner=0xe
INFLIGHT warm H=0x700000020000 T=0x7ffff7ec4000 value=111 reregister=0
```

After the deterministic pause and `MAP_FIXED` transition:

```text
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 owner=0xe ...
DIAG_REVOKED_H_INSTALL H=0x700000020000
...
INFLIGHT replacement-committed H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222 reregister=0
DIAG_INFLIGHT_RESUME H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
DIAG_OWNER_EXIT_REJECT H=0x700000020000 T=0x7ffff7ec4000 expected=0xe current=0x11
DIAG_REVOKED_H_COMPILE H=0x700000020000
```

The process exits `139` through current revoked H. There is no `worker-return value=222`.

## Repaired explicit re-registration control

Generation-2 registration becomes current H before the old worker resumes:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000 ...
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0x11 new=1
INFLIGHT reregistered H=0x700000020000 T=0x7ffff7ec4000 generation=2
```

The old exit record rejects owner `0xe`, then current H accepts owner `0x11`:

```text
DIAG_INFLIGHT_RESUME H=0x700000020000 T=0x7ffff7ec4000 stage=before-target-selection
DIAG_OWNER_EXIT_REJECT H=0x700000020000 T=0x7ffff7ec4000 expected=0xe current=0x11
DIAG_OWNER_EXIT_ACCEPT H=0x700000020000 T=0x7ffff7ec4000 owner=0x11
INFLIGHT worker-return value=222
INFLIGHT final worker-value=222 reregister=1
```

## Causal conclusion

The old-H `222` crossing is repairable at the synthetic bridge transition itself. A validity token carried by H and checked before selecting T prevents an already-running old H from silently retargeting into a later target lifetime.

The experiment also cleanly preserves legitimate reactivation: old H metadata bounces through current H, and the current definition reaches generation-2 T only after explicit registration.

## Generality boundary

VMA OwnerID is **not** the final universal token. `MREMAP_DONTUNMAP` already proved that executable content can leave a target address while its VMA/resource OwnerID remains unchanged. The general dispatch design therefore remains the per-H/active-claim generation recorded in `H_GENERATION_DISPATCH_DESIGN_2026-08-14.md`.

Treat this OwnerID result as the causal bridge:

```text
old H needs a validity token at dispatch
```

and the DONTUNMAP/remap receipts as the reason that token should represent H/claim state rather than only VMA identity.
