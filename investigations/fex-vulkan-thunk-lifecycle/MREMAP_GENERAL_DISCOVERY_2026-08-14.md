# FEX general `mremap` discovery matrix — 2026-08-14

Internal real-FEX ARM64 Actions experiment. Pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`.

## Carrier

- FEX branch: `ci/mremap-general-owner-matrix-20260814`
- carrier head: `5af8121af721ed6cae659e202c29172dd5c4fa9d`
- Actions run: `31792769322`
- job: `94743169160`
- artifact: `mremap-general-owner-31792769322`
- artifact ID: `9216240311`
- artifact digest: `sha256:0d89c281b14c820887e08eee38b551ebc228bcc0d05e36244693bf9dfa0c1c48`

Candidate includes the owner-aware thunk lifetime work plus the green `MREMAP_FIXED` and `MREMAP_DONTUNMAP` repairs.

## Matrix

```text
move=139
move-reregister=139
grow=0
shrink-reuse=0
```

## Forced non-fixed move

A one-page executable source was followed by a reserved blocker. H was registered to the source and warmed to `111`. Expanding to two pages with `MREMAP_MAYMOVE` forced the kernel to relocate the mapping.

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000050000 T=0x7ffff7ebe000 owner=0xf new=1
MREMAP_GENERAL move-warm H=0x700000050000 src=0x7ffff7ebe000 value=111 reregister=0
MREMAP_GENERAL move-committed old=0x7ffff7ebe000 new=0x7ffff7ec3000 moved-value=111 reregister=0
```

The final H call exits `139`: the source content moved away while the old H claim remained active.

With explicit registration at the new address:

```text
MREMAP_GENERAL move-committed old=0x7ffff7ebe000 new=0x7ffff7ec3000 moved-value=111 reregister=1
DIAG_OWNER_CLAIM_STANDBY H=0x700000050000 T=0x7ffff7ec3000 owner=0xf new=1
MREMAP_GENERAL move-reregister H=0x700000050000 T=0x7ffff7ec3000
```

The moved mapping preserved owner `0xf`; the obsolete old-address claim blocked the explicit new-address claim, and H again exited `139`.

This is the non-fixed analogue of the `MREMAP_DONTUNMAP` content-move defect.

## In-place grow control

The following page was made free and `mremap(src, page, 2*page, 0)` stayed at the same address:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000051000 T=0x7ffff7ec3000 owner=0xf new=1
MREMAP_GENERAL grow result=0x7ffff7ec3000 src=0x7ffff7ec3000 H-value=111 same=1
```

This is the compatibility control: whole-source retirement on every remap would incorrectly revoke a valid pointer whose executable content stayed at the same address.

## In-place shrink + same-address tail reuse

A two-page executable mapping contained:

```text
H_keep -> page 0 -> 111
H_tail -> page 1 -> 222
```

The mapping shrank in place to one page, then the now-free tail VA was reused with `MAP_FIXED_NOREPLACE` for unrelated code returning `333`.

Current candidate result:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000052000 T=0x7ffff7ec3000 owner=0xe new=1
DIAG_OWNER_CLAIM_ACTIVE H=0x700000053000 T=0x7ffff7ec4000 owner=0xe new=1
MREMAP_GENERAL shrink-warm keep=0x7ffff7ec3000 tail=0x7ffff7ec4000 values=111,222
MREMAP_GENERAL shrink-final keep-value=111 tail-value=333 reused=0x7ffff7ec4000 expected-current-gap=333
```

The retained-prefix H stays correct. The truncated-tail H silently executes unrelated code at the reused numeric address without a new H registration.

Because tail reuse used `MAP_FIXED_NOREPLACE`, the existing `MAP_FIXED` retirement hook never participates. The defect belongs to shrink retirement itself.

## Derived transaction rule

The old range must be split according to the requested remap and the kernel result:

- definite content moves (`MREMAP_FIXED`, `MREMAP_DONTUNMAP`) -> retire whole old source;
- non-fixed `MREMAP_MAYMOVE` grow/same-size -> prepare whole source, commit when result moved, rollback when result stayed;
- shrink -> prepare truncated tail always; when `MREMAP_MAYMOVE` is present also prepare retained prefix;
  - result stayed -> rollback prefix, commit tail;
  - result moved -> commit prefix and tail;
- no-MAYMOVE in-place grow -> no source retirement;
- `old_size == 0` mirror -> no source retirement.

A causal repair carrier has been launched on `ci/mremap-general-lifetime-repair-20260814` to test this exact decision matrix.
