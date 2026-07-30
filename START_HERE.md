# Start Here

Use this runbook whenever a person or agent is asked to add Linux learning, map a research direction, or investigate a Linux or Debian project through this repository.

Read [`AGENTS.md`](AGENTS.md) for the repository-wide source, review, notes, safety, and completion contract.

## In simple words

Choose the smallest useful record. Write a note for reusable understanding. Use the programme registry for a plausible formal direction. Give a lane its own directory when its bounded question and first probe are clear. Open an investigation when exact source work and repeatable evidence begin.

## 1. Check existing work

Search, in order:

1. open and closed repository issues and pull requests;
2. [`programmes/registry.yml`](programmes/registry.yml) and the relevant programme `STATUS.md`;
3. [`targets/registry.yml`](targets/registry.yml) and any target map;
4. `research/rounds/` for prior landscape reasoning;
5. `notes/` for reusable explanations;
6. `investigations/` for active or retained evidence;
7. the relevant imported tree and nearby tests under `upstream/`.

Link related records instead of repeating them. Record the duplicate search in a material investigation or pull request.

Issue and pull-request prose are orientation. Confirm technical claims against the exact source, tests, workflows, and retained artifacts.

## 2. Choose the work type

Use a **note** for:

- a Linux concept explained clearly;
- a command or workflow worth remembering;
- a small demonstration;
- a source-reading lesson;
- a distribution-specific detail with clear version limits.

Use a **registry lane** for a plausible formal question whose source target or first probe still needs mapping.

Use a **formal lane directory** when:

- the question is bounded;
- likely source targets are named;
- the environment and privilege requirements are known;
- one first probe has distinguishing outcomes;
- a meaningful promotion signal exists;
- a clean stop signal exists.

Use an **investigation** for:

- execution against an exact source or package revision;
- a suspected defect or surprising behavior;
- a candidate patch;
- a compatibility, performance, security, or lifecycle claim;
- work that may eventually be offered upstream.

Start notes and investigations from [`templates/`](templates/). Follow [`programmes/README.md`](programmes/README.md) for formal lane promotion.

## 3. Explain it simply

Near the top, add `## In simple words` and answer:

- What is this?
- Where does it sit in the system?
- What is being learned, tested, or changed?
- Why could someone care?
- What is the current answer or next step?

Keep established behavior separate from guesses and future work.

## 4. Record the source boundary

For code or package work, record the project, requested revision, resolved commit or package version, local path, and import metadata path. Preserve upstream licenses and executable permissions.

For general system behavior, record the distribution, release, kernel, architecture, shell, privileges, container or virtual-machine context, and relevant tool versions.

Update or create a target map when one upstream project becomes recurrent across several lanes or investigations.

## 5. Read the code and map the tests

Before designing a probe or patch:

- identify the owning function, caller, cleanup path, and adjacent tests;
- inspect the complete current implementation, not only the issue description;
- identify what existing test would catch the defect and what is currently missing;
- record the source and test map in the investigation or report.

## 6. Run the smallest useful demonstration

Prefer a command or test that preserves the important behavior while remaining easy to repeat. Capture the exact command, expected distinguishing outcomes, actual result, and cleanup steps.

For a candidate change, compare baseline and candidate behavior under the same conditions.

New regression harnesses must assert their contract. Add a negative control that deliberately breaks the claimed invariant and prove the harness becomes nonzero or otherwise fails clearly.

## 7. Review the complete work

Before asking for review:

- inspect the complete final diff;
- verify the exact head that executed;
- check failure paths, cleanup, reruns, destructive path safety, privileges, and concurrency where relevant;
- confirm that retained artifacts and prose match the executed result;
- record a self-review and any remaining limits.

Peer reviews must read the changed code and relevant existing code, anchor the reviewed commit, and re-review after required changes. Green CI alone is not approval.

## 8. Write down the reusable lesson

A material code investigation must create or update a related note under `notes/` when it produces a reusable Linux, Debian, shell, filesystem, packaging, permissions, process, or source-reading lesson.

Link the note from the investigation, report, issue, or pull request. When no reusable note is appropriate, write `Notes: not applicable` and explain why.

## 9. State the evidence boundary

Say exactly what the work establishes and where the conclusion ends. Mention skipped test suites, untested platforms, privilege assumptions, mocked components, reduced fixtures, and environment-specific behavior.

## 10. Decide the next step

Choose one:

- retain or expand a note;
- keep a possibility in the programme registry;
- promote a possibility into a formal lane directory;
- open or continue an investigation;
- implement or retain a bounded local candidate change;
- prepare an upstream packet after explicit authorization;
- close with a negative result;
- block with a named missing environment, decision, or dependency.

Do not stop at a report when a confirmed defect has a small feasible local fix and regression test.

## Upstream contact

Programme, lane, target, research, note, and investigation records grant no authority to contact maintainers. External issues, email, merge requests, patches, comments, and reviews require a deliberate decision.
