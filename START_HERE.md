# Start Here

Use this runbook whenever a person or agent is asked to add Linux learning, map a research direction, or investigate a Linux or Debian project through this repository.

Read [`FIELD_GUIDE.md`](FIELD_GUIDE.md) alongside this runbook for practical do, do-not, 🍩 donut, review, and investigation-selection lessons retained from prior work.

## In simple words

Choose the smallest useful record. Write a note for reusable understanding. Use the programme registry for a plausible formal direction. Give a lane its own directory when its bounded question and first probe are clear. Open an investigation when exact source work and repeatable evidence begin.

A reader should understand the defect or question before meeting the test matrix. Lead with the thing that goes wrong, who or what it can affect, and the proposed correction. Technical detail then proves the explanation.

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

Near the top, add `## In simple words`. For a defect, candidate, or surprising behavior, answer these questions before presenting the implementation details:

1. **What is this component?** Say where it sits in the larger workflow.
2. **What goes wrong?** Give one concrete input → action → bad result example.
3. **Why should someone care?** Name the affected bytes, files, processes, privileges, users, packages, or decisions.
4. **What happens if the behavior remains?** Describe the repeatable consequence instead of using a severity adjective alone.
5. **Was it intentional?** Separate evidence of an intended tradeoff from evidence of a shortcut, stale assumption, or accidental interaction.
6. **What is the proposed fix?** Describe the before/after behavior in ordinary language.
7. **Why this fix?** Explain the narrower and broader alternatives and the compatibility cost of the chosen boundary.
8. **What precedent applies?** Link relevant standards, manuals, prior bugs, release notes, or well-established design practice.
9. **What remains open?** State the evidence limit and next decision.

Use an analogy when it genuinely clarifies the authority or lifecycle involved. Pair the analogy with a literal example. A metaphor helps the reader; commands and observations carry the proof.

Prefer concrete language:

```text
origin promises 100 bytes → sends 40 → candidate deletes the temporary
```

instead of:

```text
response handling is hardened
```

Define specialized terms at first use. Expand phrases such as “post-commit failure,” “hop-by-hop header,” or “canonical path” into the actual event they describe.

Keep established behavior separate from interpretation, intent hypotheses, and future work.

## 4. Record the source boundary

For code or package work, record the project, requested revision, resolved commit or package version, local path, and import metadata path. Preserve upstream licenses and executable permissions.

For general system behavior, record the distribution, release, kernel, architecture, shell, privileges, container or virtual-machine context, and relevant tool versions.

Update or create a target map when one upstream project becomes recurrent across several lanes or investigations.

## 5. Run the smallest useful demonstration

Prefer a command or test that preserves the important behavior while remaining easy to repeat. Capture the exact command, expected distinguishing outcomes, actual result, and cleanup steps.

For a candidate change, compare baseline and candidate behavior under the same conditions. Use the donut checks in [`FIELD_GUIDE.md`](FIELD_GUIDE.md) to look for missing permission, path, metadata, lifecycle, compatibility, and evidence boundaries around the headline result.

The smallest useful demonstration should support the plain-language claim directly. A reader should be able to map each important sentence near the top to a command, fixture, source line, or observed result later in the record.

## 6. Cite precedent with care

Use primary sources when a claim depends on a protocol, API, command contract, package policy, or language behavior:

- RFCs and standards for protocol rules;
- official language or library documentation for runtime behavior;
- project manuals and source for command semantics;
- upstream issue, commit, or release history for project intent;
- established weakness catalogues for recurring defect classes.

Explain how the source applies. A link alone does not establish that the current case is identical.

Historical precedent can support three different conclusions; say which one applies:

- the behavior conflicts with a long-standing contract;
- the behavior reflects an old compatibility tradeoff that still has value;
- the behavior began as a reasonable shortcut whose assumptions no longer hold.

## 7. State the evidence boundary

Say exactly what the work establishes and where the conclusion ends. Mention skipped test suites, untested platforms, privilege assumptions, mocked components, reduced fixtures, and environment-specific behavior.

Distinguish:

- **demonstrated defect** — reproduced against the stated baseline;
- **plausible consequence** — follows from the demonstrated authority but was kept out of the safe fixture;
- **design judgment** — the proposed policy and its compatibility tradeoff;
- **open question** — requires another source, environment, or decision.

## 8. Decide the next step

Choose one:

- retain or expand a note;
- keep a possibility in the programme registry;
- promote a possibility into a formal lane directory;
- open or continue an investigation;
- keep a local candidate change;
- prepare an upstream packet after explicit authorization;
- close with a negative result.

For a merge or upstream decision, state the human choice in ordinary language. “READY FOR FINAL HUMAN CHECK” should be followed by what the reviewer is deciding and which exact evidence supports that decision.

## Upstream contact

Programme, lane, target, research, note, and investigation records grant no authority to contact maintainers. External issues, email, merge requests, patches, comments, and reviews require a deliberate decision.