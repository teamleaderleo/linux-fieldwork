# Codex tool-surface interruption corroboration

Date: 2026-08-03

Tracking: issue #194 and the existing `notes/handoffs/2026-07-31-helper-b-codex-execution-recovery.md` record.

## Scope

This is an internal process and evidence note. It does not resume mmdebstrap work, change a product candidate, rerun a package matrix, or contact OpenAI, Debian, or any other upstream.

## Observed event

A tool-heavy interaction stopped abruptly immediately after a connector/tool sequence. The user saw the reasoning stream end rather than a normal completion or a useful error explanation.

The durable record does not contain a definitive platform error receipt identifying the exact cause. A malformed invocation or stale tool shape is plausible from the visible sequence, but it is not proved. The correct classification is therefore:

```text
failure owner: interaction / tool-or-connector boundary
exact cause: unresolved
product result: none
permission result: none
remote mutation result: refresh before inferring
```

This distinction matters. An abrupt interaction stop is evidence about delivery continuity, not evidence that the repository, hosted job, product, or safety decision failed.

## Corroboration of the existing report

The earlier Codex recovery report remains directionally correct and is corroborated by later repository history.

1. Merged PR #265 made interruption recovery canonical in `ADAPTIVE_COORDINATION.md`: checkpoint the exact head and evidence boundary, classify the first incomplete step by owner, and reconstruct from repository evidence instead of chat narration.
2. Merged PR #382 added a concrete later example where a hosted job completed and uploaded an artifact after the chat stopped. The run state had to be refreshed rather than inferred from the interruption.
3. PR #261 was retired because PR #265 already carried the stronger canonical rule. This supports the report's instruction to select one canonical carrier rather than preserving duplicate recovery terminology.
4. The relative-executable/cwd scanner proposed in historical PR #222 is present on current `main` through later landed commit `e9a3dcb89f7adaeb9051fd16f170b0c4c4b88442`. The closed predecessor PR is not the final ownership record; exact current source and its landing commit are.
5. The current recovery handoff itself is present on `main`, including its later resumption checkpoint. That durable file, not the interrupted conversation, provided the recoverable state for this review.

## New insight: refresh the tool surface, not only the repository

The existing protocol says to reload instructions, source, heads, runs, artifacts, and receipts. A tool-boundary interruption adds one more required refresh:

> Re-discover the current connector function and schema before the next call when the interruption occurred during dynamic tool discovery, tool routing, or a schema-changing sequence.

Using the correct source-owning connector is necessary but not sufficient. A previously loaded recipient name, argument shape, capability subset, or write method can become stale within a long interaction. Reusing it blindly can create a second failure that looks like the first one.

For a read operation, refresh the schema and retry once through the source-owning connector. For a mutation, first inspect the remote surface to determine whether the prior call committed before its response disappeared. Only then decide whether to retry, update, or record the already-completed mutation.

## Three mutation states to keep separate

After an interrupted tool call, classify the attempted operation as one of:

1. **Not executed** — the call was rejected before reaching the remote system.
2. **Executed with a retained failure receipt** — the remote system answered with a concrete error and no successful mutation.
3. **Execution uncertain or response lost** — the interaction ended without a reliable receipt; refresh the remote head, issue, pull request, run, or comment before repeating anything.

The third state is the dangerous one for duplicate comments, duplicate pull requests, repeated workflow dispatches, or conflicting file writes. “The chat stopped” never proves “the write did not happen.”

## Suggested interruption checkpoint additions

When the interruption occurs inside a connector sequence, append these fields to the existing checkpoint rather than creating a second canonical format:

```text
Last attempted operation:
Operation class: read | mutation
Durable receipt: success | failure | absent
Remote state refreshed:
Tool/schema refreshed:
Retry decision:
```

These fields extend the existing `INTERRUPTION CHECKPOINT`; they do not replace it.

## Evidence limits

- The exact internal platform cause of the 2026-08-03 stop is unresolved.
- This note does not claim a general Codex product defect or reproduce the event in a controlled fixture.
- No private chain-of-thought content is required to recover the work. Repository state, connector receipts, and the user's visible observation are sufficient for the process conclusion.
- The relative-executable scanner concerns child process identity after cwd changes. It is useful precedent for stale identity assumptions, but it does not detect malformed API or connector calls.

## Current decision

`MERGE LOCALLY` candidate as a one-file corroboration note after complete diff review.

A later canonical-instructions edit is justified only if this schema-refresh rule recurs or reviewers prefer promoting it immediately. Avoid duplicating the already-merged PR #265 recovery section.

External contact remains unauthorized and none occurred.
