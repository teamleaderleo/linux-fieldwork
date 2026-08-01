# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap` | exact current `master` unresolved | Canonical destination named by issue #212; retrieval failed in this runtime. |
| Primary implementation | `tarfilter` | current canonical blob unresolved | Rebase target. |
| Imported implementation | `upstream/mmdebstrap/tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Baseline used by retained tests. |
| Corroborating mirror | `deepin-community/mmdebstrap:tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Exact blob equality only; this mirror is not treated as canonical or current. |
| Focused tests | `tests/test_tarfilter_transform_regex_candidate.py` | blob `57409a8e727c237dcddbdf508be6e94dd57b326f` | Baseline and core GNU differential matrix. |
| Edge tests | `tests/test_tarfilter_transform_regex_edge_cases.py` | blob `3b45d959122dc8f4a630cf144f176ecdabe7d3fb` | Python groups, malformed intervals, unmatched close, repeated quantifiers. |
| Upstream tests | canonical mmdebstrap test entry points | unresolved | Must be identified after exact Salsa checkout. |
| Contribution instructions | canonical Salsa project | unresolved current text | Read before any authorized submission. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #397 | unit 01 | priority, scope, and completion gate | canonical coordination |
| Issue #212 | release-candidate record | defect, evidence, draft, and remaining gates | canonical unit record |
| PR #113 | head `54d5f67d84f1dfb10d1e2c9079026aea5e1f41dd`; merge `9a058c2f6df430fa788c958f61f3a3e6c995e713` | GNU tar 1.35 characterization and negative controls | evidence |
| PR #68 | head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`; merge `e7388243f3436ceda16f9d5be70d5423cc379b9d` | target scopes and prerequisite transform behavior | component prerequisite |
| PR #102 | head `46f49d04639d6baf43243e5096175866c7e6a58e`; merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7` | numeric occurrence selectors | component prerequisite |
| PR #151 | head `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`; merge `1a1952a78f79b2473f1f9513c1d5820f58987594` | core dialect translator and matrix | canonical implementation carrier |
| PR #202 | head `383e60c9e2a5666ec1c9e5815edf6126f5a6379f`; closed unmerged | Python-only special-group repair | superseded component carrier |
| PR #211 | head `c76e01b3f2cc180a8d5dda2b94047361a39a372e`; merge `67cea0c3882250664fdf8d362c7c9d40ce4d6611` | release-desk issue/MR drafts | draft/evidence carrier |
| PR #216 | head `55d20a4cc08c93b34961c679bdb73458fea4c408`; merge `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` | malformed interval and unmatched-close repair; consolidated latest state | canonical repair carrier |
| Linux Fieldwork main at claim | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | packet workflow base | branch base |

## Ordered patch inputs

| Order | File | Git blob | Role |
| ---: | --- | --- | --- |
| 1 | `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch` | `1703984aa0c030e5131618a3541ee85bfd68ec65` | target and PAX prerequisite state |
| 2 | `investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch` | `81828a468854e7ec9ef4cda9626b9c57314afba3` | numeric occurrence prerequisite |
| 3 | `investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-dialects.patch` | `2d7c457b83700d51b173efd0825128b6853a5f47` | BRE/ERE translator and core grammar |
| 4 | `investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-edge-cases.patch` | `9994ac2272f23872b7f6e00a20f7282cb9b8cce3` | repeated quantifiers, Python groups, malformed intervals, unmatched close |

## Candidate code

| File | Symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `tarfilter` | transform parsing and substitution helpers | target scopes and replacement state prerequisite | patch 1 |
| `tarfilter` | match-position selection | numeric occurrence handling | patch 2 |
| `tarfilter` | `_translate_pattern()` and parser flags | GNU basic/extended translation and unsupported-form rejection | patch 3 |
| `tarfilter` | `_quantifier_at()`, `_normalize_repeated_quantifiers()`, group/interval checks | edge/parity normalization and rejection | patch 4 |

## Candidate tests

| File | Test area | Baseline result | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_tarfilter_transform_regex_candidate.py` | default `s/a+/b/` on `aaa` | predecessor produces `b`; GNU tar produces `aaa` | candidate and GNU tar both produce `aaa` |
| same | `x` flag | predecessor rejects | candidate follows characterized extended syntax |
| same | basic captures/backrefs | predecessor rejects valid GNU form | candidate matches GNU result |
| same | operators, anchors, targets, occurrences | direct-Python or unsupported behavior | candidate equals GNU tar 1.35 under `LC_ALL=C` |
| `tests/test_tarfilter_transform_regex_edge_cases.py` | Python `(?...)` groups | Python accepts some forms GNU rejects | candidate rejects before archive output |
| same | malformed active intervals | Python may compile literals GNU rejects | candidate rejects before output |
| same | unmatched extended `)` | Python rejects | candidate treats it literally when no group is open |
| same | repeated quantifiers | Python lazy/possessive/error semantics diverge | candidate normalizes the executed GNU nested semantics |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS FORK`
- Retained patch series: the four files and blobs above
- Intended application command, from a Linux Fieldwork checkout with a candidate tree rooted like the repository:

```sh
patch -p1 -d "$candidate_root" -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch -p1 -d "$candidate_root" -i investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch
patch -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-dialects.patch
patch -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-edge-cases.patch
```

Current-source work must start from an exact canonical Salsa checkout and regenerate patches when context changed; fuzz or offsets are outside the ready gate.

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| transform dialect selection | implicit Python `re` syntax | parser selects basic by default and extended with `x` | PR #151 and core test matrix |
| pattern translation | absent | stateful translator before `re.compile()` | patch 3 |
| unsupported grammar rejection | Python compiler or silent acceptance | transform parser before archive input/output | patches 3 and 4; focused tests |
| repeated quantifier semantics | Python parser | explicit normalization for executed GNU cases | patch 4; edge tests |
| malformed active interval ownership | Python literal/compiler behavior | explicit parser rejection | PR #216; edge tests |
| unmatched extended close | Python compiler rejection | escaped literal when no group is open | PR #216; edge tests |
| member/link target application | predecessor transform path | target-scope prerequisite | PR #68 / patch 1 |
| occurrence counting | absent or ordinary `re.sub` | per-field selected-match state | PR #102 / patch 2 |

## Overlap and current upstream state

Internal searches recorded by #212 found no competing source translator and no caching/LF-23 path overlap at the repaired internal head. A fresh search of current Salsa issues, merge requests, and `master` remains mandatory after exact canonical access is available. No claim about current upstream overlap is made from mirror or package snapshots.

## Files deliberately left alone

- imported `upstream/mmdebstrap/tarfilter` remains unchanged on Linux Fieldwork `main`; retained tests apply patches to disposable copies;
- unit 15 transform target/PAX semantic work remains outside this unit except as prerequisite patch state;
- POSIX locale/class support, expression lists, persistent flags, and replacement case state remain outside the candidate;
- no external repository, fork, issue, merge request, or comment was created or changed.
