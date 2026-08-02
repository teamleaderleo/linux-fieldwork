# Handoff — unit 16 link-before-target review

State: `ACTIVE — direct extractor evidence retained; exact-stack CI queued`  
Review branch: `review/unit-16-link-before-target`  
Owning unit branch: `upstream/unit-16-tarfilter-type-hardlinks`  
Owning internal PR: #399  
Review PR: #415  
External contact: unauthorized; none made

## Review question

Can unit 16 claim a type-excluded hard-link dependency failure when the dependent hard-link member appears before the later target occurrence that is removed by the type filter?

## Confirmed direct evidence

Fixture order:

```text
hard link root/peer -> root/base
regular root/base
```

Fixture identity:

```text
size: 10240 bytes
sha256: dfe43b12e512307324010ad3764a24b09c6e8a40c7d0b0da2e4f40ef8fe58aea
```

- GNU tar 1.35 lists the stream but extraction exits 2 because `root/base` does not yet exist.
- Python `tarfile` extraction exits 1 with `KeyError: "linkname 'root/base' not found"`.

The complete transcript and policy analysis are in:

`../../artifacts/review-link-before-target-2026-08-02.md`

## Source observation

The selected unit-16 patch records an excluded identity only when the excluded member is encountered. A preceding hard-link member therefore cannot know that its later target will be removed. It is emitted before the state changes.

This is adjacent to, not a refutation of, the selected target-before-link behavior. Issue #335 explicitly leaves link-before-target graphs and output rollback outside the current unit.

## Added exact-stack discriminator

`tests/test_tarfilter_type_excluded_link_before_target.py`

It applies:

1. imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
2. unit-15 transform prerequisite;
3. unit-16 lifecycle/duplicate predecessor;
4. selected final-identity patch.

With `--type-exclude=REGTYPE`, it requires status 1, the existing dependency diagnostic, and a finalized empty output archive.

## Current CI state

The earlier heads `69bb033...` and `ad4345a...` are superseded by this handoff commit. Their queued workflow results must not be used as exact-head evidence.

Classify only the Linux Fieldwork CI run associated with the current review branch head.

## First incomplete step

1. record the current exact review head and its workflow run/job identities;
2. classify whether the new control fails at the expected status assertion;
3. retain the emitted member map and stderr from the exact candidate;
4. decide whether to narrow unit 16's stated premise only, or open a separate successor design for unresolved hard links;
5. do not implement buffering, reordering, two-pass spooling, or rollback without a separate compatibility matrix;
6. keep the current Salsa-master identity gate unchanged.

## Recommended current disposition

Narrow the unit-16 claim to target identities already available before the hard-link member is processed. Treat link-before-target plus later exclusion as an unresolved successor question until exact-stack CI and a separate policy decision exist.

## Cleanup

The direct fixtures and exact-stack test use temporary directories. No persistent process, socket, mount, lock, package mutation, device node, or external fork is created.
