# MREMAP_FIXED split-effects result — 2026-08-14

## Result

The split-effects follow-up to `MREMAP_FIXED_OWNER_REUSE_2026-08-14.md` completed the intended product execution and cleanly separates two lifetime/cache effects that were conflated in the initial run.

Owned-fork run:

[`31787677084`](https://redirect.github.com/teamleaderleo/FEX/actions/runs/31787677084)

Exact FEX source under the diagnostic candidate:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Artifact:

- id: `9214261275`
- name: `mremap-fixed-owner-reuse-31787677084`
- digest: `sha256:e207bb3523af90a1207389c99206192f3f6eecb05ede24e57c315cfbbcc08098`

The GitHub job is red only because its final grep still expected an older log spelling (`MREMAP_REUSE final value=...`). Both product cases themselves exit `0` and the new logs use `MREMAP_REUSE final H-value=...`.

## Fixture

Two executable pages begin with distinct mapping owners and code results:

- destination `T`, owner `0xe`, returns `111`;
- source `S`, owner `0xf`, returns `222`.

A synthetic H is warmed as `H -> T`, then the guest performs:

```c
mremap(S, page, page, MREMAP_MAYMOVE | MREMAP_FIXED, T)
```

The follow-up then direct-calls T immediately, invalidates T's translation by an RX -> RW -> RX protection cycle without changing bytes, direct-calls T again, and finally calls H.

## No-reregister case

Runtime markers:

```text
MREMAP_REUSE warm H=0x700000030000 dst=0x7ffff7ec4000 src=0x7ffff7ec3000 value=111
MREMAP_REUSE committed H=0x700000030000 T=0x7ffff7ec4000 source-owner-moved sentinel=222 reregister=0
MREMAP_REUSE direct-before-invalidate value=111
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xf after=0xf prot=0x3
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xf after=0xf prot=0x5
MREMAP_REUSE direct-after-invalidate value=222
MREMAP_REUSE final H-value=222 reregister=0 direct-before=111 direct-after=222
```

Exit is `0`.

## Explicit-reregister case

The same direct-code transition occurs:

```text
MREMAP_REUSE direct-before-invalidate value=111
MREMAP_REUSE direct-after-invalidate value=222
```

A fresh registration after the move observes source owner `0xf`, but the retained claim table still records it as standby:

```text
DIAG_OWNER_CLAIM_STANDBY H=0x700000030000 T=0x7ffff7ec4000 owner=0xf new=1
MREMAP_REUSE final H-value=222 reregister=1 direct-before=111 direct-after=222
```

Exit is also `0`.

## Interpretation

The follow-up cleanly confirms two independent effects.

### 1. Destination translated-code invalidation is missing

Immediately after successful `MREMAP_FIXED`, a **direct** call to numeric T still executes the destroyed destination mapping's old translation and returns `111`, even though source bytes returning `222` now occupy that VA.

After an explicit code-invalidation cycle, direct T returns `222`.

So the initial stale `111` result is not solely an H/owner-table problem; translated destination code/link state survives the fixed replacement until separately invalidated.

### 2. Destination owner-claim retirement is also missing

The owner tracker correctly reports the moved source mapping at T as owner `0xf` after the fixed move. Nevertheless, the old owner-`0xe` H claim remains active. A new owner-`0xf` registration is therefore placed on standby rather than becoming the sole/current active mapping claim.

This proves that mapping-owner identity and translated-code invalidation are separate obligations for a successful fixed move.

## Repair implication

A correct `MREMAP_FIXED` transaction must account for both old address ranges **before** the kernel operation:

1. prepare retirement for claims tied to the old source address range;
2. prepare retirement for claims tied to the destination range being replaced;
3. on success, commit those retirements, invalidate destination translated code/direct-link state, and move/preserve the source mapping owner's identity at the returned destination;
4. on failure, roll back prepared ownership/claim retirement. Conservative code-cache invalidation may remain acceptable, but pointer ownership must not be lost.

In-place growth/shrink and non-fixed moves need separate range semantics; this result is specifically about successful `MREMAP_FIXED` replacement.

This is fork-local diagnostic evidence, not upstream-ready contribution code.