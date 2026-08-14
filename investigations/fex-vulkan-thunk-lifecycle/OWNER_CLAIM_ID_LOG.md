# Retained thunk-claim owner identity log

Date: 2026-08-14

## Purpose

The VMA owner-ID experiment proved that two executable mapping generations can occupy the same numeric guest address while carrying distinct non-reusable owner IDs.

This stage binds that identity to FEX's retained native-H -> guest-target claim bookkeeping.

The target claim representation becomes conceptually:

```text
{GuestTarget T, OwnerID}
```

instead of treating `T` alone as the claim identity.

## Exact carrier

Owned FEX branch:

```text
ci/thunk-owner-claim-id-20260814
carrier: 85f32a5dd110d9e86bee8ca9bdc724a98e36dcd4
FEX:     71afe476751deac24adabd1adb575fd2337b6e0a
helper:  96d3d1aff38f986f6e8e36e5afd10c04cfe67cf2
```

Actions:

```text
run: 31783294674
job: 94713523354
```

Artifact:

```text
id:      9212644152
sha256:  7eb54a65a11b2cb9b3c98d46d691afc41e27fe419c80e3991c52d592a40d77cc
```

## Source transform

The staged helper adds a mapping-owner query at the runtime boundary and changes retained host claims from plain targets to owner-aware entries.

Conceptually:

```text
LinkedHostClaims[H] = [{Target, OwnerID}, ...]
```

Duplicate claim identity becomes the pair:

```text
(Target, OwnerID)
```

This allows a same-address ABA replacement to publish a fresh claim even when the native H and numeric guest T are bit-identical to the prior generation.

Helper:

```text
.github/fieldwork/add_owner_claim_identity.py
```

## Runtime matrix

```text
claim-map-fixed-fail=0
claim-map-fixed=139
claim-map-fixed-reregister=0
claim-mprotect-owner=0
```

The matrix intentionally preserves the previous retirement/rollback controls.

## Same H, same T, distinct generation claims

The decisive `map-fixed-reregister` trace uses:

```text
H = 0x700000020000
T = 0x7ffff7ec4000
```

Generation 1 registration:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0xe new=1
```

Destructive replacement then installs generation 2 at the exact same numeric target address:

```text
DIAG_OWNER_MAP_FIXED addr=0x7ffff7ec4000 old=0xe new=0xf success=1
VMA replaced-same-address H=0x700000020000 T=0x7ffff7ec4000 generation=2 sentinel=222
```

Explicit generation-2 registration produces another fresh active claim:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0xf new=1
VMA after-map-fixed value=222 reregister=1
```

The workflow asserts the exact discriminator:

```text
OWNER_CLAIM_GENERATION_OK
('0x700000020000', '0x7ffff7ec4000', '0xe', '1')
('0x700000020000', '0x7ffff7ec4000', '0xf', '1')
```

So the runtime now distinguishes:

```text
same H
same T
owner 0xe -> generation 1
owner 0xf -> generation 2
both registrations classified as new claims
```

## Failed replacement rollback

The failed `MAP_FIXED` control still returns `0`.

Trace:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000020000 T=0x7ffff7ec4000 owner=0xe new=1
DIAG_ROLLBACK_PREPARE token=0x1 ... hosts=1
DIAG_MULTI_DROP H=0x700000020000 T=0x7ffff7ec4000 owner=0xe ...
DIAG_OWNER_MAP_FIXED addr=0x7ffff7ec4000 old=0xe new=0 success=0
DIAG_ROLLBACK_RESTORE H=0x700000020000 T=0x7ffff7ec4000 claims=1
VMA after-failed-map-fixed H-value=111
```

No replacement owner is created. The transaction restores the old claim and the old generation remains callable.

## Successful replacement without re-registration

The control arm exits `139` after successful same-address replacement because H remains revoked until a new generation claim is published.

This preserves the intended future-dispatch safety property: numeric target address reuse does not silently reactivate an old claim.

## mprotect preserves claim generation

The permission/text-change control returns `0` while owner `0xe` remains stable across RX -> RW -> RX and the existing H observes the modified code value `333`.

This keeps ordinary mapping-preserving permission transitions in the same generation.

## Interpretation

The research runtime now has executable proof for the identity chain:

```text
VMA mapping generation -> OwnerID
retained thunk claim    -> {T, OwnerID}
same-address ABA        -> distinct claim identity
failed replacement      -> rollback old claim
successful replacement  -> old claim stays retired until fresh owner claim
```

This closes the future-claim ABA hole in the research model.

It does not close the independent select-before-unmap race. A thread that already selected executable T before retirement still needs an execution-lifetime rule if that T can be physically reclaimed.

That separation is useful:

```text
OwnerID + claim identity -> future registration/dispatch correctness
quiescence/lease/epoch   -> already-selected execution safety
```

## Next discriminator

The next true-unload runtime layer should bind callback-target registrations to owner identity as well, then place the actual guest callback target in a separately unloadable DSO.

The important test is whether stale native callback state can be rejected/rebound across target-owner replacement while preserving the already-demonstrated resident `CallbackUnpack` path.

## External-contact state

No third-party/upstream interaction. All code, runs, artifacts, and records remain on repositories owned by `teamleaderleo`.
