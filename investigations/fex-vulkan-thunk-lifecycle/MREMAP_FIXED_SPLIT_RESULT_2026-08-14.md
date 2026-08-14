# FEX thunk lifetime: MREMAP_FIXED split-effects result — 2026-08-14

Carrier: `teamleaderleo/FEX` branch `ci/mremap-fixed-owner-reuse-20260814`

Discovery run: `31787677084`

Artifact: `mremap-fixed-owner-reuse-31787677084`

Digest: `sha256:e207bb3523af90a1207389c99206192f3f6eecb05ede24e57c315cfbbcc08098`

The workflow's final assertion was still written for the earlier one-effect hypothesis, so the job is red. Probe execution itself completed successfully in both cases and produced the split discriminator below. The stale assertion is retained as harness evidence and was repaired in carrier commit `8709e9d1e1d6700c1727f08c9813cc37074930ac`.

## Matrix

```text
no-reregister=0
reregister=0
```

## Setup

```text
T destination owner = 0xe, code returns 111
S source owner      = 0xf, code returns 222
H = 0x700000030000 -> T
```

Then:

```c
mremap(S, page, page, MREMAP_MAYMOVE | MREMAP_FIXED, T)
```

The source VMA owner moves to T. A later owner query is observed indirectly by fresh registration as owner `0xf`.

## Effect 1: stale translated destination code

Immediately after successful `MREMAP_FIXED`, direct execution at T returns the old destination body:

```text
MREMAP_REUSE committed H=0x700000030000 T=0x7ffff7ec4000 source-owner-moved sentinel=222 reregister=0
MREMAP_REUSE direct-before-invalidate value=111
```

The fixture then performs permission-only T RX -> RW -> RX. Owner tracking confirms the moved source owner remains stable:

```text
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xf after=0xf prot=0x3
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xf after=0xf prot=0x5
```

After that ordinary code invalidation boundary, direct T execution sees the moved source bytes:

```text
MREMAP_REUSE direct-after-invalidate value=222
```

Therefore successful `MREMAP_FIXED` currently leaves a stale translated/code-link view of the overwritten destination VA. The kernel bytes and VMA owner have changed, while FEX continues executing translation generated from the destroyed destination mapping until a later invalidation event.

## Effect 2: stale destination H ownership

No-reregister case after the permission invalidation:

```text
MREMAP_REUSE final H-value=222 reregister=0 direct-before=111 direct-after=222
```

The old H claim was registered against destination owner `0xe` before the move. No owner-retirement diagnostics fire for that claim during `mremap`. Once T's stale translation is invalidated, the old H claim simply reaches the same numeric T now owned by `0xf` and executes `222`.

This is the same address-versus-lifetime failure family as destructive `MAP_FIXED`, reached through `MREMAP_FIXED` destination replacement.

The explicit-reregister case makes the claim-table error visible:

```text
DIAG_OWNER_CLAIM_STANDBY H=0x700000030000 T=0x7ffff7ec4000 owner=0xf new=1
MREMAP_REUSE final H-value=222 reregister=1 direct-before=111 direct-after=222
```

Fresh registration correctly discovers owner `0xf`, yet the dead destination owner `0xe` remains the active H claim. The live owner becomes standby.

## Repair consequences

`MREMAP_FIXED` needs a pre-syscall lifetime transaction covering both old address ranges:

1. **old source range** — concrete guest pointers to the source VA become stale when the mapping moves, even though the mapping's owner ID survives at the returned VA;
2. **old destination range** — the destination mapping is destroyed and every claim owned by that mapping generation must retire.

On success:

- commit both prepared retirements;
- invalidate translated/code-link state for the destination replacement range before execution can observe the replacement;
- move the source VMA owner identity to the returned VA;
- let fresh explicit H/callback registrations bind to that surviving owner at its new address.

On syscall failure:

- roll back both prepared claim-retirement snapshots;
- keep source and destination VMA ownership unchanged;
- conservative code recompilation is acceptable, but pointer ownership must remain intact.

The source-owner ID alone cannot identify retained thunk validity after a move because claims also contain concrete guest target addresses. Owner identity and address lifetime are both required.

## Clean receipt rerun

Carrier commit `8709e9d1e1d6700c1727f08c9813cc37074930ac` updates the Actions assertion to require:

```text
direct-before-invalidate = 111
direct-after-invalidate  = 222
H no-reregister          = 222
fresh owner-0xf claim    = standby
```

The rerun is the clean confirmation receipt for these two current-candidate defects.
