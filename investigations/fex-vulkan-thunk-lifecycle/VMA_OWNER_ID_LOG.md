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

## Run 2 — owner-ID runtime matrix green

Actions run:

```text
31782618792
job:     94711477563
carrier: e301bdf4811089fdc6cbc1efcc1c2f2d5527b120
FEX:     71afe476751deac24adabd1adb575fd2337b6e0a
helper:  96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
```

Result: **success**.

Runtime matrix:

```text
owner-map-fixed-fail=0
owner-map-fixed=139
owner-map-fixed-reregister=0
owner-mprotect-owner=0
```

Artifact:

```text
id:      9212391042
sha256:  f68faae0d387f5b6021f3d7bda29a09bd2efb41680ef4d99f3d51c65839fedb9
```

### Failed MAP_FIXED preserves the live generation

For the target mapping `T=0x7ffff7ec4000`, the failed destructive replacement reports:

```text
DIAG_OWNER_MAP_FIXED addr=0x7ffff7ec4000 old=0xe new=0 success=0
DIAG_ROLLBACK_RESTORE H=0x700000020000 T=0x7ffff7ec4000 claims=1
VMA after-failed-map-fixed H-value=111
```

The failed syscall creates no replacement owner. The rollback layer restores the old H -> T claim and the old executable generation remains callable.

### Successful same-address replacement gets a new owner ID

The same numeric target address is destructively replaced:

```text
DIAG_OWNER_MAP_FIXED addr=0x7ffff7ec4000 old=0xe new=0xf success=1
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
```

This is the intended ABA discriminator:

```text
same T address
old OwnerID = 0xe
new OwnerID = 0xf
```

Address equality therefore no longer needs to stand in for generation identity.

The no-reregister arm exits `139` through the existing revoked-H control, while explicit generation-2 registration reactivates H and returns the new sentinel:

```text
VMA explicit-reregister H=0x700000020000 T=0x7ffff7ec4000 generation=2
VMA after-map-fixed value=222 reregister=1
```

### mprotect preserves owner identity

The protection/write/protection cycle reports:

```text
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xe after=0xe prot=0x3
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xe after=0xe prot=0x5
VMA mprotect-owner-preserved H=0x700000020000 T=0x7ffff7ec4000 value=333
```

The executable bytes changed and the existing H dispatch observed the new return value, while the mapping-generation owner stayed `0xe` throughout the permission cycle.

## Interpretation

The identity layer now has an executable proof for the key distinction:

```text
successful destructive same-address replacement -> new OwnerID
failed replacement                              -> no new owner, rollback restores old claim
mprotect permission/text cycle                  -> same OwnerID
```

This is enough to promote the next claim representation experiment from plain target addresses toward:

```text
{GuestTarget, OwnerID}
```

It remains separate from the already-proven in-flight dispatcher race. Owner IDs can reject stale/future claims across ABA replacement; they do not revoke a target another thread already selected before retirement.

## Scope boundary

This stage does **not** change `LinkedHostClaims` yet. The existing range-based retirement/rollback remains active so owner-ID propagation can be validated independently.

A staged follow-on helper exists at:

```text
.github/fieldwork/add_owner_claim_identity.py
commit: ce2742f129dfa1a0abbeb7677d7abbfe62b5ad60
```

The VMA propagation gate is now green, so that helper can be promoted to the next research discriminator.

The separate in-flight dispatcher race remains outside this identity test.

## External-contact state

No third-party/upstream interaction. All code, workflows, artifacts, and notes remain in repositories owned by `teamleaderleo`.
