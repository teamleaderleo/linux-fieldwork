# Unit 21 — tarfilter parent metadata for nested includes

State: `ACTIVE`  
Priority-zero issue: #397, unit 21  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-21-tarfilter-parent-metadata`  
External contact authorized: `false`

## TL;DR

Current `tarfilter` drops explicit parent directory entries when an exclude-all rule is followed by a nested include. A retained patch now stores the original glob, tests descendant relationships on pathname-component boundaries, and adds a focused metadata regression. The local matrix distinguishes the current algorithm from the candidate. A controlled upstream fork and a run against an exact upstream checkout remain.

## Accomplished behavior

Nested path includes retained explicit directory and symlink parents whose paths can lead to an included descendant. Retained entries preserved archive mode, uid, gid, mtime, and PAX metadata. Exact includes, wildcarded includes, character classes, and component-boundary negatives received focused coverage.

## Why care

Extraction tools auto-create omitted parent directories with default metadata. The reproduced exact-include case changed `usr/` from mode `0700` to `0755` and `usr/bin/` from `0711` to `0755`; the output archive also lost their uid, gid, mtime, and PAX headers.

## Scope

### Included

- original glob retention in `PathFilterAction`;
- conservative parent/descendant relation using the original glob's literal prefix;
- component-boundary protection for names such as `/usr` and `/usr2`;
- focused archive metadata regression and coverage registration.

### Excluded

- dotfile normalization, owned by unit 20;
- regular-file type aliases, owned by unit 22;
- broader tar transformation and hard-link semantics, owned by units 15 and 16;
- external issue, fork, pull request, or maintainer contact.

### Split boundary

This unit changes only path-include parent retention. It leaves normalization, type classification, transformation, hard links, and unrelated PAX/idshift behavior untouched.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `josch/mmdebstrap` on Muffin Forgejo |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` (repository page head observed 2026-07-31) |
| Last tarfilter-changing commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | retained patch only; no upstream branch |
| Linux Fieldwork branch | `upstream/unit-21-tarfilter-parent-metadata` |
| Linux Fieldwork head | updated in `HANDOFF.md` |
| Imported/local source identity | canonical 303-line `tarfilter`; GitHub mirror blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patch or series path | `patches/0001-tarfilter-retain-parent-metadata.patch` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; `NEEDS FORK` |

## Canonical links

- Priority-zero unit: #397 unit 21
- Owning Linux Fieldwork issue: #39
- Canonical Linux Fieldwork PR or composition: none
- Predecessor issues and PRs: none beyond #39
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- the current translated-regex prefix calculation yields no useful descendant relation for `/usr/bin/tool`;
- baseline output contains only `usr/bin/tool`;
- GNU tar 1.35 extraction creates omitted parents as `0755`;
- the candidate archive retains `usr` mode `0700` and `usr/bin` mode `0711`, plus uid, gid, mtime, and PAX markers;
- exact, wildcard, character-class, component-boundary, unrelated-path, and leading-wildcard relation cases pass in the retained local matrix;
- the retained patch applies to an exact-context synthetic fixture, its Python hunk compiles, and its shell test parses;
- the proposed upstream test passes against a focused candidate implementation.

### Not yet demonstrated

- patch application to an exact checkout of canonical upstream head;
- execution of the new test through `coverage.py` on the full upstream candidate;
- full mmdebstrap formatting, lint, coverage, package, and integration gates;
- maintainer acceptance of conservative over-inclusion behavior.

### Compatibility boundary

The candidate keeps the existing last-match-wins file decision. Its special directory/symlink retention remains conservative, matching dpkg's documented preference for retaining extra parents to avoid unpack failures. Component boundaries prevent `/usr` from being treated as an ancestor of `/usr2`.

## Candidate organization

One retained patch forms a single review unit:

1. `tarfilter: retain parent metadata for nested path includes`

Source and regression belong together because the test directly exercises the changed path-filter tuple and parent-retention predicate.

## Current disposition

`ACTIVE` — a controlled fork or exact canonical checkout is required to apply the retained patch and run upstream-native gates.

## Next human decision

Authorize creation or use of a controlled mmdebstrap fork when ready for exact-candidate validation. This does not authorize upstream contact or submission.

## Authority

Internal repository reads, branch creation, packet commits, local reproduction, patch drafting, and issue checkpoints are authorized. External contact remains unauthorized, and none occurred.
