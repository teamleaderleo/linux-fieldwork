# Start Here

Use this runbook whenever a person or agent is asked to add Linux learning or investigate a Linux or Debian project through this repository.

## In simple words

Choose the smallest useful record. Write a note when the goal is to preserve an explanation, command, or lesson. Open an investigation when the goal is to establish a technical claim through repeatable evidence.

## 1. Check existing work

Search `notes/`, `investigations/`, and the relevant imported tree under `upstream/` before creating a new path. Link related records instead of repeating them.

## 2. Choose the work type

Use a **note** for:

- a Linux concept explained clearly;
- a command or workflow worth remembering;
- a small demonstration;
- a source-reading lesson;
- a distribution-specific detail with clear version limits.

Use an **investigation** for:

- a suspected defect or surprising behavior;
- a candidate patch;
- a compatibility, performance, security, or lifecycle question;
- a claim that depends on an exact source revision and environment;
- work that may eventually be offered upstream.

Start from [`templates/note.md`](templates/note.md) or [`templates/investigation.md`](templates/investigation.md).

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

## 5. Run the smallest useful demonstration

Prefer a command or test that preserves the important behavior while remaining easy to repeat. Capture the exact command, expected distinguishing outcomes, actual result, and cleanup steps.

For a candidate change, compare baseline and candidate behavior under the same conditions.

## 6. State the evidence boundary

Say exactly what the work establishes and where the conclusion ends. Mention skipped test suites, untested platforms, privilege assumptions, mocked components, reduced fixtures, and environment-specific behavior.

## 7. Decide the next step

Choose one:

- retain the note;
- expand the demonstration;
- open or continue an investigation;
- keep a local candidate change;
- prepare an upstream packet after explicit authorization;
- close with a negative result.

## Upstream contact

Research and local changes grant no authority to contact maintainers. Record the current authority state in each investigation. External issues, email, merge requests, patches, comments, and reviews require a deliberate decision.
