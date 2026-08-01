# Unit 21 — tarfilter parent metadata for nested includes

State: `ACTIVE`  
Priority-zero issue: #397, unit 21  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-21-tarfilter-parent-metadata`  
External contact authorized: `false`

## TL;DR

Current mmdebstrap `tarfilter` drops explicit parent directory and symlink entries when an exclude-all rule is followed by a nested include. The retained candidate stores the original glob beside the compiled matcher and uses component-bounded parent/descendant checks. The exact current `tarfilter` blob fails the focused regression; the patched exact source passes five cases and preserves parent metadata. A source-level dpkg comparison now records the deliberate compatibility boundary. Full repository application and upstream-native gates remain.

## Accomplished behavior

Nested path includes retained explicit directory and symlink parents that can lead to an included descendant. Retained entries preserved archive mode, uid, gid, mtime, link target, and PAX metadata. Exact includes, wildcarded includes, character classes, component-boundary controls, and symlink parents received focused coverage.

## Why care

Extraction tools auto-create omitted parents with default metadata. In the exact reproducer, `usr/` changed from mode `0700` to `0755` and `usr/bin/` changed from `0711` to `0755`; their ownership, timestamps, and PAX metadata also disappeared from the filtered archive.

## Scope

### Included

- original path-glob retention in `PathFilterAction`;
- conservative parent/descendant relation from the original glob's literal prefix;
- component-boundary protection for `/usr` and `/usr2`;
- directory and symlink parent metadata regression;
- exact dpkg source-model comparison;
- `coverage.txt` registration.

### Excluded

- dotfile normalization, owned by unit 20;
- regular-file type aliases, owned by unit 22;
- transform/PAX semantics and hard-link dependencies, owned by units 15 and 16;
- any external issue, pull request, comment, review, or email.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `josch/mmdebstrap` on Muffin Forgejo |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current `tarfilter` Git blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Last `tarfilter` commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Patched `tarfilter` Git blob | `a7bdcb73e574aa1720b319b8531f65d10fbd2446` |
| Candidate test Git blob | `9212cb89dfcb954d84d2f7f8e6557755d59e1986` |
| dpkg reference file | `guillemj/dpkg main:src/main/filters.c@4fc1600a5717726faddc2fb556730f217e7f22a2` |
| Linux Fieldwork branch | `upstream/unit-21-tarfilter-parent-metadata` |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Patch | `patches/0001-tarfilter-retain-parent-metadata.patch` |
| Patch SHA-256 | `8bdd156eb375114c3f3be80c4433a06f6ac8a6d8e189023a02d39774d80c2f74` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; `NEEDS FORK` |

## Canonical links

- Priority-zero unit: #397 unit 21
- Owning Linux Fieldwork issue: #39
- Canonical Linux Fieldwork PR or composition: none
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- exact current source blob `ad776…` fails the focused test at the exact-include case and emits only `usr/bin/tool`;
- candidate source blob `a7bd…` passes exact, wildcard, character-class, component-boundary, and symlink-parent cases;
- directory metadata survives: `usr` mode `0700`, uid/gid `11/21`, mtime `1700000001`, PAX marker `usr-parent`; `usr/bin` mode `0711`, uid/gid `12/22`, mtime `1700000002`, PAX marker `bin-parent`;
- symlink metadata survives: link target `usr/bin`, mode `0777`, uid/gid `18/28`, mtime `1700000008`, and PAX marker `symlink-parent`;
- `python3 -m py_compile tarfilter`, `sh -n tests/tarfilter-parent-metadata`, focused execution, and `git diff --check` pass on the patched exact source;
- dpkg comparison: wildcard conservatism is preserved, exact ancestry is added, and plain-prefix `/usr`→`/usr2` aliases are rejected;
- active upstream issue and pull-request listings expose no equivalent parent-metadata work as of 2026-08-01.

### Pending demonstration

- application of the complete three-file patch to a full canonical checkout at `77ec…`;
- `CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata`;
- Black and broader repository gates on one exact candidate head;
- complete upstream diff review and final overlap recheck.

### Compatibility boundary

Ordinary last-match-wins filtering continues through the compiled regex. The special directory/symlink retention keeps dpkg's conservative wildcard policy, adds the exact-ancestor direction missing from dpkg's current one-direction comparison, and uses component separators to reject lexical sibling aliases. The candidate claims compatible intent, not exact predicate parity.

## Candidate organization

One patch forms the review unit:

1. `tarfilter: retain parent metadata for nested path includes`

Source and regression belong together because the test directly constrains the changed tuple and parent-retention predicate.

## Current disposition

`ACTIVE` — exact full-checkout application and upstream-native focused execution remain.

## Next human decision

A controlled fork or full canonical checkout becomes useful for final candidate validation. External publication still requires a separate explicit authorization.

## Authority

Internal reads, branches, commits, local execution, patch drafting, review, and issue checkpoints are authorized. External contact remains unauthorized; none occurred.
