# Source map

## Upstream and controlled-fork identities

| Item | Repository path or branch | Exact revision | Notes |
| --- | --- | --- | --- |
| Canonical implementation | `josch/mmdebstrap` `tarfilter` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; file commit prefix `87b9b385b3` | Relevant source matches the imported baseline. |
| Imported source | `upstream/mmdebstrap/tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; SHA-256 `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957` | Exact losing control. |
| Controlled fork | `teamleaderleo/mmdebstrap` | repository ID `1319064688` | User-controlled repository; no upstream interaction. |
| Controlled canonical snapshot | `linux-fieldwork/upstream-main-snapshot` | `77ec9be5417ee44c96343d2347145585da1b1f94` | Exact base for current contribution branches. |
| Controlled candidate branch | `linux-fieldwork/unit-15-tarfilter-transform-metadata` | `505bf81079a3b76c7d56bffa8097c1b5a494898e` | Three commits ahead, zero behind snapshot. |
| Candidate source | `tarfilter` | source commit `f7833615824ad99023c21a495840d10f64c6401a`; blob `adb330efcc941bf5e646f195c245a3184e42f8e2`; SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` | Exact source bytes match the retained packet candidate. |
| Upstream-native test | `tests/tarfilter-transform-metadata` | commit `f7337a7d2f33d280c8e5b1576dd729f4d076c13a`; blob `bc9fb4e0593df5a37dee986308ebb62abc4b6839`; SHA-256 `adab3852d9c8e719d64a24e1aed386d2eeccb45a43922f854d7458aa486f8caa` | Direct baseline/candidate differential and GNU tar checks. |
| Test registration | `coverage.txt` | commit/head `505bf81079a3b76c7d56bffa8097c1b5a494898e`; blob `fdac8b9f86b04e48af6476c32b649b1ed4bda95a` | Adds `Test: tarfilter-transform-metadata`. |
| Upstream runner | `coverage.py`, `coverage.sh`, `run_null.sh` | upstream base `77ec9be5417ee44c96343d2347145585da1b1f94` | Full runner invocation remains incomplete because the local materialization is not a complete mirror-backed checkout. |

## Fork history boundary

The fork's legacy `master` ends at `574048f2a720057b75e56622003932f344dc700a` and carries a separate Deepin packaging history. Git comparison reports no common ancestor between that branch and `linux-fieldwork/upstream-main-snapshot`. The legacy branch remains untouched. Unit 15 uses the exact canonical snapshot, following the project rule to preserve prior heads and prefer superseding branches over destructive replacement.

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #25 | current issue record | hard-link and stale PAX source defect | component |
| PR #48 | head `25f6bcda2a807a8901b3ff3e34f5581d6f057877`; merge `4d2550eb6a4e0765aed9f16897b4c4a9a39f119e` | original hard-link/PAX candidate with stale symlink expectation | superseded component |
| Issue #36 | current issue record | broad transform-semantics parent | canonical parent |
| Issue #51 | current issue record | first/global and `g`/`i` semantics | component |
| PR #52 | head `928c81b4fe9816d8f151eb8388356fffc2362bc7`; closed unmerged | stacked composition experiment | superseded |
| PR #56 | head `640f414cb18cf47b3e803856392c720414bea333`; merge `ff3c9458cee438d16f8d99ca9e2e9b843d3766fe` | replacement count, `g`/`i`, `&`, escapes | component |
| Issue #63 | current issue record | corrected default symlink scope | component/correction |
| PR #68 | head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`; merge `e7388243f3436ceda16f9d5be70d5423cc379b9d` | canonical integrated replacement, target-scope, hard-link, and PAX base | canonical foundation |
| Issue #98 | current issue record | numeric selectors | component |
| PR #102 | head `46f49d04639d6baf43243e5096175866c7e6a58e`; merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7` | numeric occurrence increment | canonical increment |
| Issue #397 unit 15 | Linux Fieldwork branch `upstream/unit-15-tarfilter-transform-metadata` | upstream packaging and closeout | canonical packet |

Historical exact-head workflow receipts remain in `TESTS.md` and the carrier records.

## Candidate code ownership

| File | Symbols or block | Change | Evidence |
| --- | --- | --- | --- |
| `tarfilter` | `_find_unescaped_delimiter`, `_unescape_delimiter` | delimiter-aware expression parsing | complete source diff and replacement cases |
| `tarfilter` | `_sed_replacement` | whole-match `&` and retained escapes | GNU tar differential |
| `tarfilter` | `_sed_substitute` | selected and global-after occurrence replacement | numeric matrix |
| `tarfilter` | `TransformAction.__call__` | flags, numeric selectors, and target scopes | parser controls and GNU tar differential |
| `tarfilter` | strip block | hard-link target stripping and stale PAX invalidation | long-path extraction case |
| `tarfilter` | transform block | scoped member/link mutation and PAX invalidation | scope, link, and PAX cases |
| `tests/tarfilter-transform-metadata` | shell wrapper plus Python fixture | native direct regression | baseline status 1; candidate status 0 twice |
| `coverage.txt` | test paragraph | registers native regression | fork diff and blob identity |

## Candidate test map

| Context | Discriminator | Baseline | Candidate |
| --- | --- | --- | --- |
| replacement selection | `s/a/b/` on `a/a` | test stops at `AssertionError: s/a/b/`; actual old name `b/b` | `b/a`, matching GNU tar |
| global and replacement language | `g`, `i`, `&`, escaped delimiter | unsupported or wrong count | retained matrix passes |
| target ownership | member, hard-link target, symlink target; default and `S` | link text stale | GNU-compatible scope result |
| strip and metadata | 120-byte path and hard-link target | stale `path`/`linkpath` | regenerated fields; extraction and inode identity pass |
| numeric selectors | `2`, `2g`, `g2`, `0`, `0g`, `22`, `2g3`, `i2g` | predecessor rejects numeric form | GNU-compatible result |
| parser boundary | non-ASCII numeric-looking flags | unsupported | rejected |
| recovery state | immediate rerun and `/tmp` scan | n/a | two passes; zero leftovers |

## Patch and branch references

- Linux Fieldwork branch: `upstream/unit-15-tarfilter-transform-metadata`
- Controlled fork: `teamleaderleo/mmdebstrap`
- Controlled base: `linux-fieldwork/upstream-main-snapshot` at `77ec9be5417ee44c96343d2347145585da1b1f94`
- Candidate branch: `linux-fieldwork/unit-15-tarfilter-transform-metadata`
- Candidate head: `505bf81079a3b76c7d56bffa8097c1b5a494898e`
- Retained patch: `patches/0001-tarfilter-transform-metadata.patch`
- Native receipt: `artifacts/FORK_NATIVE_TEST.txt`

Fork compare result:

```text
status: ahead
ahead_by: 3
behind_by: 0
base/merge-base: 77ec9be5417ee44c96343d2347145585da1b1f94
coverage.txt: +2/-0
tarfilter: +179/-23
tests/tarfilter-transform-metadata: +250/-0
```

## Operation ownership map

| Operation | Baseline owner | Candidate owner | Evidence |
| --- | --- | --- | --- |
| transform parsing | token regex in `TransformAction` | delimiter-aware parser carrying flags, selectors, scopes | complete source diff and direct test |
| replacement selection | Python `re.sub()` default | `_sed_substitute()` | baseline failure and numeric/replacement cases |
| member-name transform | member loop | scoped transform state in same loop | GNU tar differential |
| hard-link target transform | absent | `h/H` scope | differential and extraction |
| symlink target transform | absent | `s/S` scope | default/`S` differential |
| hard-link strip target | absent | strip block | extraction and inode identity |
| PAX path/linkpath authority | stale input dictionary | invalidated on logical-field change, then regenerated by writer | long PAX fixture |
| test discovery | no unit-15 test | `coverage.txt` paragraph matching test filename | fork diff |

## Overlap and evidence boundary

Public overlap was rechecked on 2026-08-01. Canonical upstream still exposed the same relevant baseline and no visible active equivalent transform carrier. The controlled fork branch changes no unrelated product files. This does not establish the absence of private or unindexed maintainer work.

## Files deliberately not changed

- Fork legacy `master` and its Deepin packaging history.
- Linux Fieldwork imported `upstream/mmdebstrap/tarfilter`.
- Unit 01 regex translation.
- Unit 16 hard-link dependency resolution.
- Units 18–22 passthrough, PAX identity shift, normalization, parent metadata, and typeflag work.
- Broader `flags=`, expression lists, case conversion, locale/collation, and malformed-expression parity.
