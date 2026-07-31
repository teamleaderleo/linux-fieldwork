# Upstream packet workspaces

This directory is the durable working surface for priority-zero issue #397.

The issue lists the contribution units and their order. A unit directory records the actual source work, tests, decisions, drafts, and handoff. Chat history is never the recovery source of truth.

## Start a unit from a new chat

A new chat can begin with:

```text
Work on Linux Fieldwork issue #397, unit N. Read the issue, upstream-packets/README.md, upstream-packets/INDEX.md, and every linked carrier. Create or continue the unit workspace and branch. Perform the next safe technical work, write observations and exact evidence into the workspace as you go, and leave a complete HANDOFF.md before stopping. Do not contact upstream without explicit authorization.
```

That instruction is enough. The worker is responsible for discovering the current carrier state rather than relying on an earlier chat.

## Canonical directory and branch names

Each claimed unit uses:

```text
upstream-packets/units/NN-short-slug/
upstream/unit-NN-short-slug
```

`NN` is the zero-padded number from issue #397. The Linux Fieldwork branch contains the packet, retained patch or series, fixtures, tests, and evidence updates.

When code must live in a controlled fork of the upstream project, record the fork and branch in the unit `README.md`. Prefer:

```text
linux-fieldwork/unit-NN-short-slug
```

Do not assume a fork exists. Record `NEEDS FORK` when one is required. For mailing-list or patch-based projects, retain the patch series and proposed cover letter in the packet; the final delivery method is a later explicit decision.

## Required unit bundle

Create a unit directory from `_template/` at the beginning of substantive work. Keep these files current:

- `README.md` — canonical state, exact identities, links, scope, and next decision;
- `SOURCE_MAP.md` — upstream code, tests, local carriers, patch files, and ownership map;
- `DEEP_DIVE.md` — observations, mechanism, approaches tried, rejected alternatives, compatibility analysis, and unresolved questions;
- `TESTS.md` — baseline/candidate matrix, exact commands, results, cleanup, rerun, and unexecuted gates;
- `UPSTREAM_ISSUE.md` — polished issue draft when an issue is useful;
- `UPSTREAM_PR.md` — polished pull-request or merge-request draft written as accomplished behavior;
- `DECISIONS.md` — dated decisions, supersession, split/hold/retire reasons, and reopen triggers;
- `HANDOFF.md` — exact current head, completed work, first incomplete step, and next safe action.

Use subdirectories only when useful:

```text
patches/       retained source patches or ordered series
fixtures/      minimal reproducers and generated test inputs
artifacts/     compact durable outputs, receipts, and hashes
scripts/       packet-specific reproducible helpers
```

Large hosted artifacts remain in their native store; record their IDs, digests, and interpretation instead of committing opaque bulk data.

## Write while working

The worker updates the packet immediately after any fact that would be painful to reconstruct:

- exact upstream base or candidate head changes;
- first distinguishing baseline or candidate result;
- patch application, rebase, conflict, or overlap result;
- changed code or test ownership;
- completed or skipped gate;
- cleanup or rerun state;
- compatibility concern or rejected design;
- disposition or next action.

Do not leave the only copy of a command, source identity, artifact ID, failure, or decision in chat. A report written only at the end is insufficient.

## Issue checkpoint

After creating or materially changing a unit, add or update a short comment on #397:

```text
UNIT CHECKPOINT
Unit: N
Worker or variant:
State: ACTIVE | READY FOR AUTHORIZATION | HOLD | RETIRED | SPLIT | SENT
Linux Fieldwork branch:
Packet README:
Exact upstream base:
Exact candidate head:
Latest distinguishing result:
First incomplete step:
External-contact state:
```

The issue comment routes readers. The packet carries the technical record.

## Definition of a useful branch

A branch is useful when another worker can check it out and answer all of these without the originating chat:

1. What exact upstream source is being changed?
2. What fails on the baseline?
3. What code and tests implement the candidate?
4. Which alternatives were tried or rejected, and why?
5. Which gates actually ran on the exact candidate head?
6. What survived cleanup and rerun?
7. What remains technically incomplete?
8. What draft would be sent upstream?
9. What explicit authorization is still required?

A branch that contains only prose, only a patch, or only green CI is not complete.

## Upstream destination and delivery method

Determine and record the current project contribution path, but do not contact it without authorization.

The packet should state one of:

- `GitHub fork and pull request`;
- `GitLab/Salsa fork and merge request`;
- `mailing-list patch series`;
- `Debian BTS patch or follow-up`;
- `downstream backport/package change`;
- `review/test contribution to an existing upstream carrier`;
- `NEEDS DESTINATION DECISION`.

For code-hosted projects, link the exact upstream repository, intended base branch, controlled fork when available, candidate branch, and compare/diff. For patch-based projects, retain numbered patches, the cover letter, base identity, application command, and test receipts.

## Disposition rules

Use the states from #397:

- `READY FOR AUTHORIZATION` means the technical scavenger hunt is over and only a human send/hold decision remains;
- `HOLD` names one specific blocker and the discriminator that could clear it;
- `SPLIT` names the successor units and preserves the shared evidence;
- `RETIRED` explains why no contribution should be sent;
- `SENT` records the exact public reference and submitted patch identity.

Internal Linux Fieldwork merge status does not equal upstream completion.

## Authority

This workflow authorizes internal repository reads, branches, commits, tests, reviews, rebases, packet drafting, and issue checkpoints. It does not authorize an external issue, pull request, merge request, mailing-list post, email, comment, review, release, or package upload. Debian bug #1135727 remains the only existing exception recorded by #397.
