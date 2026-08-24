# Investigation title

## In simple words

State the current answer or concrete question, the component's job, and the practical consequence. Include a literal input → action → result example when it helps.

Use `TL;DR`, `Why care`, a state trace, or another reader entry point instead when that communicates the work better. Follow [`WRITING.md`](../WRITING.md); reader-facing headings are tools rather than a required three-part ritual.

## Current state

Keep this block short and update it while the work changes. Put transcripts and detailed interpretation in the sections below.

- State: `SCOPING | EXECUTING | REPAIR | REVIEW | HOLD | COMPLETE`
- Exact working head:
- Latest authoritative gate or artifact:
- First incomplete step:
- Cleanup state:
- Next safe action:
- External-contact state:

## Intent and precedent

State what source or history shows about intent. Separate evidence from interpretation, and link the primary sources that govern the behavior.

## Question

State one bounded technical question. Omit this section when the opening already carries the exact question and repetition would add nothing.

## Source

- Project:
- Requested revision or package version:
- Resolved commit:
- Candidate source commit:
- Local source path:
- Import metadata:

## Environment

- Distribution and release:
- Kernel and architecture:
- Shell:
- Privileges:
- Container, virtual machine, or host context:
- Relevant tool versions:

## Baseline behavior

Describe what the unmodified source or current system does. Include the concrete example promised near the top.

## Hypothesis or candidate

Describe the behavior that would distinguish the likely explanations, or describe the candidate change being tested.

State what the candidate accepts, rejects, preserves, and deliberately leaves for later work.

## Reproduction

Record exact commands and setup steps.

```sh
# commands here
```

## Results

Record observed output, exit status, files created or changed, cleanup behavior, timings, logs, and other distinguishing outcomes.

For a candidate, show baseline and candidate under comparable conditions.

## Interpretation

Explain what the results establish and how they answer the question. Distinguish demonstrated behavior, plausible consequence, design choice, and open question where relevant.

## Evidence boundary

State the exact limits: skipped test suites, untested platforms, reduced fixtures, mocked components, privilege assumptions, environment-specific behavior, and claims the work leaves open.

Keep a major caveat beside the claim it qualifies near the top as well; this section collects the complete boundary instead of revealing it late.

## Next step

Choose a concrete next action or close with a retained negative result.

For a human decision, say what the reviewer is choosing and name the exact supporting evidence. End after the decision lands; a closing recap is optional.

## Authority

State whether any upstream issue, email, merge request, patch submission, comment, review, or other interaction has been authorized or created.
