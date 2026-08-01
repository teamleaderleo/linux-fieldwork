# Unit 16 — tarfilter type-excluded hard-link dependencies

State: `ACTIVE`  
Priority-zero issue: #397, unit 16  
Worker or variant: `ChatGPT final projected identity`  
Linux Fieldwork branch: `upstream/unit-16-tarfilter-type-hardlinks`  
External contact authorized: `false`

## TL;DR

The executed baseline shows that `--type-exclude=REGTYPE` can remove a data-bearing target, retain its payload-free hard link, return status 0, and emit an archive GNU tar cannot extract. The selected candidate preserves PR #310's finalized rejection and duplicate-target repair, then moves dependency state into the final name domain produced by component stripping and applicable transform scopes.

The candidate accepts a hard link when a retained occurrence supplies its final target identity, rejects a genuine final target removed by the active type filter, and leaves pre-existing strip or transform reference failures with unit 15. Exact selected-policy CI run `30690541675` passed 442 tests. Inherited run `30690583438` passed 450 tests before duplicate-discovery cleanup; the clean expanded rerun is run `30691015678`.

## Accomplished behavior

Type-excluded members are projected through the same member-name strip and transform rules used by output. Retained hard-link targets are projected through hard-link strip and transform scope. Dependency checks compare those final identities while diagnostics retain the original input member and target names.

A known removed dependency stops before the broken hard-link member is written. The streaming tar context closes before status 1, leaving a finalized partial or empty archive. Earlier retained duplicate targets remain available after a later excluded occurrence with the same final identity.

## Why care

Input-name dependency state can reject a valid rewritten hard link. Alias-based state can also blame type exclusion for a broken reference already created by stripping or transform scope. Final projected identity assigns the failure to the operation that removed the actual emitted target.

## Scope

### Included

- target-before-link hard-link dependencies;
- type-excluded target occurrences;
- finalized output before status 1;
- retained duplicate targets and output-name collisions;
- component stripping of member names and hard-link targets;
- transform member and hard-link target scopes;
- GNU-equivalent leading archive-root prefixes;
- original-name diagnostics and exact zero-fuzz patch composition.

### Excluded

- link-before-target buffering and arbitrary dependency graphs;
- path-filter dependency policy;
- rollback of members already emitted;
- intrinsic strip or transform reference failures present without type exclusion;
- general transform language and PAX metadata policy owned by unit 15;
- package-pipeline impact, other extractors, platforms, and privileged metadata.

### Split boundary

Unit 15 owns the general rewrite operation, transform language, occurrence selection, target scopes, and PAX regeneration. Unit 16 consumes unit 15's clean prerequisite and adds only type-filter hard-link availability in final projected identity space.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap `tarfilter` / `mmtarfilter` |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master` |
| Current upstream base commit | `NEEDS CURRENT-MASTER FETCH AND REBASE` |
| Imported source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Controlled fork | `NEEDS FORK` |
| Linux Fieldwork branch | `upstream/unit-16-tarfilter-type-hardlinks` |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Unit-15 prerequisite | `patches/0000-unit15-transform-metadata-prerequisite.patch` |
| Lifecycle and duplicate predecessor | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Selected correction | `patches/0002-use-rewritten-identities-for-type-hardlinks.patch` |
| Rejected policy evidence | `patches/rejected/0002-alias-projection-overattributes-strip-breaks.patch` |
| First selected-policy green head | `ec55994f0db12044f9c7ef9f843fe42aec7393e6` |
| Expanded matrix head | `371802ab8728f149ddbac5a959e83ca8d0edef2d` |
| Duplicate-cleanup head | `7fe46662141fa39a3b18ae1baba29b2b39f6c330` |
| Proposed destination | Debian mmdebstrap Salsa project |
| Delivery method | GitLab/Salsa fork and merge request; `NEEDS FORK`; external authorization required |

## Canonical links

- Priority-zero unit: #397 unit 16
- Owning Linux Fieldwork issues: #243 and #335
- Internal draft PR: #399
- Executed baseline: PR #244, merge `29ac38765bbbe99ed62313da54e7e0022b8cb9c3`
- Initial rejection candidate: PR #248, head `f1b013832b5f3b073a9131de83ce89077771a7ea`
- Lifecycle and duplicate repair: PR #310, head `32dfa36a6feb533bc1126a11ef33979e45b410ec`
- Unit-15 prerequisite packet: `../15-tarfilter-transform-metadata/`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream merge-request draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- PR #244 executed the original dangling-hard-link baseline.
- PR #310 established finalized rejection and duplicate-target state.
- The selected final-only policy passed run `30690541675`: 442 tests, patch validation, compilation, shell syntax, and command-help gates.
- The inherited matrix passed run `30690583438`: 450 tests, including prefix equivalence, independent filters and immediate rerun, first-peer stopping, and retained duplicate targets.
- The rejected alias candidate passed a full gate in run `30690434953`; the direct strip control proves its policy attribution is wrong.

### In progress

- clean expanded matrix after duplicate-discovery repair: run `30691015678`;
- exact current Salsa `master` fetch and zero-fuzz rebase;
- controlled-fork creation and final submission identity;
- complete final diff review and unchanged-head rerun.

### Compatibility boundary

The candidate preserves target-before-link streaming, path-filter behavior, finalized failure output, original diagnostics, unit-15 transform/PAX semantics, retained duplicate targets, independent type filters, and the existing boundary for archives already invalid without type exclusion.

## Candidate organization

Ordered patch series:

1. `0000-unit15-transform-metadata-prerequisite.patch` — member/link rewrite, transform occurrence and scope semantics, and PAX regeneration;
2. `0001-compose-pr310-predecessor-on-transform-carrier.patch` — finalized type-dependency rejection and retained duplicate state;
3. `0002-use-rewritten-identities-for-type-hardlinks.patch` — final projected identity for type-excluded targets and retained hard-link targets.

The series remains ordered because patch 0002 calls unit 15's `_sed_substitute` and replaces the input-identity state introduced by patch 0001.

## Current disposition

`ACTIVE` — the selected candidate is internally green on focused and inherited gates. Clean expanded rerun, current upstream rebase, controlled fork, and final complete review remain.

## Next human decision

No send decision is requested yet. After current-master rebase and clean expanded rerun, the repository owner must decide whether to authorize creating or using a controlled Salsa fork and opening a merge request.

## Authority

Internal repository reads, branches, commits, tests, public-source inspection, packet drafting, and issue checkpoints are authorized. External issue, merge request, mailing-list post, email, review, release, or package upload remains unauthorized. No external contact was made.
