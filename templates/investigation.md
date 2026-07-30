# Investigation title

## In simple words

Explain what component or workflow is involved, where it sits, what is being tested or changed, why someone could care, and the current answer or next step.

## Question

State one bounded technical question.

## Existing work and duplicate search

- Issues and pull requests searched:
- Programme, target, research, note, and investigation records searched:
- Existing work reused or linked:
- Why this is not a duplicate:

## Source

- Project:
- Requested revision or package version:
- Resolved commit:
- Candidate source commit:
- Local source path:
- Import metadata:

## Source and test map

Name the owning function or component, its callers, cleanup path, adjacent tests, and the exact missing assertion or behavior being investigated.

## Environment

- Distribution and release:
- Kernel and architecture:
- Shell:
- Privileges:
- Container, virtual machine, or host context:
- Relevant tool versions:

## Baseline behavior

Describe what the unmodified source or current system does.

## Hypothesis or candidate

Describe the behavior that would distinguish the likely explanations, or describe the candidate change being tested.

List the expected distinguishing outcomes before running the probe.

## Reproduction

Record exact commands and setup steps.

```sh
# commands here
```

## Assertions and negative control

List the conditions the probe enforces. Describe and execute at least one deliberate break that must make the harness fail when practical.

## Results

Record observed output, exit status, files created or changed, cleanup behavior, timings, logs, and other distinguishing outcomes.

## Cleanup and rerun

Record surviving processes, descriptors, locks, mounts, temporary paths, package state, or other retained state as relevant. Record the immediate rerun result.

## Interpretation

Explain what the results establish and how they answer the question.

## Evidence boundary

State the exact limits: skipped test suites, untested platforms, reduced fixtures, mocked components, privilege assumptions, environment-specific behavior, and claims the work leaves open.

## Self-review

- Exact reviewed head:
- Complete diff inspected:
- Failure and cleanup paths checked:
- Destructive path and privilege safety checked:
- Concurrency or repeated execution checked where relevant:
- Claims compared with executed evidence:
- Remaining concerns:

## Peer review

- Reviewer and reviewed head:
- Findings:
- Required changes and re-review result:

## Reusable notes

- Related note created or updated:
- Or `Notes: not applicable` with rationale:

## Next step

Choose a concrete disposition: implement a bounded fix, retain, expand, stop, block on a named dependency, or prepare an authorized upstream packet.

Do not stop at a report when a confirmed defect has a small feasible local fix and regression test.

## Authority

State whether any upstream issue, email, merge request, patch submission, comment, review, or other interaction has been authorized or created.
