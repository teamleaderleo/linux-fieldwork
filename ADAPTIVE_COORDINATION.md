# Adaptive Coordination

## In simple words

Linux Fieldwork should coordinate people and agents without turning research into a rigid workflow. Keep enough structure to prevent duplicated work, unclear responsibility, lost evidence, and accidental upstream interaction. Let the actual investigation change shape when the source and experiments reveal a better boundary.

The normal progression remains:

```text
note -> registry possibility -> formal lane -> exact investigation
```

Not every piece of work must pass through every stage.

## The minimum durable facts

Substantial work should make these facts discoverable:

- the bounded question or intended outcome;
- one current owner or worker identity;
- the relevant lane, issue, branch, source revision, or package version;
- what evidence exists and where it stops;
- the next useful action;
- whether upstream contact is authorized.

Do not add ceremony that does not protect one of those facts.

## Use issues as dispatch cards

An issue should point someone toward useful work, not dictate every command. A small assignment can contain:

```text
Question:
Why this is worth checking:
Useful starting points:
Known boundaries:
Owner:
```

Use issue comments for short checkpoints, blockers, transfers, review requests, and next actions. Put commands, fixtures, source maps, results, interpretation, and evidence limits in the repository or a coherent pull request.

Detailed instructions are appropriate when a test method, safety condition, or exact compatibility boundary must be preserved. They are not the default.

## Identity and ownership

Humans may use their GitHub identity. Agents and temporary workers may use a short stable callsign such as `LF-R01` for attribution during active work.

The identity tells reviewers who produced or reviewed evidence. It does not create a permanent role, exclusive lane ownership, competence claim, or authority grant.

Keep one current owner for a coherent piece of work. That owner may:

- change methods;
- split independent findings into focused investigations;
- ask for specialist help;
- transfer the work;
- stop after a sound negative result;
- continue into a candidate fix when the evidence supports it.

Record a meaningful scope change or transfer. Do not force a useful investigation to remain inside an obsolete initial assignment.

## Notes stay lightweight

Use a note when the durable value is an explanation, command, workflow, source-reading lesson, or small demonstration. Notes do not need scout identities, formal review, promotion decisions, research metadata, or a full evidence packet.

Add ordinary links when they help the reader understand the subject or find a related local record. The external-GitHub rule below concerns cross-reference backlinks to third-party projects; it is not a ban on useful links between Linux Fieldwork notes.

## Formal lanes give direction, not scripts

A formal lane should define a bounded question, likely targets, a useful first probe, an evidence boundary, and signals for promotion or stopping. It should leave room for the worker to choose the best source reading, fixture, tracing method, or comparison.

A lane may produce:

- a focused investigation;
- several independent findings;
- a reusable fixture or compatibility map;
- a candidate patch;
- a retained negative result;
- a better follow-up question;
- a reason to stop.

All are valid outcomes when the evidence is durable.

## Review according to consequence

Do not require fixed reviewer rings.

Choose a reviewer when the work is ready, based on relevant source knowledge, independence from the candidate, security or destructive risk, overlap with other investigations, and the ability to challenge the evidence.

- Tiny probes and clear negative results may receive light review or coordinator acceptance.
- Bounded reversible repository work may use careful self-review.
- Security findings, broad claims, destructive operations, merge candidates, and upstream packets deserve stronger independent or specialist review.

Review the exact evidence and current head, not merely the prose or the original assignment format.

## Let work branch naturally

Broad reconnaissance is useful when it creates concrete next branches. Once a specific behavior, failure, compatibility boundary, or candidate change appears, prefer a focused investigation over extending one giant scout report indefinitely.

Keep the broad report as orientation. Link the focused work from it. Preserve passing cases and failed hypotheses because they prevent future duplicate work.

## External GitHub backlinks

Quiet research must not create accidental backlinks or notifications in third-party official repositories.

For third-party GitHub issues, pull requests, discussions, and commits, use backlink-suppressing references:

```text
https://redirect.github.com/OWNER/REPOSITORY/issues/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/pull/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/discussions/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/commit/SHA
```

Do not use bare third-party shorthand such as `OWNER/REPO#123` in prose. Direct links among controlled `teamleaderleo/*` repositories are fine. Repository homepages, documentation sites, specifications, package registries, and release pages may be linked normally.

Use a direct third-party issue, pull-request, discussion, or commit link only when it records an explicitly authorized upstream interaction.

This link rule does not itself authorize contact. Issues, email, merge requests, patches, comments, and reviews in an upstream project still require a deliberate decision.

## Working rule

> Coordinate only enough to preserve responsibility, evidence, recoverability, and upstream safety. Adapt the rest to the work.

When a rule repeatedly causes stalled work, duplicate effort, misleading ownership, or unnecessary review ceremony, improve the rule rather than teaching everyone to work around it.
