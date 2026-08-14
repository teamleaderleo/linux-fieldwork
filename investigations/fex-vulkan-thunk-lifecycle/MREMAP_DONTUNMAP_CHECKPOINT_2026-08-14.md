# FEX `MREMAP_DONTUNMAP` thunk-lifetime checkpoint — 2026-08-14

Internal research only. Pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Question

Does VMA owner-generation identity remain sufficient when `MREMAP_DONTUNMAP` keeps the old virtual address alive while moving its original page contents to a new virtual address?

The current owner-aware candidate records each dynamic synthetic `H -> T` claim as `{Target, OwnerID}`. FEX's VMA tracking intentionally retains the old VMA for `MREMAP_DONTUNMAP` and mirrors the same mapped resource/owner identity at the new address.

## Discovery carrier

- FEX branch: `ci/mremap-dontunmap-owner-20260814`
- carrier head: `f510447c13e5b8aa30b7fa446cf95d62fe270852`
- Actions run: `31791887819`
- job: `94740428803`
- artifact: `mremap-dontunmap-owner-31791887819`
- artifact ID: `9215915730`
- artifact digest: `sha256:b3d267625be51e282140ff125f47500928566d4b777f61312fd23ad9292d04b1`

Fixture:

1. map anonymous executable source page containing x86 `mov eax,111; ret`;
2. register synthetic `H = 0x700000040000 -> source`;
3. warm H and observe `111`;
4. call `mremap(source, page, page, MREMAP_MAYMOVE | MREMAP_DONTUNMAP)`;
5. inspect both virtual addresses;
6. optionally re-register H explicitly to the new address;
7. call H.

## Result

Matrix:

```text
inspect=0
no-reregister=139
reregister=139
```

The byte-level discriminator proves the executable content moved while the old VA survived:

```text
DONTUNMAP warm H=0x700000040000 src=0x7ffff7ec4000 value=111
DONTUNMAP old-bytes=000000000000
DONTUNMAP new-bytes=b86f000000c3
DONTUNMAP moved src=0x7ffff7ec4000 new=0x7ffff7ec3000 moved-value=111 reregister=0 inspect=1
DONTUNMAP inspect old-zero=1 new-code=1 moved-value=111
```

The owner-aware candidate kept the old source claim active:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000040000 T=0x7ffff7ec4000 owner=0xe new=1
```

After the move, an explicit registration for the new address saw the same owner ID and became standby:

```text
DONTUNMAP moved src=0x7ffff7ec4000 new=0x7ffff7ec3000 moved-value=111 reregister=1 inspect=0
DIAG_OWNER_CLAIM_STANDBY H=0x700000040000 T=0x7ffff7ec3000 owner=0xe new=1
DONTUNMAP reregister H=0x700000040000 T=0x7ffff7ec3000
```

The final H call exits `139` because H still points at the zero-filled old address.

## Interpretation

A VMA/resource generation identifies a mapped lifetime, while synthetic thunk claims also depend on the lifetime of executable content at a specific target address. `MREMAP_DONTUNMAP` separates those two concepts: the old VMA survives with owner `0xe`, yet the function bytes leave that address.

Therefore automatic claim retirement cannot depend only on VMA destruction or owner-ID replacement. A destructive-content transition can require retiring `{H, old target}` even while its VMA owner remains valid.

This also explains why explicit `H -> newVA` registration must be allowed to become active after the move. The old source claim has lost its executable content and should no longer block the new claim merely because both addresses share owner `0xe`.

## Causal repair under test

Branch: `ci/mremap-dontunmap-lifetime-repair-20260814`

The candidate extends the successful remap retirement transaction with a `MREMAP_DONTUNMAP` source-content rule:

- when `old_size != 0` and `MREMAP_DONTUNMAP` is set, prepare retirement for the old source range before the syscall;
- keep the VMA owner ID unchanged;
- roll the source claim back if `mremap` fails;
- commit retirement on success;
- do not prepare a destination-overwrite retirement because the kernel chooses a new free destination for this non-fixed case;
- retain the existing remap code invalidation of the old source VA;
- after success, explicit registration at the moved address should become active even though it carries the same owner ID.

Expected repaired matrix:

```text
inspect=0
no-reregister=139   # H is deliberately revoked after content leaves old target
reregister=0        # explicit H -> moved target becomes active and returns 111
```

The distinction from ordinary in-place `mremap` is important. An in-place resize can preserve executable pointer identity in the retained prefix, so source retirement must be tied to operations that actually move/remove target content, not every `mremap` call indiscriminately.
