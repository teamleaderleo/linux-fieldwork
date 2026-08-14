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

## Run 1 — source-transform failure before owner-ID build

Actions run:

```text
31782191987
job:    94710193222
carrier: 57b4626930a7731186b3a7a9c68ad4ec9c8ec472
```

Result: **patch/harness failure; no owner-ID runtime result**.

Completed successfully first:

- exact baseline FEX checkout;
- base FEX/FEXServer build;
- amd64 guest rootfs assembly;
- updated `vma-linkaddress-probe` build including `mprotect-owner`.

The failure occurred while applying `add_vma_owner_id.py`, before the modified FEX compiled:

```text
mprotect original-protection split owners:
expected 3 anchors in SyscallsVMATracking.cpp, found 2
```

Artifact:

```text
id:      9212197948
sha256:  560ca669fa2d94153ae3611876c33f5400087e02afe49f19fffa44522c3adca6
```

### Cause

`ChangeProtectionFlags()` has three original-protection VMA insertions, but they are emitted in two different indentation/initializer shapes:

- merge strategy 4 tail and merge strategy 3 tail share the wider shape;
- merge strategy 2 uses a shorter indentation shape.

The first helper attempted to match all three with one exact string, so its safety assertion correctly stopped after finding only the two identical wide-form sites.

No product code ran with partially applied owner IDs.

### Repair

The helper now patches the split sites explicitly by shape:

```text
2 x wide CurrentProt initializer
1 x strategy-2 CurrentProt initializer
1 x NewProt middle-split initializer
```

Repair commit:

```text
e301bdf4811089fdc6cbc1efcc1c2f2d5527b120
```

No identity rules or runtime cases changed. Because the helper is in the branch workflow path, this repair launches a fresh owner-ID run automatically.

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

A staged follow-on helper exists at:

```text
.github/fieldwork/add_owner_claim_identity.py
commit: ce2742f129dfa1a0abbeb7677d7abbfe62b5ad60
```

It is intentionally excluded from the active workflow until VMA owner-ID propagation is green.

The separate in-flight dispatcher race remains outside this identity test.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
