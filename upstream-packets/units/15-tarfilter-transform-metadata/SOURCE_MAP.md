# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `tarfilter` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; file commit `87b9b385b3` | Current parser and member loop retain the baseline behavior. |
| Imported source | `upstream/mmdebstrap/tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Byte identity used by the local materialization. |
| Adjacent implementation | Python `tarfile.TarInfo.name`, `linkname`, and `pax_headers` handling | Python 3.13.5 runtime used | Python regenerates long PAX fields when stale explicit values are removed. |
| Upstream tests | `tests/`, `coverage.py`, `coverage.sh` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94` | No focused upstream tarfilter transform test was executed in this pass. |
| Build or package metadata | repository root and Debian packaging | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94` | Full package gates remain. |
| Contribution instructions | upstream `README.md`; Forgejo issues/pull requests | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94` | README names the issue tracker and test entry points. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #25 | current issue record | hard-link and stale PAX source defect | component |
| PR #48 | head `25f6bcda2a807a8901b3ff3e34f5581d6f057877`; merge `4d2550eb6a4e0765aed9f16897b4c4a9a39f119e` | original hard-link/PAX candidate with stale symlink-scope expectation | superseded component |
| Issue #36 | current issue record | broad transform-semantics parent | canonical parent |
| Issue #51 | current issue record | first/global and `g`/`i` focused duplicate | component |
| PR #52 | head `928c81b4fe9816d8f151eb8388356fffc2362bc7`; closed unmerged | stacked composition experiment | superseded by #56/#68 |
| PR #56 | head `640f414cb18cf47b3e803856392c720414bea333`; merge `ff3c9458cee438d16f8d99ca9e2e9b843d3766fe` | replacement count, `g`/`i`, `&`, escapes | component |
| Issue #63 | current issue record | corrected default symlink scope | component/correction |
| PR #68 | head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`; merge `e7388243f3436ceda16f9d5be70d5423cc379b9d` | canonical integrated replacement, target-scope, hard-link, and PAX base | canonical foundation |
| Issue #98 | current issue record | numeric selectors | component |
| PR #102 | head `46f49d04639d6baf43243e5096175866c7e6a58e`; merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7` | incremental numeric occurrence patch | canonical increment |
| Issue #397 unit 15 | branch base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | upstream packaging and closeout | canonical packet |

Historical exact-head workflow receipts:

- PR #56: `30535166174`
- PR #68: `30536181358`
- PR #102: `30543327305` final; `30543032983` corrected code; `30542362599` initial differential
- PR #48: malformed-carrier run `30534545841`; repaired runs `30534925492`, `30534925524`, and final `30534974328`

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `tarfilter` | `_find_unescaped_delimiter`, `_unescape_delimiter` | delimiter-aware substitution parser | composed patch |
| `tarfilter` | `_sed_replacement` | GNU/sed whole-match and tested escapes | composed patch |
| `tarfilter` | `_sed_substitute` | numbered and global-after occurrence selection | composed patch |
| `tarfilter` | `TransformAction.__call__` | flags, selectors, scopes, compiled transform state | composed patch |
| `tarfilter` | strip block in `main()` | hard-link target stripping and stale PAX removal | composed patch |
| `tarfilter` | transform block in `main()` | selected name/link transformations and PAX invalidation | composed patch |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `scripts/run_matrix.py` | first/global, `&`, escaped delimiter | `s/a/b/` produces `b/b`; `g` rejected | match GNU tar |
| `scripts/run_matrix.py` | default and `S` scopes | link targets retain `prefix/target` | default `rsh`; `S` preserves symlink text |
| `scripts/run_matrix.py` | strip + 120-byte PAX leaf | stale prefixed path and hard-link target | regenerated path/linkpath and successful extraction |
| `scripts/run_matrix.py` | numeric selector matrix | PR #68 predecessor rejects selector | match GNU tar, including link-target counting |
| `scripts/run_matrix.py` | non-ASCII selector controls | unsupported | unsupported like GNU tar |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-15-tarfilter-transform-metadata`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS FORK`
- Retained patch: `patches/0001-tarfilter-transform-metadata.patch`
- Patch application command:

```sh
patch --fuzz=0 -p1 -d /path/to/mmdebstrap \
  -i upstream-packets/units/15-tarfilter-transform-metadata/patches/0001-tarfilter-transform-metadata.patch
```

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| transform expression parsing | token regex in `TransformAction` | delimiter-aware parser carrying flags, selectors, and scopes | composed diff and matrix |
| replacement selection | Python `re.sub()` defaults | `_sed_substitute()` | replacement/numeric matrix |
| member-name transform | member loop | same loop with scoped transform state | GNU tar differential |
| hard-link target transform | absent | same transform loop under `h/H` | GNU tar differential and extraction |
| symlink target transform | absent | same transform loop under `s/S` | default/`S` differential |
| hard-link strip target | absent | strip block | extraction and inode identity |
| PAX path/linkpath authority | stale input dictionary | removed on changed logical fields; writer regenerates | 120-byte PAX fixture |

## Overlap and current upstream state

Search date: 2026-08-01.

The public canonical repository currently shows `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`, with `tarfilter` last changed by commit prefix `87b9b385b3` on 2024-09-13. Source inspection shows the same parser and name-only transform loop as imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`. The visible open issue list contains six unrelated issues, and targeted public search found no active equivalent tarfilter transform carrier. This is an overlap search boundary, not proof that no older private or unindexed discussion exists.

## Files deliberately not changed

- `upstream/mmdebstrap/tarfilter` in Linux Fieldwork: imported source remains untouched.
- Unit 01 regex translator carriers: separate pattern-language ownership.
- Unit 16 hard-link dependency resolver: separate emitted-member dependency lifecycle.
- Unit 18 no-option passthrough.
- Unit 19 PAX uid/gid shift semantics.
- Units 20–22 normalization, parent metadata, and typeflag work.
- Broader `flags=`, expression lists, case conversion, locale/collation, and malformed-expression parity.
