# FEX `MREMAP_DONTUNMAP` lifetime repair — 2026-08-14

Internal causal-repair receipt. Pinned FEX base: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Discovery context is recorded in `MREMAP_DONTUNMAP_CHECKPOINT_2026-08-14.md`.

## Candidate

- FEX branch: `ci/mremap-dontunmap-lifetime-repair-20260814`
- carrier head: `56bd39ecb033b84d35525635bda1516343b52c20`
- Actions run: `31792350110`
- job: `94741872889`
- artifact: `mremap-dontunmap-lifetime-repair-31792350110`
- artifact ID: `9216082232`
- artifact digest: `sha256:79c0b47bbd83d06e642f732ba22b351a2ce906d5e9d2f84b2439cf6d2eafe628`

Mechanism:

- recognize `MREMAP_DONTUNMAP` with nonzero `old_size` as a source-content move;
- prepare a guest-range retirement transaction for the old source before the host syscall;
- keep VMA/resource OwnerID unchanged;
- rollback the source claim if the syscall fails;
- commit source retirement on success;
- avoid fixed-destination retirement because this case chooses a new free destination;
- retain the existing old-source translated-code invalidation;
- require explicit H registration at the moved address before H becomes active again.

## Result

Matrix:

```text
inspect=0
no-reregister=139
reregister=0
```

### Inspect control

```text
DIAG_OWNER_CLAIM_ACTIVE H=0x700000040000 T=0x7ffff7ec4000 owner=0xe new=1
DONTUNMAP warm H=0x700000040000 src=0x7ffff7ec4000 value=111
DIAG_MREMAP_PREPARE_SOURCE range=0x7ffff7ec4000+0x1000 dontunmap=1 fixed=0
DIAG_ROLLBACK_PREPARE token=0x1 range=0x7ffff7ec4000+0x1000 hosts=1 callbacks=0
DIAG_MULTI_DROP H=0x700000040000 T=0x7ffff7ec4000 owner=0xe range=0x7ffff7ec4000+0x1000
DIAG_MULTI_RETIRE H=0x700000040000 OLD=0x7ffff7ec4000 NEW=0
DIAG_REVOKED_H_INSTALL H=0x700000040000
DIAG_ROLLBACK_COMMIT token=0x1 snapshot=1
DONTUNMAP old-bytes=000000000000
DONTUNMAP new-bytes=b86f000000c3
DONTUNMAP moved src=0x7ffff7ec4000 new=0x7ffff7ec3000 moved-value=111 reregister=0 inspect=1
DONTUNMAP inspect old-zero=1 new-code=1 moved-value=111
```

This shows the claim is retired before the content move, while the operation still produces the expected old-zero/new-code virtual-address state.

### No re-registration

```text
DIAG_MULTI_DROP H=0x700000040000 T=0x7ffff7ec4000 owner=0xe ...
DIAG_REVOKED_H_INSTALL H=0x700000040000
...
DONTUNMAP moved src=0x7ffff7ec4000 new=0x7ffff7ec3000 moved-value=111 reregister=0 inspect=0
DIAG_REVOKED_H_COMPILE H=0x700000040000
```

The final H call exits `139` through the revoked synthetic definition. The old source address surviving with owner `0xe` no longer keeps its obsolete H claim active.

### Explicit re-registration

```text
DIAG_REVOKED_H_INSTALL H=0x700000040000
...
DONTUNMAP moved src=0x7ffff7ec4000 new=0x7ffff7ec3000 moved-value=111 reregister=1 inspect=0
DIAG_REVOKED_H_ACTIVATE H=0x700000040000 T=0x7ffff7ec3000 ...
DIAG_OWNER_CLAIM_ACTIVE H=0x700000040000 T=0x7ffff7ec3000 owner=0xe new=1
DONTUNMAP reregister H=0x700000040000 T=0x7ffff7ec3000
DONTUNMAP final H-value=111 reregister=1 old-zero=1 moved-value=111
```

The new target intentionally carries the same owner ID `0xe`. The repair still lets it become active because the old target claim was retired by the content-move event.

## Conclusion

This closes the discovery gap without inventing a new VMA generation for the old surviving mapping. The key distinction is:

```text
VMA/resource owner lifetime != executable content lifetime at one target address
```

OwnerID remains useful for dependency indexing and destructive mapping replacement. Claim retirement must also observe operations that move/remove executable content while preserving the mapped owner.

For in-flight dispatch, this result strengthens the separate H-generation direction recorded in `H_GENERATION_DISPATCH_DESIGN_2026-08-14.md`: VMA OwnerID cannot serve as the universal compiled-H validity token because it remains `0xe` across this successful `DONTUNMAP` transition.
