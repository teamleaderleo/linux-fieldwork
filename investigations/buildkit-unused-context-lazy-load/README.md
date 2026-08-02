# BuildKit unused local context loading

## TL;DR

At BuildKit commit `275d6864ff0ce91a06225af5f5b012887bd257cf`, Dockerfile conversion still touches the local build context even when the reachable build graph never consumes a context file. There are two separate eager operations: `dispatchStages()` loads Docker ignore patterns before dispatching any instruction, and `finalizeResultImage()` calls `MainContext()` unconditionally. A sound repair needs two lazy gates rather than merely moving one call.

## Explain like I'm five

A recipe says “start with an empty box and write a label on it.” The builder still asks a delivery truck to bring the entire ingredient cabinet, even though the recipe never uses an ingredient.

Literal example: `FROM scratch` plus metadata-only instructions → Dockerfile is available → no `COPY`, `ADD`, or context bind is reachable → BuildKit still opens the main local context to look for `.dockerignore` and later creates the context source.

## Why care

An unused local input can still become observable in build progress, provenance, session traffic, access checks, and failure behavior. A remote or restricted builder can fail because a context is unavailable even though the selected Dockerfile target does not need it. Unnecessary context capture also weakens the distinction between “declared input” and “consumed input.”

## Current state

- State: `SCOPING`
- Exact working head: canonical `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Latest authoritative gate or artifact: exact source-path review of Docker UI and Dockerfile-to-LLB conversion
- First incomplete step: create a gateway-client fixture that supplies the Dockerfile input but makes the main context detectably unavailable
- Cleanup state: no daemon, worker, content-store object, branch, or temporary context created in this round
- Next safe action: create an exact canonical-base branch in the controlled BuildKit fork and land the failing tests before selecting a callback interface
- External-contact state: none authorized or made

## Intent and precedent

Public issue `moby/buildkit#3267` was opened by a maintainer and describes the intended direction: avoid capturing the local context when a Dockerfile does not use it, possibly by moving Docker ignore loading behind a callback invoked only when conversion requests context files.

Current source shows that the issue is split across two phases:

1. `dispatchStages()` asks the Docker UI client for Docker ignore patterns before it knows whether a reachable command has a local source that needs validation.
2. `finalizeResultImage()` calls `MainContext()` and assigns its output to the mutable context placeholder even when the collected context-path set is empty.

The first call supports the `CopyIgnoredFile` linter warning. The second supplies the actual local LLB source used by local `COPY`, `ADD`, and context-backed mounts. These operations have related but non-identical purposes.

## Question

Can Dockerfile conversion avoid all main-context access when the selected reachable graph does not consume the context, while preserving ignore-file linting and context filtering exactly when local paths are used?

## Source

- Project: BuildKit
- Requested revision: current canonical `master` observed 2026-08-03
- Resolved commit: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- `frontend/dockerui/config.go` blob: `5bbe333dcd594415c14432c37b5db540d08e48e2`
- `frontend/dockerfile/dockerfile2llb/convert.go` blob: `4a4aa7eec4489651a524ee2f8ae09f574bfa0e18`
- `frontend/dockerfile/dockerfile2llb/convert_copy.go` blob: `75d5913d347c9d8d345b01600ff42bccd221c4a8`
- `frontend/dockerfile/dockerfile2llb/validations.go` blob: `9a3523a7ef4d1977f91d113b3955a17e8420cf97`
- Candidate source commit: none
- Controlled fork: `teamleaderleo/buildkit`
- Fork head observed: `df0761886a20e368d75e0aa6bb3f20874f58b692`
- Current-main relation: canonical was five commits ahead, with no unique fork commits at the observed merge base
- Local source path: not imported yet
- Import metadata: not present

## Environment

- Distribution and release: not executed in this round
- Kernel and architecture: ordinary Linux CI should be sufficient for the first converter fixture
- Shell: test harness dependent
- Privileges: unprivileged
- Context: in-process gateway/client fixture first; daemon integration only if needed to prove provenance or session behavior
- Relevant tool versions: record Go version and BuildKit test target at execution time

## Baseline behavior

### Dockerfile entrypoint

`ReadEntrypoint()` obtains the Dockerfile from its Dockerfile local input. It follows both the Dockerfile and its Dockerfile-specific ignore file and caches that ignore data if present. This access is required because the Dockerfile itself is an input even when the main build context is not.

### Eager ignore access

`dispatchStages()` currently calls `Client.DockerIgnorePatterns(ctx)` before dispatching reachable stages. When no Dockerfile-specific ignore data was cached, `DockerIgnorePatterns()` constructs and solves a local source that follows the default `.dockerignore` path in the **main context**.

The resulting matcher is used by `validateCopySourcePath()` to issue the `CopyIgnoredFile` lint warning for local `COPY` or `ADD` paths. Remote HTTP, Git, stage, image, and inline-document sources do not use that matcher in the same way.

### Eager context materialization

After dispatch, `finalizeResultImage()` computes context filters, then calls `Client.MainContext(ctx, opts...)` unconditionally. `MainContext()` loads ignore patterns and constructs the `llb.Local` source. Its output is assigned to the mutable context placeholder used by dispatched operations.

This occurs even when `ctxPaths` is empty.

## Hypothesis or candidate

The repair likely needs two lazy interfaces.

### Gate A: lazy ignore matcher

Load Docker ignore patterns only when dispatch encounters a reachable local source whose static validation needs the matcher.

Possible forms:

- a memoized callback on `dispatchOpt` that returns the matcher on first use;
- a Docker UI method passed through `ConvertOpt` and called from local copy validation;
- a two-pass decision that first detects whether reachable instructions contain local context sources, then loads patterns once.

The callback form best matches the public issue direction and avoids coupling graph discovery to eager I/O.

### Gate B: conditional main context

Only call `MainContext()` when the mutable context output is actually referenced by the reachable result or when an explicit feature requires the full context, such as context SBOM scanning.

A simple `len(ctxPaths) > 0` check may be insufficient. Context use can include:

- local `COPY` and `ADD`;
- `RUN --mount=type=bind` with the main context;
- context scanning requested by `BUILDKIT_SBOM_SCAN_CONTEXT`;
- future commands that retain the mutable context output without adding a conventional copied path.

The deciding signal should represent **context consumption**, not only a non-empty path-filter set.

### Required preservation

The candidate must preserve:

- Dockerfile-specific `.dockerignore` precedence;
- default `.dockerignore` parsing when the main context is used;
- `CopyIgnoredFile` warnings for local sources;
- context path filtering and cache identity;
- named contexts and `COPY --from=` behavior;
- remote Git and HTTP `ADD` behavior;
- inline heredoc sources;
- lint, outline, and convert subrequests;
- multi-platform builds without duplicate context fetches;
- context SBOM scanning.

## Reproduction

The most discriminating fixture should separate the Dockerfile input from the main context input.

### Negative control: context-free target

```Dockerfile
FROM scratch
LABEL fieldwork=context-free
```

Provide the Dockerfile through the Dockerfile local input. Configure the main-context provider so any read or solve is recorded and fails with a unique sentinel error.

Expected after repair:

- Dockerfile conversion succeeds;
- no main-context solve occurs;
- no `.dockerignore` read occurs from the main context;
- no context source appears in the resulting definition or provenance unless explicitly requested.

### Positive control: local copy

```Dockerfile
FROM scratch
COPY probe /probe
```

Expected:

- the sentinel main-context access is observed;
- with a real context, ignore parsing and filtered local source behavior remain unchanged.

### Other controls

```Dockerfile
FROM scratch
COPY <<EOF /inline
inline
EOF
```

must remain context-free.

```Dockerfile
FROM scratch AS source
RUN echo data >/probe
FROM scratch
COPY --from=source /probe /probe
```

must remain main-context-free.

```Dockerfile
FROM scratch
ADD https://example.invalid/probe /probe
```

must not load the local context merely because `ADD` exists.

A context-backed `RUN --mount=type=bind` must load it.

## Results

### Demonstrated by exact source review

- `dispatchStages()` loads Docker ignore patterns before any instruction-specific decision.
- Default ignore loading performs a main-context local solve when no Dockerfile-specific ignore data is already cached.
- The matcher is used for local copy-source lint validation.
- `finalizeResultImage()` calls `MainContext()` regardless of whether the collected context path set is empty.
- The public issue remains open, unassigned, marked `help wanted`, and had no visible competing pull request in the overlap search performed during this round.

### Not yet demonstrated here

- A failing exact-head test with a sentinel context provider.
- The exact provenance delta.
- The best internal consumption signal for context-backed run mounts and SBOM scanning.
- Candidate compatibility with every Dockerfile frontend subrequest.

## Interpretation

Moving only `.dockerignore` loading is incomplete because finalization still materializes the context. Guarding only finalization is also incomplete because the linter path touches the context earlier.

The likely design is a memoized, instruction-triggered ignore loader plus an explicit context-consumed signal that controls final materialization. The tests should define that contract before the callback API is chosen.

## Cross-context review

| Context | Should main context load? | Discriminator |
|---|---:|---|
| Metadata-only reachable target | no | no local context source |
| Unreachable stage contains `COPY` | no | target reachability |
| Local `COPY`/`ADD` | yes | source is main context |
| `COPY --from=stage` | no | source is stage state |
| Named context | not the default main context | separate context identity |
| HTTP/Git `ADD` | no | remote source owns bytes |
| Inline heredoc copy | no | source is generated scratch state |
| Context bind mount | yes | execution consumes main context |
| Context SBOM scan | yes | explicit full-context consumer |
| Lint/outline subrequest | only if its contract requires ignore data | subrequest semantics |
| Multi-platform conversion | once per shared context identity where possible | memoization and session identity |

Stop widening the candidate after all current context consumers are represented by one explicit signal. Split provenance-only changes if they require unrelated result metadata work.

## Evidence boundary

This investigation records source behavior and a test design. It does not claim a passing candidate, a daemon-level reproduction, reduced network transfer, or a verified provenance change. No BuildKit worker, snapshotter, registry, or rootless runtime was started.

## Next step

Create an exact canonical-base branch in `teamleaderleo/buildkit` and implement tests in this order:

1. sentinel main context plus context-free Dockerfile;
2. local-copy positive control;
3. stage, inline, HTTP/Git, named-context, and bind-mount controls;
4. context SBOM scan;
5. multi-platform and frontend subrequests.

Use the failing tests to choose the smallest memoized loader and context-consumption signal. Do not start with a product-code patch.

## Authority

No upstream issue, pull request, comment, email, review, or other external interaction has been authorized or made.