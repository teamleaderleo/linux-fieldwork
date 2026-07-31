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

## Use comment cards for live release work

A release desk needs one stable front-door issue whose body changes rarely. Put
the rules, links, and card format in that body. Put each live release unit in
one top-level comment on the desk.

The worker edits that unit's comment in place as the head, evidence, owner, or
disposition changes. Other workers update different comments, so routine
progress does not create competing edits to one large issue body.

Every live card should contain:

```text
STATUS CARD
Unit:
Owner:
State: DRAFTING | REPAIR | REVIEW 1 | REVIEW 2 | RELEASE CANDIDATE | HOLD
Exact head:
TL;DR:
Why care:
Owning issue or PR:
Tracked evidence:
Latest gate:
Remaining boundary:
Next action:
External-contact state:
```

The set of live card comments is the board. When a unit lands, is retired, or
moves out of the release desk, add its exact final receipt to the owning issue
or pull request and remove the live card. If the available GitHub client cannot
delete comments, replace the card with one short `ARCHIVED` line and its final
receipt link. Never keep a stale card as apparent live state.

Long commands, transcripts, fixtures, and interpretation remain in tracked
fieldwork records. A status card points to that evidence; it does not duplicate
it.

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

## Autonomous push work

An issue may declare an autonomous multi-helper push for a bounded batch. In that mode:

1. Every helper first reads [`README.md`](README.md), [`START_HERE.md`](START_HERE.md), this coordination guide, the push issue in full, and the live issues, pull requests, tracked records, and source revisions linked from its initial packet.
2. A helper letter, callsign, packet, or review pairing identifies an initial focus. It does not reserve work, limit review authority, or require another helper to finish first.
3. Begin useful work immediately. Do not wait for a coordinator, schedule, claim, reviewer assignment, or another packet when the next safe action is available.
4. Make bounded repository changes, execute focused gates, inspect the complete current diff, rerun after cleanup, and review the exact head being recommended. Careful self-review is valid for reversible internal work; higher-consequence work still deserves stronger independent review.
5. After completing the initial packet, inspect adjacent packets and the current open work. Continue with useful review, repair, evidence transfer, or closeout rather than ending solely because the initial packet is complete.
6. Keep ownership discoverable while allowing overlap. A short claim or transfer comment records who is acting; it never locks the work.
7. Record substantial completed work in at least two durable surfaces:
   - the owning issue or pull request, with the disposition, exact head, executed gates, caveats, authority state, and next human decision;
   - the relevant tracked fieldwork record, such as an investigation README or results file, scout report or artifact, reusable note, programme status, research selection record, or target map.
8. Link records instead of copying large reports between them. The tracked record carries commands, fixtures, results, interpretation, and evidence limits; the issue or pull request carries routing, review state, and the current decision.
9. Leave the repository sufficient for another person or agent to understand, reproduce, review, and continue the work even when the helper chat receives no follow-up message.

## Write while the work is still in progress

Do not wait for the end of a long investigation to create the first durable record. Chat narration is optional and lossy; the repository is the recovery source of truth.

Create or update a compact checkpoint before any step that is long-running, tool-heavy, likely to change scope, likely to produce a sensitive-looking result, or difficult to reconstruct from memory. Update it again whenever one of these facts changes:

- exact branch or head;
- bounded question;
- first observed distinguishing result;
- changed paths;
- completed gate or artifact identity;
- cleanup state;
- evidence boundary;
- next safe action;
- external-contact authority.

Write the checkpoint before deepening a surprising or “spicy” finding. Preserve the exact observation first; interpretation, candidate design, and broader consequence can follow. Never leave the only copy of a command, artifact ID, failing case, or next action inside a chat response that may not be delivered.

Prefer one live checkpoint on the owning issue or pull request and edit it in place instead of producing a stream of partial comments. Once commands, fixtures, or results become substantial, move them into the tracked investigation and leave the live checkpoint as a pointer.

Use this compact form:

```text
LIVE CHECKPOINT
Unit:
Owner:
Exact head:
Question:
Observed so far:
Changed paths:
Completed gates:
Cleanup state:
Evidence boundary:
Next safe action:
External-contact state:
```

A checkpoint is not a claim that work is complete. Mark unknown, queued, skipped, unreviewed, or not-yet-executed state explicitly. Do not include secrets, private credentials, unsafe operational detail, or speculative attribution merely to make the checkpoint feel complete.

## Recover from interrupted or blocked interaction

A chat response, connector call, local command, hosted job, or safety check can stop while repository work remains valid. Treat the interruption as a coordination event. It does not by itself establish a product defect, test result, or permission decision.

When this happens:

1. Stop adding speculative detail or repeated retries.
2. Write a concise factual checkpoint in a durable surface already owned by the work whenever repository writes remain available.
3. Include the work unit, exact branch and head, changed paths, completed gates, first incomplete step, failure owner, cleanup state, evidence boundary, authority state, and next safe action.
4. On resumption, reload [`README.md`](README.md), [`START_HERE.md`](START_HERE.md), this guide, [`FIELD_GUIDE.md`](FIELD_GUIDE.md), the owning issue or pull request, the tracked record, and the exact source. Reconstruct the state from commits, raw artifacts, logs, and receipts rather than chat narration.
5. Classify the interruption separately as product, fixture or harness, tool or connector, environment, hosted execution, or interaction and safety. Do not edit product code until the owner of the first incomplete or failing step is known.
6. For benign safety-sensitive work, prefer synthetic fixtures, disposable directories, fake destructive commands, no real credentials, no public targets, and no external contact. Describe the component, exact input and action, observed result, practical consequence, selected design, evidence limit, and next decision.
7. If a task genuinely requires higher-risk operational detail or crosses the declared authority boundary, stop, record `HOLD`, and request a specific human decision. Do not disguise, fragment, or rephrase prohibited work to force it through.

Use this compact checkpoint:

```text
INTERRUPTION CHECKPOINT
Unit:
Exact head:
Changed paths:
Completed gates:
First incomplete step:
Failure owner:
Cleanup state:
Evidence boundary:
Authority:
Resume with:
```

Safety checks and platform policies still apply. This protocol preserves bounded benign work; it is not a workaround for those checks.

## Notes stay lightweight

Use a note when the durable value is an explanation, command, workflow, source-reading lesson, or small demonstration. Notes do not need scout identities, formal review, promotion decisions, research metadata, or a full evidence packet.

Add ordinary links when they help the reader understand the subject or find a related record. Notes and other repository files do not create GitHub autolinked issue or pull-request references, so they do not need an automated backlink check.

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

Quiet coordination should not create accidental backlinks or notifications in third-party official repositories.

Apply backlink suppression to GitHub interaction text: issue and pull-request titles and bodies, comments, reviews, discussions, and intentional issue references in commit messages. In those surfaces, use:

```text
https://redirect.github.com/OWNER/REPOSITORY/issues/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/pull/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/discussions/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/commit/SHA
```

Do not use bare third-party shorthand such as `OWNER/REPO#123` in interaction prose. Direct links among controlled `teamleaderleo/*` repositories are fine.

Repository notes, reports, maps, and other tracked files may link directly to third-party GitHub work because GitHub does not create autolinked issue or pull-request references in repository files. Those files do not need an automated reference scanner.

Repository homepages, documentation sites, specifications, package registries, release pages, and ordinary web sources may be linked normally.

Use a direct third-party issue, pull-request, discussion, or commit link in interaction text only when it records an explicitly authorized upstream interaction.

This link rule does not itself authorize contact. Issues, email, merge requests, patches, comments, and reviews in an upstream project still require a deliberate decision.

## Working rule

> Coordinate only enough to preserve responsibility, evidence, recoverability, and upstream safety. Adapt the rest to the work.

When a rule repeatedly causes stalled work, duplicate effort, misleading ownership, or unnecessary review ceremony, improve the rule rather than teaching everyone to work around it.
