# Start Here

Use this runbook whenever a person or agent is asked to add Linux learning, map a research direction, or investigate a Linux or Debian project through this repository.

Read [`FIELD_GUIDE.md`](FIELD_GUIDE.md) alongside this runbook for practical do, do-not, 🍩 donut, review, and investigation-selection lessons retained from prior work.

## In simple words

Choose the smallest useful record. Write a note for reusable understanding. Use the programme registry for a plausible formal direction. Give a lane its own directory when its bounded question and first probe are clear. Open an investigation when exact source work and repeatable evidence begin.

A reader should understand the question, consequence, and proposed answer before meeting the test matrix.

## 1. Check existing work

Search, in order:

1. [`programmes/registry.yml`](programmes/registry.yml) and the relevant programme `STATUS.md`;
2. [`targets/registry.yml`](targets/registry.yml) and any target map;
3. `research/rounds/` for prior landscape reasoning;
4. `notes/` for reusable explanations;
5. `investigations/` for active or retained evidence;
6. the relevant imported tree under `upstream/`.

Link related records instead of repeating them.

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

## 3. Explain it for a human reader

Near the top, add these reader-facing fields:

- `## TL;DR` — the current answer and next action in a few sentences;
- `## Explain like I'm five` — a concrete, low-jargon explanation;
- `## Why care` — the practical failure, risk, or opportunity.

Existing lightweight notes may keep the combined `## In simple words` heading.
For a defect, candidate, or surprising behavior, answer:

- What does the component do, and where does it sit?
- What exact input and action produce the wrong result?
- Who or what receives the consequence?
- What does source or history show about intent?
- What changes, why is that boundary appropriate, and what remains open?

Prefer a literal example such as `origin promises 100 bytes → sends 40 → candidate removes the temporary file` over a phrase such as “response handling is hardened.” Define specialized terms at first use.

Keep observed behavior, intent evidence, interpretation, design choice, and future work distinct.

## 4. Record the source boundary

For code or package work, record the project, requested revision, resolved commit or package version, local path, and import metadata path. Preserve upstream licenses and executable permissions.

For general system behavior, record the distribution, release, kernel, architecture, shell, privileges, container or virtual-machine context, and relevant tool versions.

Update or create a target map when one upstream project becomes recurrent across several lanes or investigations.

## 5. Run the smallest useful demonstration

Prefer a command or test that preserves the important behavior while remaining easy to repeat. Capture the exact command, expected distinguishing outcomes, actual result, and cleanup steps.

For a candidate change, compare baseline and candidate behavior under the same conditions. Use the donut checks in [`FIELD_GUIDE.md`](FIELD_GUIDE.md) to look for missing permission, path, metadata, lifecycle, compatibility, and evidence boundaries around the headline result.

Each important plain-language claim should map to a command, fixture, source line, or observed result.

## 6. State the evidence boundary

Say exactly what the work establishes and where the conclusion ends. Mention skipped test suites, untested platforms, privilege assumptions, mocked components, reduced fixtures, and environment-specific behavior.

When the distinction could be unclear, label a conclusion as demonstrated behavior, plausible consequence, design choice, or open question.

## 7. Decide the next step

Choose one:

- retain or expand a note;
- keep a possibility in the programme registry;
- promote a possibility into a formal lane directory;
- open or continue an investigation;
- keep a local candidate change;
- prepare an upstream packet after explicit authorization;
- close with a negative result.

For a merge or upstream decision, say what the reviewer is choosing and which exact evidence supports that choice.

## Upstream contact

Programme, lane, target, research, note, and investigation records grant no authority to contact maintainers. External issues, email, merge requests, patches, comments, and reviews require a deliberate decision.
