# Adaptive Coordination

## Working rule

Coordinate only enough to preserve attribution, exact evidence, resumability, safe writes to shared mutable surfaces, and deliberate external contact. Parallel or competing work is allowed. Assignments, assignees, branch names, callsigns, and status cards make work visible; they do not reserve a question, source area, investigation, or candidate design.

The usual research progression is `note -> registry possibility -> formal lane -> exact investigation`, with stages skipped when useful. [`START_HERE.md`](START_HERE.md) owns work-type guidance; this file owns collaboration semantics.

## Minimum durable facts

Substantial work should make these facts discoverable:

- the bounded question or intended outcome;
- current workers or competing variants when relevant;
- the issue, branch, exact head, source revision, package version, or lane that identifies the work;
- the evidence that exists and where it stops;
- cleanup state and the next useful action when relevant;
- whether external contact is authorized.

Add ceremony only when it protects one of those facts.

## Issues, pull requests, and live cards

Use an issue as a dispatch card, not a command transcript. A small assignment can carry:

```text
Question:
Why care:
Useful starting points:
Known boundaries:
Active workers or variants:
```

Use issue or pull-request comments for short claims, checkpoints, blockers, transfers, review requests, and decisions. Put commands, fixtures, source maps, results, interpretation, and evidence limits in tracked records or a coherent pull request, then link them instead of copying long reports.

For live release work, keep one stable front-door issue and one editable top-level comment per live unit:

```text
STATUS CARD
Unit:
Worker or variant:
State:
Exact head:
Owning issue or PR:
Tracked evidence:
Latest gate:
Remaining boundary:
Next action:
External-contact state:
```

The live comments are the board. Update the unit's comment in place. When the unit lands, retires, or moves away, preserve its final receipt in the owning issue or pull request and remove the live card; if deletion is unavailable, replace it with a short `ARCHIVED` line and the final receipt. A card points to evidence rather than duplicating it.

## Identity, overlap, and shared mutation

Humans may use their GitHub identity. Agents and temporary workers may use a stable callsign such as `LF-R01`. Identity supports attribution and review; it creates no permanent role, exclusivity, competence claim, or authority grant.

Use separate branches, pull requests, records, or exact commits for competing variants. Compare overlapping work to reuse evidence and understand decisions. A later variant may supersede an earlier one; before discarding work, preserve any unique exact head, failed hypothesis, fixture, result, or design lesson worth retaining.

Only a shared mutable surface may receive a brief lease: for example, force-updating the same branch, editing the same live card or issue body, merging, or changing a shared release pointer. A lease names the exact surface and worker, lasts at most ten minutes unless renewed with a fresh timestamp and concrete progress, never reserves the underlying problem, and never authorizes overwriting unseen work. Before a destructive or replacing write, refresh the surface, preserve the prior exact identity, and compare what changed. Prefer superseding commits or branches to force-pushes.

Record scope changes, competing variants, and supersession when they affect review. Useful work may continue outside an obsolete assignment or nominal owner.

## Autonomous push work

For an issue that declares an autonomous multi-helper push:

1. Read the issue in full, the repository router, this guide, and the live work, records, and source revisions linked by the packet before acting.
2. Treat a callsign, helper letter, packet, or review pairing as an initial focus only. Begin useful work without waiting for claims, schedules, coordinator approval, or another helper when the next repository action is already authorized.
3. Make bounded changes, run focused gates, inspect the complete current diff, rerun after cleanup, and review the exact head being recommended. Reversible internal work may use careful self-review; higher-consequence work deserves stronger independent review.
4. After the initial packet, inspect adjacent open work and continue with useful review, repair, evidence transfer, or closeout. Parallel variants remain allowed.
5. Record substantial completed work in both the owning issue or pull request and the relevant tracked fieldwork record. The issue or PR carries disposition, exact head, gates, caveats, authority, and next decision; the tracked record carries commands, fixtures, results, interpretation, and evidence limits.

Leave enough durable state for another worker to reproduce, review, and continue even if chat disappears.

## Durable checkpoints and interruption recovery

Write or update one compact checkpoint before a long-running, tool-heavy, scope-changing, difficult-to-reconstruct, or sensitive-looking step, and whenever exact head, evidence, changed paths, gates, cleanup, authority, or next action changes. Edit the live checkpoint in place when possible; move substantial commands and results into tracked records.

Use the same checkpoint when an interaction, connector, local command, hosted job, or safety check stops:

```text
WORK CHECKPOINT
Unit:
Worker or variant:
State:
Exact head:
Question:
Changed paths:
Evidence so far:
Completed gates:
First incomplete step / failure owner:
Cleanup and evidence boundary:
Next safe action:
External-contact state:
```

Existing routers that refer to an `INTERRUPTION CHECKPOINT` mean this `WORK CHECKPOINT`; `WORK CHECKPOINT` is the canonical name.

Mark unknown, queued, skipped, or unreviewed facts explicitly. Preserve the first distinguishing observation before deepening a surprising result. Keep secrets, private credentials, unsafe operational detail, and speculative attribution out of public checkpoints.

An interruption is a coordination event, not evidence of a product defect or permission decision. On resumption, reload the owning issue or pull request, exact head, tracked record, raw artifacts, and current receipts. Classify the first incomplete or failing step as product, fixture/harness, tool/connector, environment, hosted execution, or interaction/safety before changing product code. For benign safety-sensitive work, prefer synthetic fixtures, disposable state, fake destructive commands, and no external contact.

For a genuinely disclosure-sensitive finding, follow [`SECURITY_RECONVENE.md`](SECURITY_RECONVENE.md). It owns the threshold and handling rules. Keep this public-safe handoff when that guide calls for `RECONVENE`:

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

## Review and branching

Choose review strength by consequence and evidence, not a fixed reviewer ring. Tiny probes and clear negative results may receive light review; bounded reversible repository work may use careful self-review; security findings, destructive operations, broad claims, merge candidates, and upstream packets deserve stronger independent or specialist review. Review the exact evidence and current head.

Broad reconnaissance should create concrete next branches. Once a specific behavior, compatibility boundary, failure, or candidate appears, prefer a focused investigation to an indefinitely growing scout report. Keep useful passing cases and failed hypotheses when they save future work.

## External GitHub backlinks

Quiet coordination must avoid accidental backlinks or notifications in third-party official repositories.

In GitHub interaction text — issue and pull-request titles and bodies, comments, reviews, discussions, and intentional external references in commit messages — refer to third-party GitHub objects through:

```text
https://redirect.github.com/OWNER/REPOSITORY/issues/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/pull/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/discussions/NUMBER
https://redirect.github.com/OWNER/REPOSITORY/commit/SHA
```

Do not use bare third-party shorthand such as `OWNER/REPO#123` in interaction prose. Direct links among controlled `teamleaderleo/*` repositories are fine. Repository notes, reports, maps, and other tracked files may link directly to third-party GitHub objects because they do not create issue or pull-request cross-reference events; ordinary websites, specifications, package registries, and release pages may also be linked normally.

A human-designated upstream candidate has the stricter commit-message rule in [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md): external issue and pull-request references stay out of candidate commits entirely.

Use a direct third-party issue, pull-request, discussion, or commit link in interaction text only when recording an explicitly authorized upstream interaction. Redirect hygiene never grants contact authority.
