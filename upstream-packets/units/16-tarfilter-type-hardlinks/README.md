# Unit 16 — tarfilter type-excluded hard-link dependencies

State: `ACTIVE`  
Priority-zero issue: #397, unit 16  
Worker or variant: `ChatGPT final-name identity characterization`  
Linux Fieldwork branch: `upstream/unit-16-tarfilter-type-hardlinks`  
External contact authorized: `false`

## TL;DR

The executed baseline proves that member-local type exclusion can retain a hard link after removing its target. PR #248 adds focused rejection; PR #310 repairs archive finalization and duplicate-name state. The remaining defect is identity timing: dependency state and checks use pre-strip input names while the emitted archive uses rewritten member and hard-link target names.

This unit now retains a packet-local composition of the PR #310 predecessor on the canonical transform/strip carrier and an executable two-case discriminator from issue #335. The discriminator covers one valid final target that the predecessor rejects and one missing final target that the predecessor accepts.

## Accomplished behavior

The eventual candidate will decide hard-link availability in the same final-name domain used by emitted member names and emitted hard-link targets. It will preserve finalized output on rejection and preserve valid duplicate targets already emitted.

## Why care

A pre-rewrite dependency check has two product outcomes:

- status 1 for an archive whose rewritten hard link has a valid emitted target;
- status 0 for an emitted hard link whose rewritten target is absent, followed by GNU tar extraction failure.

## Scope

### Included

- target-before-link hard-link dependencies;
- type-excluded target occurrences;
- archive finalization before status 1;
- retained duplicate-name targets;
- `--strip-components` rewriting of member names and hard-link targets;
- final-name availability checks and GNU tar extraction controls.

### Excluded

- link-before-target buffering;
- arbitrary hard-link graphs;
- path-filter dependency policy;
- output rollback;
- package-pipeline impact;
- other extractors and platforms;
- privileged metadata;
- broad transform language compatibility owned by adjacent tarfilter units.

### Split boundary

Unit 15 owns general transform, target, and PAX metadata semantics. Unit 16 consumes that canonical carrier only where final rewritten names decide type-filter hard-link availability.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap `tarfilter` |
| Canonical repository | `NEEDS DESTINATION DECISION` |
| Intended base branch | `NEEDS DESTINATION DECISION` |
| Upstream base commit | imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | packet-local composition pending selected correction |
| Candidate head | current Linux Fieldwork branch head; exact value in `HANDOFF.md` |
| Linux Fieldwork branch | `upstream/unit-16-tarfilter-type-hardlinks` |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Imported/local source identity | `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Canonical transform patch | blob `1703984aa0c030e5131618a3541ee85bfd68ec65` |
| Predecessor composition | PR #310 head `32dfa36a6feb533bc1126a11ef33979e45b410ec` |
| Packet predecessor patch | `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` |
| Proposed destination | `NEEDS DESTINATION DECISION` |
| Delivery method | `NEEDS DESTINATION DECISION`; no external contact authorized |

## Canonical links

- Priority-zero unit: #397 unit 16
- Owning Linux Fieldwork issues: #243 and #335
- Internal draft PR: #399
- Executed baseline: PR #244, merge `29ac38765bbbe99ed62313da54e7e0022b8cb9c3`
- Initial rejection candidate: PR #248, head `f1b013832b5f3b073a9131de83ce89077771a7ea`
- Lifecycle and duplicate repair: PR #310, head `32dfa36a6feb533bc1126a11ef33979e45b410ec`
- Canonical transform/strip carrier: PR #68, merge `e7388243f3436ceda16f9d5be70d5423cc379b9d`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- PR #244 executed the original dangling-hard-link baseline.
- PR #310 defined finalized rejection and duplicate-target state repairs.
- Source review establishes that PR #310 checks hard-link identity before strip and transform rewriting.
- The packet contains an executable two-case test for both strip-induced failure directions.

### Pending exact execution

- exact-head Linux Fieldwork CI for PR #399;
- selected final-name state representation;
- candidate patch and rerun of inherited PR #248 and PR #310 matrices;
- complete current-main gate on the selected candidate.

### Compatibility boundary

The selected correction must preserve target-before-link streaming, finalized partial or empty archives on rejection, retained duplicate targets, transform scope behavior from PR #68, and existing path-filter semantics.

## Candidate organization

Current packet order:

1. canonical transform/strip carrier from PR #68;
2. `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch`;
3. `tests/test_tarfilter_type_excluded_final_name_identity.py` characterization;
4. pending final-name identity correction;
5. inherited and complete-gate reruns.

## Current disposition

`ACTIVE` — executable characterization and final-name correction selection remain.

## Next human decision

No human decision is required yet. Technical work should continue through exact execution and a bounded correction.

## Authority

Internal repository reads, branches, commits, tests, draft PRs, packet drafting, and issue checkpoints are authorized. External issue, pull request, merge request, mailing-list post, email, review, release, or package upload remains unauthorized. No external contact was made.
