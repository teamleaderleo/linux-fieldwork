# Investigation title

## In simple words

### Explain it like I am five

Describe the component and its job with ordinary words. One useful analogy is welcome when it clarifies the authority or lifecycle involved.

### What goes wrong?

Give one literal input → action → bad result example. Name the exact file, byte stream, process, privilege, package, or decision affected.

### Why should someone care?

Describe the concrete consequence and who or what receives it.

### What happens if this remains?

Explain the repeatable outcome. Say whether an error persists through caching, retries, saved state, cleanup, or later consumers.

### Was this intentional?

Separate:

- evidence of a deliberate compatibility or design choice;
- evidence of a shortcut or friendly-input assumption;
- your interpretation where source history is incomplete.

### Proposed answer or fix

Describe the before/after behavior and why this boundary is preferable to narrower and broader alternatives.

### Historical or technical precedent

Link primary sources such as standards, official manuals, language documentation, upstream source/history, or an established weakness catalogue. Explain how each source applies to this case.

## Question

State one bounded technical question.

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

State the compatibility policy explicitly:

- accepted inputs or behaviors;
- rejected inputs or behaviors;
- preserved historical behavior;
- deliberately deferred redesigns.

## Reproduction

Record exact commands and setup steps.

```sh
# commands here
```

## Results

Record observed output, exit status, files created or changed, cleanup behavior, timings, logs, and other distinguishing outcomes.

For a candidate, show baseline and candidate under comparable conditions.

## Interpretation

Explain what the results establish and how they answer the question.

Label important conclusions as appropriate:

- demonstrated defect;
- plausible consequence kept outside the safe fixture;
- design judgment;
- open question.

## Evidence boundary

State the exact limits: skipped test suites, untested platforms, reduced fixtures, mocked components, privilege assumptions, environment-specific behavior, and claims the work leaves open.

## Next step

Choose a concrete next action or close with a retained negative result.

For a human decision, say what the reviewer is choosing in ordinary language and name the exact evidence that supports that choice.

## Authority

State whether any upstream issue, email, merge request, patch submission, comment, review, or other interaction has been authorized or created.