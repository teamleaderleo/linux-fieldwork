# Adaptive Coordination

## In simple words

Linux Fieldwork should coordinate people and agents without turning research into a rigid workflow. Keep enough structure to make parallel work legible, preserve evidence, and prevent accidental upstream interaction. Duplicate or competing work is an acceptable cost when it produces faster learning or a better candidate. Let the actual investigation change shape when the source and experiments reveal a better boundary.

The normal progression remains:

```text
note -> registry possibility -> formal lane -> exact investigation
```

Not every piece of work must pass through every stage.

## The minimum durable facts

Substantial work should make these facts discoverable:

- the bounded question or intended outcome;
- the current worker identities, branches, or competing variants when they matter;
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
Active workers or variants:
```

Use issue comments for short checkpoints, blockers, transfers, review requests, and next actions. Put commands, fixtures, source maps, results, interpretation, and evidence limits in the repository or a coherent pull request.

Detailed instructions are appropriate when a test method, safety condition, or exact compatibility boundary must be preserved. They are not the default.

## Use comment cards for live release work

A release desk needs one stable front-door issue whose body changes rarely. Put
the rules, links, and card format in that body. Put each live release unit in
one top-level comment on the desk.

The current editor updates that unit's comment in place as the head, evidence,
worker, or disposition changes. Other workers normally update different
comments. When two people need the same mutable card, use the brief mutable-
surface lease below rather than treating the release unit itself as reserved.

Every live card should contain:

```text
STATUS CARD
Unit:
Worker or variant:
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

## Identity, attribution, and overlap

Humans may use their GitHub identity. Agents and temporary workers may use a short stable callsign such as `LF-R01` for attribution during active work.

The identity tells reviewers who produced or reviewed evidence. It does not create a permanent role, exclusive lane ownership, competence claim, or authority grant.

A claim, assignment, issue comment, branch name, assignee, or status card is an advisory visibility signal. It does not reserve the question, source area, investigation, or candidate design. Several workers may independently reproduce, review, rewrite, or replace the same work. Check overlap to reuse evidence and understand competing decisions, not to ask permission to continue.

Use separate branches, pull requests, records, or exact commits for competing variants. A later variant may supersede an earlier one. It is acceptable to discard work after preserving the exact head and any unique evidence, failed hypothesis, fixture, or design lesson worth retaining.

Only a shared mutable surface may receive a brief lease. Examples are force-updating the same branch, editing the same live status comment, rewriting the same issue body, merging, or changing a shared release pointer. A lease:

- names the exact mutable surface and current worker;
- lasts no more than ten minutes unless renewed with a fresh timestamp and concrete progress;
- does not reserve the underlying problem or prevent parallel branches;
- expires automatically and needs no handoff ceremony;
- never authorizes deleting an unrecorded head or overwriting unseen changes.

Before a destructive or replacing write, refresh the surface, preserve the prior exact head or content identity, and compare what changed. Prefer superseding commits and branches over force-pushing. When replacement is useful, make the surviving evidence and decision clear rather than preserving every implementation indefinitely.

Record meaningful scope changes, competing variants, and supersession when they affect review. Do not force useful work to remain inside an obsolete assignment or wait for a nominal owner.

## Autonomous push work

An issue may declare an autonomous multi-helper push for a bounded batch. In that mode:

1. Every helper first reads [`README.md`](README.md), [`START_HERE.md`](START_HERE.md), this coordination guide, the push issue in full, and the live issues, pull requests, tracked records, and source revisions linked from its initial packet.
2. A helper letter, callsign, packet, or review pairing identifies an initial focus. It does not reserve work, limit review authority, or require another helper to finish first.
3. Begin useful work immediately. Do not wait for a coordinator, schedule, claim, reviewer assignment, or another packet when the next safe action is available.
4. Make bounded repository changes, execute focused gates, inspect the complete current diff, rerun after cleanup, and review the exact head being recommended. Careful self-review is valid for reversible internal work; higher-consequence work still deserves stronger independent review.
5. After completing the initial packet, inspect adjacent packets and the current open work. Continue with useful review, repair, evidence transfer, or closeout rather than ending solely because the initial packet is complete.
6. Keep active variants discoverable while allowing overlap. A short claim or transfer comment records who is acting; it never locks the work. Do not stop solely because another worker or branch exists; compare, reuse, compete, or supersede as the evidence warrants.
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
Worker or variant:
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
7. If the interruption exposes a genuinely higher-risk or authority-crossing direction, switch to **RECONVENE** mode below instead of trying to continue through the same interaction.

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

## Switch to RECONVENE mode for unexpectedly sensitive findings

`RECONVENE` is an exceptional transition, not the default response to security-adjacent work. Continue ordinary investigation, repair, and review when the work remains bounded to public source, local or owned systems, synthetic fixtures, disposable state, and authorized repository actions.

Examples that normally stay in the ordinary workflow include local path traversal proved with fake destructive commands, malformed-input crashes in a disposable fixture, cleanup or signal lifecycle errors, wrong-result bugs, permission mistakes, and defense-in-depth hardening whose practical consequence depends on several restrictive conditions.

Do not use a hard severity-score cutoff. A rough 7/10 or 8/10 estimate is useful context, not an authority decision. A lower-scored finding can still require reconvening if it exposes real credentials or a live target; a higher-scored finding can remain in the normal workflow when it is fully synthetic, locally bounded, already public in substance, and safe to repair and review. Judge the concrete operation, affected authority, deployment reach, ease of exploitation, and publication delta.

Continue normally when all of these remain true:

- no real secret, private data, or private repository content is exposed;
- no live public target or unrelated external system is being probed or changed;
- no unauthorized authentication or authorization boundary is crossed;
- no destructive, persistent, self-propagating, or production-impacting action is performed;
- the reproduction stays local, synthetic, disposable, or inside an explicitly owned testbed;
- the record can truthfully describe the defect and fix without adding materially dangerous operational detail beyond what is already public;
- cleanup, rerun, evidence limits, and external-contact authority remain explicit.

Switch to `RECONVENE` when one or more of these becomes true:

- real secrets, private data, private infrastructure, or identifying live-target details appear;
- the work reaches an unauthorized authentication or authorization bypass on a real system;
- a local model turns into a credible live exploit path with unusually broad, immediate, or low-friction impact;
- continuing would require destructive, persistent, stealthy, self-propagating, or production-changing action;
- the operational detail needed to continue cannot safely live in the current public repository or chat;
- public disclosure timing, coordinated handling, or a private security channel becomes a real decision rather than a hypothetical concern.

Public source does not automatically make every new exploit chain or operational detail safe to publish. The relevant question is what the current work newly enables, whom it affects, and whether the ordinary public record is still the right surface.

At that point, do not keep deepening the same path. Switch the unit to `RECONVENE`:

1. Stop expanding reproduction, target enumeration, exploitability, persistence, destructive action, or operational detail.
2. Preserve the exact repository state, raw artifact identity, first distinguishing observation, cleanup state, and evidence class. Do not delete valid evidence merely because the conclusion became sensitive.
3. Finish safe cleanup and verify that no process, mount, credential, temporary service, public target, or modified external state remains under the worker's control.
4. Put only public-safe facts in the ordinary issue or pull request: the affected component, broad failure class, exact internal head, evidence boundary, authority state, and the decision needed. Do not publish secrets, identifying private data, live target details, or step-by-step operational instructions.
5. Ask for one specific human decision: continue with a sanitized synthetic reduction, move the work into an explicitly authorized private security process, contact a named upstream destination, or stop and retain the result.
6. Resume only after the selected scope, storage surface, reviewer, and contact authority are explicit.

Use this compact handoff:

```text
RECONVENE CHECKPOINT
Unit:
Exact head:
Broad finding class:
Evidence retained:
Public-safe summary:
Cleanup state:
Current authority:
Decision required:
Permitted next step:
```

Sanitizing a report means removing secrets, private identifiers, and unnecessary operational detail while preserving the technical truth and evidence boundary. It does not mean disguising, fragmenting, encoding, or euphemizing work to evade safety, review, or authority controls.

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

Keep the broad report as orientation. Link focused and competing work from it. Preserve passing cases and failed hypotheses when they save future effort, but do not treat duplication itself as a failure. Independent implementations and reviews can expose hidden assumptions; retain the strongest result and the evidence needed to understand why other variants were superseded.

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

> Coordinate only enough to preserve attribution, evidence, recoverability, safe mutation, and upstream safety. Parallel work is allowed; adapt the rest to the work.

When a rule repeatedly causes stalled work, misleading ownership, avoidable information loss, or unnecessary review ceremony, improve the rule rather than teaching everyone to work around it.
