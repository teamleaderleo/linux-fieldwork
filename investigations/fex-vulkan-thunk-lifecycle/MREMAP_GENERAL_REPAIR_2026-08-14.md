# FEX generalized `mremap` lifetime repair — 2026-08-14

Internal causal-repair receipt. Pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Discovery context: `MREMAP_GENERAL_DISCOVERY_2026-08-14.md`.

## Carrier

- FEX branch: `ci/mremap-general-lifetime-repair-20260814`
- carrier head: `f19f8940d31f51dac5117c17ab753c004a2ee1fd`
- Actions run: `31793308929`
- job: `94744821331`
- artifact: `mremap-general-lifetime-repair-31793308929`
- artifact ID: `9216443679`
- artifact digest: `sha256:0fb0f9afb31ccdcf94d739c41cc11fc3653a54ebeb3b407280eafdcb07b994ec`

## Candidate rule

The remap lifetime transaction is split by requested operation and kernel result.

For a nonzero old mapping:

- definite content moves (`MREMAP_FIXED`, `MREMAP_DONTUNMAP`) prepare/commit whole source;
- non-fixed `MREMAP_MAYMOVE` grow or same-size prepares whole source and commits only when the returned address moved; an in-place result rolls the source snapshot back;
- shrink prepares the truncated tail in all cases;
- a shrink that may move additionally prepares the retained prefix;
  - moved result commits prefix + tail;
  - in-place result rolls prefix back and commits tail;
- no-MAYMOVE in-place grow performs no source retirement;
- fixed destination retirement remains a separate transaction;
- failure rolls back every prepared component in reverse order.

This keeps pre-syscall retirement visibility for concurrency while allowing the post-syscall result to preserve valid pointer identity.

## Result

```text
move=139
move-reregister=0
grow=0
shrink-reuse=139
```

The changed exits are intentional: stale H is revoked after a real move/truncation, while explicit registration to a moved target and retained in-place pointers continue.

## Forced non-fixed move

No explicit re-registration:

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000050000 T=0x7ffff7ebe000 owner=0xf new=1
MREMAP_GENERAL move-warm H=0x700000050000 src=0x7ffff7ebe000 value=111 reregister=0
DIAG_MREMAP_PREPARE_SOURCE range=0x7ffff7ebe000+0x1000 dontunmap=0 fixed=0 maymove=1 shrink=0
DIAG_ROLLBACK_PREPARE token=0x1 range=0x7ffff7ebe000+0x1000 hosts=1 callbacks=0
DIAG_MULTI_DROP H=0x700000050000 T=0x7ffff7ebe000 owner=0xf ...
DIAG_MULTI_RETIRE H=0x700000050000 OLD=0x7ffff7ebe000 NEW=0
DIAG_REVOKED_H_INSTALL H=0x700000050000
DIAG_MREMAP_COMMIT_SOURCE token=0x1 moved=1 definite=0
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
MREMAP_GENERAL move-committed old=0x7ffff7ebe000 new=0x7ffff7ec3000 moved-value=111 reregister=0
DIAG_REVOKED_H_COMPILE H=0x700000050000
```

The stale H now exits `139` through the revoked definition instead of pointing at the dead old source.

With explicit re-registration:

```text
DIAG_MREMAP_COMMIT_SOURCE token=0x1 moved=1 definite=0
...
MREMAP_GENERAL move-committed old=0x7ffff7ebe000 new=0x7ffff7ec3000 moved-value=111 reregister=1
DIAG_REVOKED_H_ACTIVATE H=0x700000050000 T=0x7ffff7ec3000 ...
DIAG_OWNER_CLAIM_ACTIVE H=0x700000050000 T=0x7ffff7ec3000 owner=0xf new=1
MREMAP_GENERAL move-reregister H=0x700000050000 T=0x7ffff7ec3000
MREMAP_GENERAL move-final H-value=111 reregister=1
```

The moved mapping preserves owner `0xf`, yet the fresh registration becomes active because the obsolete old-address claim was committed away.

## In-place grow compatibility control

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000051000 T=0x7ffff7ec3000 owner=0xf new=1
MREMAP_GENERAL grow result=0x7ffff7ec3000 src=0x7ffff7ec3000 H-value=111 same=1
```

No source retirement diagnostic appears. H remains valid and returns `111`.

This is the key guard against a blanket whole-source retirement policy.

## In-place shrink with tail reuse

Two claims begin in one two-page mapping:

```text
H_keep -> page 0 -> 111
H_tail -> page 1 -> 222
```

Repair ordering:

```text
DIAG_MREMAP_PREPARE_TAIL range=0x7ffff7ec4000+0x1000 maymove=0
DIAG_ROLLBACK_PREPARE token=0x1 range=0x7ffff7ec4000+0x1000 hosts=1 callbacks=0
DIAG_MULTI_DROP H=0x700000053000 T=0x7ffff7ec4000 owner=0xe ...
DIAG_MULTI_RETIRE H=0x700000053000 OLD=0x7ffff7ec4000 NEW=0
DIAG_REVOKED_H_INSTALL H=0x700000053000
DIAG_MREMAP_COMMIT_TAIL token=0x1 moved=0
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
MREMAP_GENERAL shrink-keep value=111 reused=0x7ffff7ec4000
DIAG_REVOKED_H_COMPILE H=0x700000053000
```

The retained-prefix H returns `111`. The tail H exits `139` even after unrelated code is mapped at the old tail VA. The previous silent `333` reattachment is gone.

## Conclusion

The synthetic-H dependency lifetime can follow Linux remap semantics without sacrificing valid in-place pointer identity. The practical model is operation/result-sensitive:

```text
mapping owner identity
+ executable content at a target address
+ transactional pre-retirement
+ kernel-result commit/rollback
```

This closes the tested `MAP_FIXED`, `MREMAP_DONTUNMAP`, forced movable-remap, in-place grow, and in-place shrink/reuse cases at the claim-retirement layer.

The remaining separate problem is an **already-running compiled synthetic H** that has passed H lookup before retirement. That requires the H-generation dispatch work; ordinary already-selected guest code remains on the native lifetime boundary established by the native DSO controls.
