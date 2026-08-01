# Unit 15 — mmdebstrap tarfilter transform metadata semantics

State: `ACTIVE`  
Priority-zero issue: #397, unit 15  
Worker or variant: `ChatGPT`  
Linux Fieldwork branch: `upstream/unit-15-tarfilter-transform-metadata`  
External contact authorized: `false`

## TL;DR

The canonical transform, target-scope, hard-link, PAX, and numeric-occurrence carriers are now materialized in the controlled fork `teamleaderleo/mmdebstrap` on branch `linux-fieldwork/unit-15-tarfilter-transform-metadata`. That branch starts at the exact canonical upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94` and ends at `505bf81079a3b76c7d56bffa8097c1b5a494898e`.

The fork contains the source candidate, an upstream-native test under `tests/`, and its `coverage.txt` registration. A clean local exact-source rerun makes the baseline fail at the first-replacement assertion and makes the candidate pass twice with no retained temporary directories. Full `coverage.py`, shellcheck, shfmt, package, and hosted gates remain incomplete.

## Accomplished behavior

The candidate parses the retained GNU tar substitution subset, applies first-only replacement unless `g` is present, supports `i`, whole-match `&`, escaped replacement characters, target scopes, and numeric occurrence selectors, and applies each transform consistently to selected member names and link targets. Component stripping repairs hard-link targets. Changed member and link names discard stale PAX `path` and `linkpath` fields so Python regenerates long metadata from the corrected values.

## Why care

The baseline can rename every match, reject valid numeric/global flags, leave hard-link and symlink references stale, preserve obsolete PAX names, and emit archives that fail extraction or contain paths different from the requested transform.

## Scope

### Included

- first-only and global replacement;
- case-insensitive matching;
- whole-match `&` and tested replacement escapes;
- `r/R`, `s/S`, and `h/H` target scopes with default `rsh`;
- numeric occurrence selectors, zero behavior, and last decimal-run selection;
- hard-link target repair for `--strip-components`;
- stale PAX `path` and `linkpath` removal/regeneration;
- GNU tar differential checks, extraction, inode identity, cleanup, and immediate rerun;
- upstream-native test file and `coverage.txt` registration in the controlled fork.

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

Start with one semantic source patch because parsing state, replacement count, target scopes, link rewriting, and PAX invalidation converge in `TransformAction` and the archive-member loop. The fork currently uses three commits only to keep source, native test, and test registration identities explicit. Reconsider a two-source-commit series only if final review demonstrates an independently mergeable parser/replacement boundary and link/PAX boundary without duplicate edits.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `teamleaderleo/mmdebstrap` |
| Controlled base branch | `linux-fieldwork/upstream-main-snapshot` at `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Candidate source branch | `linux-fieldwork/unit-15-tarfilter-transform-metadata` |
| Candidate branch head | `505bf81079a3b76c7d56bffa8097c1b5a494898e` |
| Source commit | `f7833615824ad99023c21a495840d10f64c6401a` |
| Native-test commit | `f7337a7d2f33d280c8e5b1576dd729f4d076c13a` |
| Coverage-registration commit | `505bf81079a3b76c7d56bffa8097c1b5a494898e` |
| Candidate source Git blob | `adb330efcc941bf5e646f195c245a3184e42f8e2` |
| Candidate source SHA-256 | `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Native-test Git blob | `bc9fb4e0593df5a37dee986308ebb62abc4b6839` |
| Native-test SHA-256 | `adab3852d9c8e719d64a24e1aed386d2eeccb45a43922f854d7458aa486f8caa` |
| Coverage Git blob | `fdac8b9f86b04e48af6476c32b649b1ed4bda95a` |
| Linux Fieldwork branch | `upstream/unit-15-tarfilter-transform-metadata` |
| Imported source identity | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; SHA-256 `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957` |
| Retained patch | `patches/0001-tarfilter-transform-metadata.patch`; SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c` |
| Native test receipt | `artifacts/FORK_NATIVE_TEST.txt`; SHA-256 `74d0ceff423a8bbc57bd5e8ae4dff3aa6ba1cfc105ebdbfd47d717f9e20f33a1` |
| Proposed destination | `josch/mmdebstrap` Forgejo pull request |
| Delivery method | controlled fork branch and pull request after explicit authorization |

## Fork history decision

The fork's legacy `master` is a separate Deepin packaging history and has no common ancestor with the canonical source snapshot. It remains untouched. Unit 15 is based on the existing controlled snapshot branch instead of force-replacing or rewriting `master`.

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

- The controlled base branch resolves exactly to current canonical upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94`.
- The fork candidate is three commits ahead and zero commits behind that base.
- The complete fork diff contains only `tarfilter`, `tests/tarfilter-transform-metadata`, and `coverage.txt`.
- The regenerated source patch applies with GNU patch 2.8 using `--fuzz=0` and produces the fork source bytes.
- The upstream-native test fails on the exact baseline with status `1` at `AssertionError: s/a/b/`.
- The same test passes twice on the candidate with status `0` and `tarfilter transform metadata: PASS`.
- Python compilation and POSIX shell syntax checks pass.
- The focused packet matrix remains green with identical JSON across repeated runs.
- The test rerun leaves zero matching temporary directories.

### Not yet demonstrated

- Execution through `coverage.py` in a complete checkout with its required mirror state.
- Shellcheck and shfmt: both tools were absent in the execution container.
- Relevant package/build tests or hosted CI.
- Other Python, GNU tar, distribution, and architecture combinations.
- Maintainer preference for one commit versus an ordered series.

### Compatibility boundary

The candidate preserves the existing Python regular-expression pattern dialect. Unit 01 owns GNU basic/extended regex translation. This unit claims the tested replacement, selector, scope, link, and PAX behavior only.

## Current disposition

`ACTIVE` — the controlled fork, exact candidate head, native regression, registration, direct baseline/candidate run, cleanup, and rerun are complete. The first incomplete gate is execution through the upstream `coverage.py` path in a complete checkout, followed by formatting and relevant package gates.

## Next human decision

No send decision exists. After the remaining gates and complete release-diff review, the packet can move to `READY FOR AUTHORIZATION` or name one concrete hold.

## Authority

Internal fork branches, tests, review, packet preparation, and issue checkpoints are authorized by #397. No issue, pull request, merge request, email, comment, or review was sent upstream.
