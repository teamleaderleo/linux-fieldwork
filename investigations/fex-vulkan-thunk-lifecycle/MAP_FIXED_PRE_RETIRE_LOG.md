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

## Run 1 — A-B-C causal discriminator succeeds

Actions run:

```text
31780286007
job:    94704363107
carrier: 5ff913bc7f9e82dc46adcf5566480398094f8429
product base: 71afe476751deac24adabd1adb575fd2337b6e0a
lifetime helper: 96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
job conclusion: success
```

Artifact:

```text
id:      9211564733
name:    map-fixed-pre-retire-31780286007
sha256:  62214afb44ef15ae1ad13cbecff2f2fcf545684398b2d7abf0214b6df6bfe5e5
```

### Matrix

```text
stock-map-fixed=0
stock-map-fixed-reregister=0
current-map-fixed=0
current-map-fixed-reregister=0
pre-retire-map-fixed=139
pre-retire-map-fixed-reregister=0
```

The stock/current zero exits both mean the no-reregister path reached generation-2 code and returned sentinel 222.

Stock:

```text
VMA first H=0x700000020000 T=0x7ffff7ec4000 value=111
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
VMA after-map-fixed value=222 reregister=0
```

Current integrated lifetime candidate:

```text
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000
DIAG_MULTI_ACTIVE H=0x700000020000 T=0x7ffff7ec4000
VMA first H=0x700000020000 T=0x7ffff7ec4000 value=111
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
VMA after-map-fixed value=222 reregister=0
```

### Pre-destructive retirement closes the silent ABA

For the causal candidate, immediately before the controlled one-page replacement:

```text
DIAG_MAP_FIXED_PREPARE range=0x7ffff7ec4000+0x1000
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 range=0x7ffff7ec4000+0x1000
DIAG_MULTI_RETIRE H=0x700000020000 OLD=0x7ffff7ec4000 NEW=0
DIAG_LOCKED_DEFINITION H=0x700000020000 handler=1
DIAG_REVOKED_H_INSTALL H=0x700000020000
DIAG_LOCKED_RETIRE H=0x700000020000
```

Then the kernel installs generation 2 at the same numeric T:

```text
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
DIAG_REVOKED_H_COMPILE H=0x700000020000
```

The old H no longer reaches the replacement code. The process exits 139 through the intentionally revoked synthetic route instead of returning 222.

This proves the required ordering:

```text
retire dependent H while old mapping generation is still identifiable
    -> exact-evict compiled/cached H
    -> leave H revoked
    -> perform destructive MAP_FIXED replacement
```

Same numeric address alone cannot revive the bridge.

### Explicit fresh registration reactivates the new generation

The positive control repeats the same retirement, then issues a fresh guest `LinkAddressToFunction(H, T)` after generation 2 is installed:

```text
VMA explicit-reregister H=0x700000020000 T=0x7ffff7ec4000 generation=2
DIAG_LOCKED_DEFINITION H=0x700000020000 handler=1
DIAG_REVOKED_H_ACTIVATE H=0x700000020000 T=0x7ffff7ec4000
DIAG_MULTI_ACTIVE H=0x700000020000 T=0x7ffff7ec4000
VMA after-map-fixed value=222 reregister=1
```

That case exits 0.

So the discriminator is exactly the desired one:

```text
same-address replacement without new ownership claim -> old H unavailable
same-address replacement + explicit fresh claim       -> H reaches generation 2
```

## Additional observation: loader/runtime MAP_FIXED traffic

The pre-retire diagnostic sees several other `MAP_FIXED` operations during normal guest process startup, including large and multi-page ranges. Those produce only `DIAG_MAP_FIXED_PREPARE` when no tracked thunk target lies inside them.

This reinforces why a production implementation should avoid a global CustomIR scan for every replacement and instead maintain reverse owner/dependency bookkeeping. The causal range scan is correct for this controlled case but can be unnecessarily broad on common loader mapping traffic.

## What this result proves

The causal run establishes three things independently:

1. `MAP_FIXED` is a real mapping-generation lifetime boundary for thunk guest targets.
2. Retirement must occur before the host replacement destroys the old mapping generation.
3. Existing exact H invalidation + revoked-H state is sufficient after the dependency is identified; a fresh explicit claim can safely reactivate H for the new generation.

The remaining production work is identity and transaction semantics, not the H state machine itself.

## Production follow-on

Replace the range scan with mapping-generation ownership as detailed in [`OWNER_TOKEN_IMPLEMENTATION_SKETCH.md`](./OWNER_TOKEN_IMPLEMENTATION_SKETCH.md):

- non-reusable owner ID visible from VMA entries and mapped resources;
- claims store `{owner_id, target_address}`;
- reverse dependency index owner -> thunk claims/callback bridges;
- prepare retirement before destructive mapping operation;
- commit fresh VMA owner state after syscall success;
- rollback the complete claim set and active/standby ordering on syscall failure;
- explicit LinkAddress registration reactivates a revoked H for the new owner generation.

The in-flight peer-dispatch race remains a separate production problem.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes are in repositories owned by `teamleaderleo`.
