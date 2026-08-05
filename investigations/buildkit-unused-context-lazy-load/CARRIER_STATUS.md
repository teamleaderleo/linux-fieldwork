# BuildKit unused-context carrier status

- State: `ACTIVE`
- Controlled fork: `teamleaderleo/buildkit`
- Test branch: `research/unused-context-lazy-load`
- Test-only head: `4024335d0e905d1206786644d8f363336d4678ec`
- Exact canonical base commit: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Internal draft PR: `teamleaderleo/buildkit#2`
- PR state at latest review: open, draft, mergeable
- Submitted reviews/comments: none observed on controlled PR #2
- Candidate source patch: `candidate-lazy-main-context.patch`
- Canonical-project contact: none

## Static carrier receipt

Linux Fieldwork run `31012029092`, job `92326394200`, succeeded on the exact test carrier. Checkout identity, canonical-base ancestry, `git diff --check`, `gofmt`, vendored Dockerfile package compilation, and cleanup passed.

## Live baseline receipt

BuildKit frontend workflow run `30942870861` executed the focused test across the frontend backend matrix. The retained JUnit artifact `buildkit-frontend-containerd-test-reports.zip` (artifact ID `8914318532`) records the first named failure:

```text
TestIntegration/FrontendDockerfileSuite/TestContextAccess/metadata-only
unexpected context access in metadata-only build: walk=1 open=0
```

The same metadata-only subtest failed across all frontend backends. Setup succeeded and the failure is inside the new test, so this is shared converter behavior rather than a backend-specific setup failure. The local `COPY` and default-context bind cases remain the positive controls that require main-context access.

## Source owner

At the exact canonical base, `dispatchStages()` calls `Client.DockerIgnorePatterns(ctx)` before any command-specific decision. Later, `finalizeResultImage()` calls `MainContext()` unconditionally. Local ADD/COPY and default-context run mounts already populate the aggregated `ctxPaths`; explicit context scanning is represented by `scanContext`.

## Candidate

The retained candidate:

1. memoizes Docker ignore matcher construction and invokes it only from local ADD/COPY dispatch;
2. materializes the main context only when `ctxPaths` is non-empty or context SBOM scanning is requested;
3. leaves named/stage/remote sources outside the default-main-context gate.

Linux Fieldwork run `31021699370` is the first exact-source apply, formatting, and package-compile gate for this candidate. It was queued when this record was written; queued is not a result.

## Next technical action

Classify run `31021699370`. Repair the first patch/apply/format/compile failure if present. After a green static candidate receipt, apply the candidate to a controlled BuildKit source branch and rerun the same frontend integration matrix. The unit remains `ACTIVE`; no human approval is needed for these internal technical steps.

## Authority

No canonical BuildKit issue comment, pull request, review, email, or other external contact is authorized or made.
