# VMA mapping-generation owner-ID log

Date: 2026-08-14

## Purpose

The MAP_FIXED experiments have independently established:

1. retirement must happen before destructive same-address replacement;
2. a failed destructive syscall needs rollback;
3. the same numeric guest address cannot identify a mapping generation.

This log begins the identity layer: a non-reusable owner ID carried by FEX VMA tracking before thunk claims start depending on it.

Related evidence:

- [`VMA_TRANSITION_LOG.md`](./VMA_TRANSITION_LOG.md)
- [`MAP_FIXED_PRE_RETIRE_LOG.md`](./MAP_FIXED_PRE_RETIRE_LOG.md)
- [`MAP_FIXED_ROLLBACK_LOG.md`](./MAP_FIXED_ROLLBACK_LOG.md)
- [`OWNER_TOKEN_IMPLEMENTATION_SKETCH.md`](./OWNER_TOKEN_IMPLEMENTATION_SKETCH.md)

## Prototype representation

Owned FEX branch:

```text
ci/vma-owner-id-20260814
```

Helper:

```text
.github/fieldwork/add_vma_owner_id.py
```

Current carrier:

```text
57b4626930a7731186b3a7a9c68ad4ec9c8ec472
```

Actions run:

```text
31782191987
```

The prototype adds:

```text
MappedResource::OwnerID
VMAEntry::OwnerID
VMATracking::NextOwnerID
TrackVMARange(..., OwnerID = 0)
```

Zero means “allocate/derive an ID”. A file-backed VMA reuses the canonical ID already stored on its `MappedResource`; a private anonymous mapping gets a fresh ID directly on its VMA entry.

`mremap` explicitly carries the old ID when preserving/moving a mapping generation.

## Split rules under test

The VMA split paths copy `OwnerID` into newly created entries:

```text
DeleteVMARange partial split -> same owner ID on surviving pieces
mprotect split               -> same owner ID on every split piece
```

The first runtime matrix focuses on the rules most relevant to the known thunk ABA:

```text
map-fixed-fail
map-fixed
map-fixed-reregister
mprotect-owner
```

## Required identity results

### Failed MAP_FIXED

The old VMA remains live, so the tracked old generation must remain the same. The diagnostic prints:

```text
DIAG_OWNER_MAP_FIXED addr=T old=<id> new=0 success=0
```

Rollback should restore H -> old T, as already proven by the transaction layer.

### Successful MAP_FIXED replacement

A new mapping generation is installed at the same T, so:

```text
old != 0
new != 0
old != new
success=1
```

The numeric address remains identical while the owner ID changes.

### mprotect

Permission changes are not mapping-generation replacement. The new `mprotect-owner` guest control performs:

```text
RX T returning 111
-> RW
-> write code returning 333
-> RX
-> existing H calls T and returns 333
```

Every owner diagnostic for T must show:

```text
before == after != 0
```

This keeps ordinary pointer semantics across protection changes while still allowing code invalidation to observe modified guest text.

## Scope boundary

This stage does **not** change `LinkedHostClaims` yet. The existing range-based retirement/rollback remains active so owner-ID propagation can be validated independently.

Once the VMA identity rules are green, the next step is to change thunk claims from plain T values to `{T, OwnerID}` and add reverse owner dependency bookkeeping.

The separate in-flight dispatcher race remains outside this identity test.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
