# FEX thunk lifetime: MREMAP_FIXED destination reuse — 2026-08-14

## Initial lane

Carrier: `teamleaderleo/FEX` branch `ci/mremap-fixed-owner-reuse-20260814`

Run: `31787295957`

Artifact: `mremap-fixed-owner-reuse-31787295957`

Digest: `sha256:2f25187326780e4bb078fe8ce71c7c8c2dba8afcc4c9dc369c9a488c9ca3c0c1`

## Fixture

Two anonymous executable pages are created:

```text
destination T: owner 0xe, returns 111
source S:      owner 0xf, returns 222
H = 0x700000030000 -> T
```

After warming H, the guest executes:

```c
mremap(S, page, page, MREMAP_MAYMOVE | MREMAP_FIXED, T)
```

Linux therefore destroys the old destination mapping and moves the source mapping onto T's numeric VA.

Cases:

- no new H registration;
- explicit `LinkAddressToFunction(H, T)` after the move.

## Initial matrix

The discovery assertion expected both cases to reach `222`; the workflow failed that expectation after product execution:

```text
no-reregister=6
reregister=6
```

Both cases actually returned `111` through H.

No-reregister key lines:

```text
DIAG_OWNER_MPROTECT addr=0x7ffff7ec4000 before=0xe after=0xe prot=0x5
DIAG_OWNER_MPROTECT addr=0x7ffff7ec3000 before=0xf after=0xf prot=0x5
DIAG_REVOKED_H_ACTIVATE H=0x700000030000 T=0x7ffff7ec4000 thread=...
DIAG_OWNER_CLAIM_ACTIVE H=0x700000030000 T=0x7ffff7ec4000 owner=0xe new=1
MREMAP_REUSE warm H=0x700000030000 dst=0x7ffff7ec4000 src=0x7ffff7ec3000 value=111
MREMAP_REUSE committed H=0x700000030000 T=0x7ffff7ec4000 source-owner-moved sentinel=222 reregister=0
MREMAP_REUSE final value=111 reregister=0
```

Explicit-reregister key lines add:

```text
DIAG_OWNER_CLAIM_STANDBY H=0x700000030000 T=0x7ffff7ec4000 owner=0xf new=1
MREMAP_REUSE final value=111 reregister=1
```

## Two effects are overlapping

### 1. Destination-owner retirement is missing

After the move, a fresh H registration queries T and receives owner `0xf`, proving the source owner moved onto the destination VA. The original owner-`0xe` H claim remains active, however. Fresh owner `0xf` is therefore added only as a standby claim.

So `MREMAP_FIXED` currently fails to retire the old destination owner claim before the kernel replaces that mapping.

### 2. Destination translated code also appears stale

Even after the source bytes returning `222` occupy T, H continues to return `111`. That suggests FEX retained the compiled destination block or direct link across `MREMAP_FIXED`.

This stale-code effect masks the ownership bug: the old active H claim still points to numeric T, but T's old compiled translation produces `111` instead of observing the new source bytes.

## Follow-up lane

Run `31787677084` is the split-effects follow-up. The fixture now:

1. direct-calls T immediately after `mremap`;
2. records the result as `direct-before-invalidate`;
3. performs T RX -> RW -> RX without changing its bytes, preserving the moved source owner while forcing code invalidation;
4. direct-calls T again as `direct-after-invalidate`;
5. calls H with and without explicit re-registration.

Expected discriminator if both suspected bugs exist:

```text
direct-before-invalidate = 111   # stale destination translation
direct-after-invalidate  = 222   # source bytes become visible after invalidation
H without reregister      = 222   # stale owner-0xe H claim survives and now reaches generation/source owner 0xf bytes
```

The explicit re-registration case should also expose the owner-table state: if old owner `0xe` remains active, owner `0xf` will again register as standby even though it is the only VMA owner currently covering T.

## Repair model implied by MREMAP_FIXED

A successful fixed move has two pointer-lifetime effects:

- the old source address ceases to designate the moved source code;
- the old destination mapping is destroyed by replacement.

The source VMA's owner ID may legitimately follow the mapping to its new address, but retained thunk/callback claims contain concrete guest target addresses. Claims to the old source address must therefore retire even though that owner ID survives elsewhere.

For `MREMAP_FIXED`, the lifetime transaction should prepare retirement for both affected old address ranges before the syscall, then:

- on success: commit retirement, invalidate destination code/link state, update VMA ownership so source owner moves to destination;
- on failure: restore prepared claims for both source and destination ranges; cache invalidation may conservatively recompile but pointer ownership must remain unchanged.

In-place grow/shrink and non-fixed moves need separate range rules. Shrink removes only the truncated tail; a successful move invalidates the old source VA while preserving the mapping owner's identity at the returned VA.
