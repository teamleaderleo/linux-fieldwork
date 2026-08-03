# Test carrier — BuildKit unused main context

## Exact identities

- Canonical BuildKit base: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Controlled fork: `teamleaderleo/buildkit`
- Snapshot base branch: `linux-fieldwork/upstream-master-snapshot-2026-08-03`
- Test branch: `research/unused-context-lazy-load`
- Test-only head: `67c480358d6f5d1fd2e3d41bb3fd460e3957210e`
- Internal draft PR: `teamleaderleo/buildkit#2`
- Test path: `frontend/dockerfile/dockerfile_context_access_test.go`
- Product source changed: no
- Canonical-project contact: none

## Purpose

Retain a failing integration contract before choosing a lazy-loader API.

The Dockerfile is supplied through `dockerui.DefaultLocalNameDockerfile` using a normal temporary filesystem. The default main context is a custom `fsutil.FS` whose first `Walk` or `Open` increments an atomic counter and returns the unique error:

```text
main build context was accessed
```

This makes context use observable without relying only on progress text, provenance serialization, or transfer size.

## Test registration

The carrier appends `testDockerfileLazyContextAccess` to the package's existing `allTests` slice through an `init()` function. It therefore uses the same:

- worker initialization;
- builtin/client/gateway frontend matrix;
- mirrored-image setup;
- sandbox lifecycle;
- Linux platform gating;
- integration result reporting

as the surrounding Dockerfile suite, without creating a second top-level integration runner.

## Matrix

### Metadata-only target

```Dockerfile
FROM scratch
LABEL org.mobyproject.buildkit.test=unused-context
```

Required result:

- solve succeeds;
- sentinel access count remains zero.

Current exact-head expectation:

- solve fails with the sentinel because current conversion touches the main context eagerly.

### Local copy control

```Dockerfile
FROM scratch
COPY marker /marker
```

Required result:

- main context is accessed;
- sentinel error is returned;
- access count is positive.

### Context bind control

```Dockerfile
FROM busybox
RUN --mount=type=bind,source=.,target=/src test -f /src/marker
```

Required result:

- main context is accessed;
- sentinel error is returned;
- access count is positive.

## Why both positive controls are needed

Local `COPY` records paths in the Dockerfile conversion flow. A default-context bind mount consumes the same mutable context through execution rather than a copy operation. A final condition based only on copied path count could pass the first control and break the second.

## What the first failure establishes

A failing metadata-only subtest proves that some main-context operation occurs despite no reachable consumer. It deliberately does not claim whether the first observed access came from:

1. default `.dockerignore` loading in `dispatchStages()`; or
2. unconditional `MainContext()` materialization in finalization.

Exact source review already shows both gates. Candidate development should temporarily disable or instrument one gate at a time so the retained test is not satisfied by repairing only the first observed failure.

## Static validation plan

Linux Fieldwork workflow `.github/workflows/research-carrier-static.yml` pins this exact head and performs:

- ancestry check against the canonical base;
- `git diff --check`;
- `gofmt` verification for the new file;
- vendored package compile with `go test -mod=vendor ./frontend/dockerfile -run '^$'`.

The hosted compile receipt is pending. The local execution container could not resolve `github.com`, so its clone/compile attempt stopped before source checkout. That is an environment limitation, not a code result.

## Runtime plan

The first hosted runtime should select only `testDockerfileLazyContextAccess` and retain all frontend/worker matrix outcomes.

Expected baseline classification:

- metadata-only: fails with sentinel;
- local-copy: passes its expected-error assertions;
- context-bind-mount: passes its expected-error assertions.

The overall test remains red until metadata-only no longer touches the context.

A later candidate run must be compared against the same exact test source.

## Next controls

After the three-case gate is stable, add independent context-free controls for:

- `COPY --from=stage`;
- inline heredoc copy;
- HTTP `ADD`;
- Git `ADD`;
- unreachable stages containing local `COPY`;
- named contexts;
- lint, outline, and targets subrequests;
- context SBOM scanning;
- multi-platform conversion.

These should be added according to distinct consumer classes, not merely to increase test count.

## Candidate boundary

Do not infer a final interface from the first failing call. A complete candidate must address:

- lazy, memoized ignore-pattern loading when a reachable local source needs static validation;
- explicit main-context consumption controlling final materialization;
- context bind mounts and SBOM scans that may not look like ordinary copied paths;
- Dockerfile-specific ignore precedence;
- one shared context identity across multi-platform work where possible.

## Authority

This is an internal controlled-fork, test-only carrier. No BuildKit issue comment, pull request, review, email, or other canonical-project interaction was created.
