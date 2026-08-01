# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap` | exact current `master` unresolved | Canonical destination named by issue #212. |
| Current Debian archive source | `https://sources.debian.org/src/mmdebstrap/1.5.7-3/` | source version `1.5.7-3`; Salsa tag `debian/1.5.7-3` abbreviated `6fde9997` | Current in sid/forky during 2026-08-01 refresh. |
| Debian archive implementation | `tarfilter` | 11,453 bytes in `1.5.7-3` | Authoritative archive observation; direct file digest was unavailable in this runtime. |
| Primary canonical implementation | Salsa `tarfilter` | current canonical blob unresolved | Required rebase target. |
| Imported implementation | `upstream/mmdebstrap/tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Baseline used by retained tests. |
| Package-version mirror | `deepin-community/mmdebstrap:tarfilter` | commit `574048f2a720057b75e56622003932f344dc700a`; file blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Commit message updates to `1.5.7-3`; corroborates imported package-generation bytes, without replacing canonical Salsa. |
| Focused tests | `tests/test_tarfilter_transform_regex_candidate.py` | blob `57409a8e727c237dcddbdf508be6e94dd57b326f` | Baseline and core GNU differential matrix. |
| Edge tests | `tests/test_tarfilter_transform_regex_edge_cases.py` | blob `3b45d959122dc8f4a630cf144f176ecdabe7d3fb` | Python groups, malformed intervals, unmatched close, repeated quantifiers. |
| Group-guard positive controls | `tests/test_tarfilter_transform_regex_python_group_controls.py` | blob `5a7bbac729caf71be6033f71d792dfde0d5f653a` | Escaped-parenthesis and bracket-state neighbors, merged through PR #220. |
| Native runner | `coverage.py`, `coverage.sh`, `coverage.txt`, `tests/` | Debian archive source `1.5.7-3` | `coverage.py` copies local `./tarfilter` into `shared/tarfilter`; README documents full and individual commands. |
| Contribution instructions | canonical Salsa project and project README | current canonical text partly unresolved | Re-read exact current tree before authorized submission. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #397 | unit 01 | priority, scope, and completion gate | canonical coordination |
| Issue #212 | release-candidate record | defect, evidence, draft, and remaining gates | canonical unit record |
| Issue #36 | parent transform-semantics defect | advertised GNU/sed contract and broader boundary | parent record |
| Issue #63 | symlink-scope correction | corrected stale PR #48 expectation | predecessor repair |
| Issue #98 | numeric occurrence selectors | prerequisite defect and boundary | predecessor record |
| Issue #108 | basic/extended dialect defect | direct unit defect and requirements | owning defect record |
| PR #48 | head `25f6bcda2a807a8901b3ff3e34f5581d6f057877`; merge `4d2550eb6a4e0765aed9f16897b4c4a9a39f119e` | path/hard-link/PAX predecessor with stale symlink claim | superseded component |
| PR #56 | head `640f414cb18cf47b3e803856392c720414bea333`; merge `ff3c9458cee438d16f8d99ca9e2e9b843d3766fe` | first/global, flags, `&`, escaped replacement behavior | component prerequisite |
| PR #68 | head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`; merge `e7388243f3436ceda16f9d5be70d5423cc379b9d` | corrected target scopes and prerequisite transform behavior | component prerequisite |
| PR #102 | head `46f49d04639d6baf43243e5096175866c7e6a58e`; merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7` | numeric occurrence selectors | component prerequisite |
| PR #113 | head `54d5f67d84f1dfb10d1e2c9079026aea5e1f41dd`; merge `9a058c2f6df430fa788c958f61f3a3e6c995e713` | GNU tar 1.35 characterization and negative controls | evidence |
| PR #151 | head `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`; merge `1a1952a78f79b2473f1f9513c1d5820f58987594` | core dialect translator, edge state, Python-group rejection | canonical product carrier |
| PR #202 | head `383e60c9e2a5666ec1c9e5815edf6126f5a6379f`; closed unmerged | parallel Python-only special-group repair | duplicate/superseded |
| PR #203 | head `ee8b25d3f878a28db2e75076bb499bcc1c884101`; closed unmerged | initial accepted-neighbor proof | superseded proof carrier |
| PR #211 | head `c76e01b3f2cc180a8d5dda2b94047361a39a372e`; merge `67cea0c3882250664fdf8d362c7c9d40ce4d6611` | release-desk issue/MR drafts | draft/evidence carrier |
| PR #216 | head `55d20a4cc08c93b34961c679bdb73458fea4c408`; merge `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` | malformed interval and unmatched-close repair; consolidated latest grammar state | canonical repair carrier |
| PR #220 | head `bb0a79dec47958c6b865d4b382a44baff17ab736`; merge `ed49c01a85e9d363626db5d2973a33b67209e13b` | accepted-neighbor proof for active-`(?` guard | canonical proof carrier |
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

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_tarfilter_transform_regex_candidate.py` | default `s/a+/b/` on `aaa` | predecessor produces `b`; GNU tar produces `aaa` | candidate and GNU tar both produce `aaa` |
| same | `x` flag | predecessor rejects | candidate follows characterized extended syntax |
| same | basic captures/backrefs | predecessor rejects valid GNU form | candidate matches GNU result |
| same | operators, anchors, targets, occurrences | direct-Python or unsupported behavior | candidate equals GNU tar 1.35 under `LC_ALL=C` |
| `tests/test_tarfilter_transform_regex_edge_cases.py` | Python `(?...)` groups | Python accepts forms GNU rejects | candidate rejects before archive output |
| same | malformed active intervals | Python may compile literals GNU rejects | candidate rejects before output |
| same | unmatched extended `)` | Python rejects | candidate treats it literally when no group is open |
| same | repeated quantifiers | Python lazy/possessive/error semantics diverge | candidate normalizes executed GNU nested cases |
| `tests/test_tarfilter_transform_regex_python_group_controls.py` | `s/\(?/X/x`, `s/[(?]/X/x`, `s/\(/X/x` | overbroad guard could reject valid neighbors | candidate and GNU tar produce `X` |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS FORK`
- Retained patch series: the four files and blobs above
- Intended application command:

```sh
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-dialects.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-edge-cases.patch
```

Current-source work must start from an exact canonical Salsa checkout and regenerate patches when context changed; fuzz or offsets are outside the ready gate.

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| transform dialect selection | implicit Python `re` syntax | parser selects basic by default and extended with `x` | PR #151 and core matrix |
| pattern translation | absent | stateful translator before `re.compile()` | patch 3 |
| unsupported grammar rejection | Python compiler or silent acceptance | transform parser before archive input/output | patches 3 and 4 |
| active Python-group guard neighbors | unproved guard ordering | accepted escaped/bracket forms retained | PR #220 and positive-control test |
| repeated quantifier semantics | Python parser | explicit normalization for executed GNU cases | patch 4 |
| malformed active interval ownership | Python literal/compiler behavior | explicit parser rejection | PR #216 |
| unmatched extended close | Python compiler rejection | escaped literal when no group is open | PR #216 |
| member/link target application | predecessor transform path | target-scope prerequisite | PR #68 / patch 1 |
| occurrence counting | absent or ordinary `re.sub` | per-field selected-match state | PR #102 / patch 2 |
| native test staging | source tree | `coverage.py` copies local `tarfilter` to `shared/tarfilter` | Debian source `1.5.7-3` coverage runner |

## Overlap and current upstream state

Search date: `2026-08-01`.

- Debian BTS package listing for current `mmdebstrap 1.5.7-3` was searched for `tarfilter`, `transform`, and regex-dialect equivalents; no matching open carrier appeared.
- Web-indexed Salsa issue/MR searches for `tarfilter transform regex` returned no equivalent carrier.
- Exact Salsa `master` source and complete live issue/MR inventory remain inaccessible in this runtime, so the overlap gate remains open.
- Internal searches recorded by #212 found no competing source translator and no caching/LF-23 path overlap at the repaired internal head.

## Files deliberately left alone

- imported `upstream/mmdebstrap/tarfilter` remains unchanged on Linux Fieldwork `main`; retained tests apply patches to disposable copies;
- unit 15 transform target/PAX semantic work remains outside this unit except as prerequisite patch state;
- POSIX locale/class support, expression lists, persistent flags, and replacement case state remain outside the candidate;
- no external repository, fork, issue, merge request, or comment was created or changed.
