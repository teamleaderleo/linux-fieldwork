# Unit 16 — tarfilter type-excluded hard-link dependencies

State: `ACTIVE`  
Priority-zero issue: #397, unit 16  
Worker or variant: `ChatGPT final projected identity`  
Linux Fieldwork branch: `upstream/unit-16-tarfilter-type-hardlinks`  
Internal draft PR: #399  
External contact authorized: `false`

## TL;DR

The executed baseline shows that `--type-exclude=REGTYPE` can remove a data-bearing target, retain its payload-free hard link, return status 0, and emit an archive GNU tar cannot extract.

The selected candidate preserves PR #310's finalized rejection and retained-duplicate behavior, then moves type-owned dependency state into the final name domain produced by component stripping and applicable transform scopes. It accepts a hard link when a retained occurrence supplies the final target identity, rejects a genuine final target removed by the active type filter, keeps original input names in diagnostics, and leaves strip or transform failures that already exist without type exclusion outside this unit.

The complete clean matrix is green twice: run `30691015678` passed 449 tests at the duplicate-clean technical head, and run `30691660479` passed the same 449-test matrix at the current packet head. The next incomplete step is the exact current mmdebstrap `master` fetch and zero-fuzz rebase.

## Accomplished behavior

Type-excluded members are projected through the member-name strip and transform rules used by output. Retained hard-link targets are projected through hard-link strip and transform scope. Dependency checks compare those final identities while diagnostics retain original input member and target names.

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
- original-name diagnostics;
- exact zero-fuzz patch composition;
- cleanup and immediate-rerun controls.

### Excluded

- link-before-target buffering and arbitrary dependency graphs;
- path-filter dependency policy;
- rollback of members already emitted;
- intrinsic strip or transform reference failures present without type exclusion;
- general transform language and PAX metadata policy owned by unit 15;
- package-pipeline impact, other extractors, platforms, and privileged metadata.

### Split boundary

Unit 15 owns general rewrite operations, transform language, occurrence selection, target scopes, and PAX regeneration. Unit 16 consumes unit 15's clean prerequisite and adds only type-filter hard-link availability in final projected identity space.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap `tarfilter` / `mmtarfilter` |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master` |
| Current upstream base commit | `NEEDS CURRENT-MASTER FETCH AND REBASE` |
| Imported source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Controlled fork | `NEEDS FORK` |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Unit-15 prerequisite | `patches/0000-unit15-transform-metadata-prerequisite.patch` |
| Lifecycle and duplicate predecessor | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Selected correction | `patches/0002-use-rewritten-identities-for-type-hardlinks.patch` |
| Rejected policy evidence | `patches/rejected/0002-alias-projection-overattributes-strip-breaks.patch` |
| First selected-policy green head | `ec55994f0db12044f9c7ef9f843fe42aec7393e6` |
| Inherited matrix green head | `300b51056ded64a56ec3998bc639a57e9ea81125` |
| Duplicate-clean technical head | `7fe46662141fa39a3b18ae1baba29b2b39f6c330` |
| Prior current packet head | `c0926e099b98252e3d8f0c8463d53e9709e2a470` |
| Proposed destination | Debian mmdebstrap Salsa project |
| Delivery method | controlled Salsa fork and merge request; external authorization required |

Use the branch ref for the latest packet head. Documentation and receipt commits after `7fe4666...` do not alter candidate or unit-16 test bytes.

## Canonical records

- Priority-zero unit: #397 unit 16
- Owning Linux Fieldwork issues: #243 and #335
- Internal draft PR: #399
- Executed baseline: PR #244
- Lifecycle and duplicate repair: PR #310
- Unit-15 prerequisite packet: `../15-tarfilter-transform-metadata/`
- Source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and historical receipts: [`TESTS.md`](TESTS.md)
- Clean expanded receipts: [`artifacts/ci-clean-expanded-and-rerun.md`](artifacts/ci-clean-expanded-and-rerun.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Withheld upstream drafts: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md) and [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- PR #244 executed the original dangling-hard-link baseline.
- PR #310 established finalized rejection and retained-duplicate state.
- Run `30690541675` passed the four focused final-name cases and 442 complete repository tests.
- Run `30690583438` passed the inherited matrix and exposed duplicate test discovery.
- Run `30691015678`, job `91345628785`, passed the clean 449-test matrix in 166.207 seconds at technical head `7fe4666...`.
- Run `30691660479`, job `91347358106`, passed the same 449-test matrix in 151.721 seconds at packet head `c0926e0...`.
- Both clean runs validated 4 patch files and 11 hunks, compiled Python, passed all focused/inherited/transform unit-16 controls, and passed shell/help gates.
- The rejected alias candidate was mechanically green, but direct strip controls prove its policy attribution is wrong.
- The pre-receipt branch review found 14 added files and no imported-source modification.

### In progress

- exact current Salsa `master` commit and current `tarfilter` identity;
- comparison against imported blob `ad776167...`;
- zero-fuzz current-master rebase of patches 0000 through 0002;
- current-source matrix and complete diff review;
- controlled-fork creation only after authorization.

## Candidate organization

Ordered patch series:

1. `0000-unit15-transform-metadata-prerequisite.patch` — member/link rewrite, transform occurrence and scope semantics, and PAX regeneration;
2. `0001-compose-pr310-predecessor-on-transform-carrier.patch` — finalized type-dependency rejection and retained duplicate state;
3. `0002-use-rewritten-identities-for-type-hardlinks.patch` — final projected identity for type-excluded targets and retained hard-link targets.

Patch 0002 calls unit 15's `_sed_substitute` and replaces the input-identity state introduced by patch 0001, so the series remains ordered until current upstream overlap proves it can be reduced.

## Current disposition

`ACTIVE` — selected policy and complete internal matrix are green. Current-upstream identity, rebase, execution, and review remain.

## Next decision

No send decision is requested. After the current-master rebase and current-source matrix, the repository owner must decide whether to authorize creating or using a controlled Salsa fork and opening a merge request.

## Authority

Internal repository reads, branches, commits, tests, public-source inspection, packet drafting, and issue checkpoints are authorized. External issue, merge request, mailing-list post, email, review, release, or package upload remains unauthorized. No external contact was made.
