# Unit 15 — mmdebstrap tarfilter transform metadata semantics

State: `ACTIVE`  
Priority-zero issue: #397, unit 15  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-15-tarfilter-transform-metadata`  
External contact authorized: `false`

## TL;DR

The canonical Linux Fieldwork transform, target-scope, hard-link, PAX, and numeric-occurrence carriers were composed into one clean patch against the exact current upstream `tarfilter` source. The composed candidate passes a baseline/candidate differential matrix against GNU tar 1.35 and applies with GNU `patch --fuzz=0`. Upstream-native repository gates and a controlled upstream fork/branch remain incomplete.

## Accomplished behavior

The candidate parses the retained GNU tar substitution subset, applies first-only replacement unless `g` is present, supports `i`, whole-match `&`, escaped replacement characters, target scopes, and numeric occurrence selectors, and applies each transform consistently to selected member names and link targets. Component stripping repairs hard-link targets. Changed member and link names discard stale PAX `path` and `linkpath` fields so Python regenerates long metadata from the corrected values.

## Why care

The baseline can silently rename every match, reject valid numeric/global flags, leave hard-link and symlink references stale, preserve obsolete PAX names, and emit archives that fail extraction or contain paths different from the requested transform.

## Scope

### Included

- first-only and global replacement;
- case-insensitive matching;
- whole-match `&` and tested replacement escapes;
- `r/R`, `s/S`, and `h/H` target scopes with default `rsh`;
- numeric occurrence selectors, zero behavior, and last decimal-run selection;
- hard-link target repair for `--strip-components`;
- stale PAX `path` and `linkpath` removal/regeneration;
- GNU tar differential checks, extraction, inode identity, cleanup, and immediate rerun.

### Excluded

- basic-versus-extended regex translation and broader GNU regex grammar: unit 01;
- type-excluded hard-link dependency resolution: unit 16;
- no-option byte preservation: unit 18;
- shifted PAX uid/gid: unit 19;
- leading-dot normalization and parent metadata: units 20 and 21;
- regular typeflag `0`: unit 22;
- persistent `flags=`, expression lists, and case-conversion grammar;
- upstream publication.

### Split boundary

Start with one semantic patch because parsing state, replacement count, target scopes, link rewriting, and PAX invalidation converge in `TransformAction` and the single archive-member loop. Reconsider a two-commit ordered series only after upstream-native review demonstrates an independently reviewable parser/replacement commit and a link/PAX commit without duplicate parser or loop edits.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | local composed source SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Linux Fieldwork branch | `upstream/unit-15-tarfilter-transform-metadata` |
| Linux Fieldwork base head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; SHA-256 `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957` |
| Patch or series path | `patches/0001-tarfilter-transform-metadata.patch` |
| Proposed destination | `josch/mmdebstrap` Forgejo pull request |
| Delivery method | controlled fork branch and pull request; `NEEDS FORK` |

## Canonical links

- Priority-zero unit: #397 unit 15
- Owning Linux Fieldwork parent: #36
- Canonical composition: PR #68 plus incremental PR #102
- Component and predecessor carriers: #25, #51, #63, #98; PRs #48, #52, #56, #68, #102
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Current upstream `main` still points to a `tarfilter` whose relevant implementation matches imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.
- The exact PR #68 patch blob `1703984aa0c030e5131618a3541ee85bfd68ec65` and PR #102 patch blob `81828a468854e7ec9ef4cda9626b9c57314afba3` compose with `git apply --check`.
- A regenerated one-file patch applies with GNU patch 2.8 using `--fuzz=0` and produces the tested candidate byte-for-byte.
- The focused matrix passes four times with identical JSON output on Python 3.13.5 and GNU tar 1.35.

### Not yet demonstrated

- Upstream repository test-suite integration.
- A complete review in a current upstream checkout rather than the exact source-file materialization.
- Formatting or project-specific lint expectations.
- Controlled fork, candidate commit, and public destination branch.
- Maintainer preference for one commit versus an ordered two-commit series.

### Compatibility boundary

The candidate preserves the existing Python regular-expression pattern dialect. Unit 01 owns GNU basic/extended regex translation. This unit claims the tested replacement, selector, scope, link, and PAX behavior only.

## Candidate organization

1. `tarfilter: keep transform names and metadata consistent`
   - one clean source patch generated from exact baseline to composed candidate;
   - focused upstream test conversion remains the next code task.
2. A later split into parser/replacement and link/PAX commits is permitted only when the complete upstream diff supports it without overlapping source edits.

## Current disposition

`ACTIVE` — focused source composition and differential proof are complete; upstream-native integration and the controlled candidate branch remain.

## Next human decision

No send decision yet. The next repository-owner decision arrives after upstream-native tests and complete-diff review establish the final one-commit or ordered-series form.

## Authority

Internal rebasing, testing, review, packet preparation, and branch work are authorized by #397. External contact remains unauthorized, and none occurred.
