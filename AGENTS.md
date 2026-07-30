# Linux Fieldwork agent contract

This file is the repository-wide working contract for people and agents doing Linux Fieldwork.

Read this file and [`START_HERE.md`](START_HERE.md) before changing code, opening an issue, adding a lane, or publishing a technical conclusion.

## Start with existing work

Before creating anything new:

1. Search open and closed issues and pull requests.
2. Search `programmes/`, `targets/`, `research/`, `notes/`, and `investigations/`.
3. Read the relevant imported source and nearby tests under `upstream/`.
4. Link the existing record instead of creating a duplicate.

Issue prose is orientation, not source evidence. Confirm claims against the exact code, test, workflow, or retained artifact.

## Source-first work

For code investigations and fixes:

- identify the exact source revision and file/function ownership;
- map the call path and adjacent tests before proposing a change;
- reproduce baseline behavior with an executable probe when practical;
- include a negative control that proves the probe fails when the claimed invariant is broken;
- keep observation, interpretation, and proposed policy separate;
- prefer a bounded candidate fix once a defect is confirmed and the repository authority allows local changes;
- do not stop at a report when a small local repair and regression test are feasible.

A green command is not evidence unless it ran against the exact reviewed head. Record the commit, command or workflow run, and relevant environment.

## Durable notes are part of the work

Every material code investigation must leave a reusable repository record.

Create or update a file under `notes/` when the work teaches a reusable Linux, Debian, shell, filesystem, process, packaging, permissions, or source-reading lesson. Link the note from the investigation, lane report, issue, or pull request.

If no reusable note is appropriate, state `Notes: not applicable` in the investigation or pull request and explain why. Silence is not a disposition.

Notes must distinguish stable lessons from target-specific observations and must name their version and environment limits.

## Self-review contract

Before asking for review, inspect the complete final diff and record a self-review that covers:

- source identity and exact head;
- whether the test actually asserts the written contract;
- failure-path and cleanup behavior;
- destructive path and privilege safety;
- signal, subprocess, descriptor, lock, mount, and temporary-path ownership where relevant;
- concurrent or repeated execution where relevant;
- compatibility and untested boundaries;
- stale comments, generated files, and retained artifacts;
- whether claims exceed executed evidence.

Run at least one negative control for a new regression harness. A test that only records output without asserting the expected result is incomplete.

## Peer-review contract

Review active peer work against code, not only prose.

A useful review:

- anchors the exact reviewed commit;
- reads the changed implementation and relevant existing code;
- checks that the test would fail for the old or deliberately broken behavior;
- checks cleanup and rerun behavior;
- separates product defects from harness, CI, formatting, and policy failures;
- gives concrete blocking findings with file and line context when possible;
- re-reviews after changes instead of leaving a stale verdict.

Do not approve a branch merely because CI is green. Do not block a product fix for an unrelated inherited CI defect without identifying the separation and, when practical, repairing the repository gate separately.

## Investigation completion contract

A material investigation is complete only when it has:

1. an existing-work and duplicate search;
2. exact source and environment identity;
3. a source and test map;
4. a baseline and distinguishing probe;
5. asserted results and at least one negative control where practical;
6. interpretation and evidence limits;
7. cleanup and rerun results;
8. a self-review;
9. a reusable note or an explicit `Notes: not applicable` rationale;
10. a concrete disposition: fix, retain, expand, stop, block, or prepare an authorized upstream packet.

## Safety and authority

- Guard every caller-controlled path before destructive operations such as `rm -rf`.
- Use disposable roots, containers, or virtual machines for privileged or destructive probes.
- Never commit credentials, private host data, raw personal logs, or unnecessary large artifacts.
- Imported upstream source remains attributed and license-preserving.
- No issue, email, merge request, patch submission, comment, review, or other upstream interaction is authorized unless a repository record explicitly grants it.
