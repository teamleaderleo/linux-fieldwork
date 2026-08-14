# Pre-`MAP_FIXED` thunk-retirement experiment log

Date: 2026-08-14

## Starting evidence

Real-FEX VMA run `31778138756` demonstrated a same-address mapping-generation ABA:

```text
H = 0x700000020000
T = 0x7ffff7ec4000
first H() -> 111
MAP_FIXED replaces the page at T with a new mapping generation
new code at the same T returns 222
no new LinkAddress registration occurs
H() -> 222
```

Both stock FEX and the current integrated lifetime candidate show that behavior. See [`VMA_TRANSITION_LOG.md`](./VMA_TRANSITION_LOG.md).

## Hypothesis under test

The missing correctness hook is the mapping-generation destruction boundary. For `MAP_FIXED`, dependent thunk claims must stop being active before the host kernel replaces the old mapping.

A narrow causal candidate therefore calls the existing `ThunkHandler::RetireGuestRange()` for the destination range immediately before host `mmap(... MAP_FIXED ...)`.

This experiment deliberately reuses the current range-based claim index. It is **not** the proposed production ownership design. Its job is to test whether pre-destructive retirement at this exact syscall boundary closes the silent ABA.

## Temporary candidate limitation

The diagnostic retires claims before the host `mmap` call and does not restore them if the `MAP_FIXED` syscall fails. The controlled probe supplies a valid aligned replacement and does not exercise failure rollback.

A production mapping-owner transaction needs prepare/commit/rollback semantics and a non-reusable VMA/`MappedResource` owner token.

## Owned FEX branch

```text
ci/map-fixed-pre-retire-20260814
```

Relevant commits:

```text
6dd22be1b75d746808a47a3d76f8e082252ecda4  add pre-MAP_FIXED retirement helper
4bd727075a60a1bf35a730498267db2ba1b1791e  add explicit re-registration control
5ff913bc7f9e82dc46adcf5566480398094f8429  run stock/current/pre-retire A-B-C matrix
```

Actions run launched:

```text
31780286007
```

## Matrix and expected discriminator

Three runtime phases use the same x86 guest probe:

```text
stock
current integrated lifetime candidate
current candidate + pre-MAP_FIXED retirement hook
```

Each phase runs:

```text
map-fixed
map-fixed-reregister
```

Expected current behavior:

```text
stock map-fixed                    -> 222
current candidate map-fixed        -> 222
```

Expected causal-fix signature:

```text
pre-retire map-fixed               -> old H is revoked; must never return 222
pre-retire map-fixed-reregister    -> explicit new LinkAddress claim reactivates H; returns 222
```

The exact signal/exit code of the revoked call is secondary. The critical property is that same-address replacement alone cannot attach old H to generation-2 code, while an explicit fresh claim can.

## Production follow-on if green

Replace the range scan with mapping-generation ownership:

- non-reusable owner ID associated with VMA/`MappedResource` generation;
- reverse dependency index owner -> thunk claims/callback bridges;
- prepare retirement before destructive mapping operation;
- commit owner transition only after syscall success;
- rollback or preserve old claims if the syscall fails;
- explicit LinkAddress registration reactivates a revoked H for the new owner generation.

## External-contact state

No third-party/upstream interaction. All code, workflows, and notes are in repositories owned by `teamleaderleo`.
