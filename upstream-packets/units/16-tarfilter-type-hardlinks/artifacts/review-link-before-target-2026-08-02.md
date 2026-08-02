# Unit 16 review — hard link before later target

Date: 2026-08-02  
Review branch: `review/unit-16-link-before-target`  
Review PR: #415  
External contact: unauthorized; none made

## Question

Does the selected unit-16 implementation cover a retained hard link that appears before its target when the later target is removed by `--type-exclude`?

## Source observation

The selected patch records an identity in `type_excluded_members` only when the excluded member is encountered. A preceding hard-link member therefore sees neither a retained target nor a known excluded target and is emitted. When the later target is excluded, no retroactive dependency check removes or rejects the already-emitted link.

This is a different lifecycle topology from unit 16's selected and tested premise, where the target occurrence is processed before the dependent hard link. Issue #335 explicitly kept link-before-target graphs and output rollback separate.

## Direct archive discriminator

The fixture contains, in order:

```text
hard link root/peer -> root/base
regular file root/base
```

Archive identity:

```text
size: 10240 bytes
sha256: dfe43b12e512307324010ad3764a24b09c6e8a40c7d0b0da2e4f40ef8fe58aea
```

### GNU tar 1.35

Listing succeeds and preserves the order:

```text
hrw-r--r-- 0/0 0 2000-01-01 00:00 root/peer link to root/base
-rw-r--r-- 0/0 12 2000-01-01 00:00 root/base
```

Extraction result:

```text
status: 2
tar: root/peer: Cannot hard link to 'root/base': No such file or directory
tar: Exiting with failure status due to previous errors
```

The regular target is extracted after the failed hard-link operation; the peer is absent.

### Python 3 tarfile

Extraction result:

```text
status: 1
KeyError: "linkname 'root/base' not found"
```

Only the parent directory exists afterward.

## Added exact-stack control

`tests/test_tarfilter_type_excluded_link_before_target.py` applies:

1. exact imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
2. unit-15 prerequisite patch;
3. unit-16 lifecycle/duplicate predecessor;
4. selected final-identity patch.

It runs the fixture with `--type-exclude=REGTYPE` and requires status 1, the dependency diagnostic, and a finalized empty output archive. The initial review commit is expected to fail if the source observation is correct.

## Classification boundary

This review should not silently broaden unit 16. The current selected behavior is defensible only under an explicit premise:

> A hard-link target must already be available among retained final identities before the hard-link member is processed.

The link-before-target topology requires a separate policy choice:

- reject a target that is not yet available;
- buffer unresolved hard links until their target disposition is known;
- spool or perform a two-pass analysis to preserve order and support rollback;
- or retain existing behavior with a written unsupported-input boundary.

Immediate rejection is small but would also reject target-later archives when an unrelated type filter is active. Buffering changes member order and duplicate-name behavior. Full rollback conflicts with the current streaming output design. Those choices require their own compatibility matrix.

## Current disposition

- Unit 16 target-before-link work: continue review under a narrowed premise.
- Link-before-target plus later type exclusion: confirmed adjacent correctness gap; do not describe it as solved.
- Upstream contact: none.
