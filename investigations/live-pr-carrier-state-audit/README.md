# Explicit terminal carrier-state audit

State: `first read-only probe implemented — exact-head gates pending`

Tracking: issue #323.

## TL;DR

Linux Fieldwork already says that exploration may keep parallel carriers while selection remains open and should leave one canonical carrier at closeout. The live pull-request list still retained several superseded components and one completed stopped investigation as open work.

This first probe introduces an opt-in exact declaration:

```text
Carrier state: active | component-evidence | superseded | stopped
Successor: #NUMBER | none
```

It flags open `superseded` and `stopped` pull requests, rejects malformed opted-in declarations, and ignores narrative uses of words such as “superseded history.” It changes no pull request automatically.

## Explain like I'm five

Old experiments can stay on the shelf. Only the current folder should still look ready to ship. Two exact labels let a reader and a small checker tell the difference.

## Why care

A stale open carrier can present an obsolete exact head, duplicate landing path, expired gate, or completed stop result as live work. Reviewers then spend time rediscovering selection that the repository already made.

## Instruction review result

The current project guidance already handles:

- exact heads and expiring evidence;
- parallel variants during open selection;
- one canonical carrier after selection;
- preservation of unique historical evidence;
- stop rules and reopening triggers;
- archival of stale live release cards.

The gap is the connection between that guidance and pull-request state. Existing `State`, `Disposition`, and narrative language vary by investigation, so closeout intent cannot be audited reliably.

The proposed fields are routing metadata. They do not replace technical state, review disposition, or evidence boundaries.

## First manual cleanup receipt

The instruction review immediately retired seven misleading live surfaces:

- component PRs #270, #282, and #304 after composition into PR #319;
- stale PRs #259 and #260 after merged successor PR #286;
- stopped PR #264 after its result and reopening triggers were complete;
- stale PR #285 after exact seven-blob transfer to PR #321.

Every closeout comment preserves the exact successor or stopped-head receipt.

## Probe contract

`tools/audit_pr_carrier_state.py` accepts a JSON list compatible with:

```sh
gh pr list --state open --limit 200 \
  --json number,title,body,url,state
```

Rules:

1. A PR with neither field remains outside the first adoption probe.
2. Once either field appears, exactly one of each field is required.
3. Values are case-insensitive; successor syntax is exact.
4. `active` requires `Successor: none`.
5. `component-evidence` requires an exact `#NUMBER` successor.
6. `superseded` requires an exact `#NUMBER` successor and is a finding while open.
7. `stopped` requires `Successor: none` and is a finding while open.
8. A PR cannot name itself as successor.
9. Closed PRs are outside the open-carrier inventory.
10. Narrative text never creates state.

The tool emits text or typed JSON and returns nonzero for terminal open carriers or malformed opted-in declarations.

## Negative and passing controls

The executable matrix covers:

- narrative “superseded” and “stopped” text with no exact fields;
- valid active and component-evidence declarations;
- open superseded and stopped findings;
- closed stopped control;
- missing, duplicate, invalid, and self-referential declarations;
- exact integer identity, rejecting JSON booleans;
- CLI JSON output and result status.

## Workflow boundary

The focused workflow uses read-only `contents` and `pull-requests` permissions. It runs the tests, downloads the current open-PR metadata through `gh`, records findings, and uploads the inventory even when findings make the audit step fail.

No close, comment, label, merge, branch, or external-project action is permitted.

## Evidence boundary

The probe establishes only declared routing state. It does not decide:

- technical correctness or merge readiness;
- whether workflow receipts are fresh;
- whether an undeclared successor exists;
- whether a component should already be composed;
- whether an active hold remains proportionate;
- whether an exact historical head should be deleted.

The fields remain opt-in during this first round. Missing fields do not fail the audit.

## Stop rule

Stop after exact parsing, false-positive controls, and a read-only live inventory pass review. Avoid automatic PR closure and broad natural-language inference.

## Reopening triggers

Expand only after repeated adopted-field evidence supports one additional deterministic check, such as:

- an active carrier names a successor that has already merged;
- component evidence remains open after the canonical composition lands;
- an exact-head gate receipt refers to a different current head.

Each expansion needs its own negative controls and authority boundary.

## Authority

Internal Linux Fieldwork metadata and synthetic fixtures only. External contact authorized: false.
