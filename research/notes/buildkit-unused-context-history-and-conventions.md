# BuildKit unused-context history and conventions

## Scope

This note records how the design constraints around `moby/buildkit#3267` changed after the issue was opened. It supports the test carrier in `investigations/buildkit-unused-context-lazy-load/` and does not select a product API.

## Timeline

### 2022-11-09 — unused-context issue opened

Maintainer-authored issue `moby/buildkit#3267` observed that a Dockerfile with no main-context consumer still captured the local context because the frontend tried to read `.dockerignore` before `Dockerfile2LLB`.

The proposed direction was a callback that would load ignore data only when conversion actually requested files from the context.

At that point the current `CopyIgnoredFile` lint rule did not exist.

### 2024-07-10 — `CopyIgnoredFile` merged

PR `moby/buildkit#5135`, merge commit `e83d79a51fb49aeb921d8a2348ae14a58701c98c`, added a Dockerfile check for `COPY` or `ADD` sources excluded by `.dockerignore`.

Its implementation deliberately loaded Docker ignore patterns before stage dispatch and placed a matcher in `dispatchOpt`. Local main-context copies used the matcher; stage copies did not.

This attached a new semantic purpose to the eager read originally called out by issue #3267.

### 2025-11 — path matching repair

Commit `143a046f6230fbb0a8e840daacf92d9b77b3cdfc` cleaned source paths before matching, especially for exclusion patterns.

This shows that the linter's input semantics are subtle. A lazy loader must return the same parsed pattern set and preserve the same path normalization point.

### 2026-01-08 — lint rule promoted

Commit `4187c344ceefe2f0218835d1cd585453cf8c8e2e` promoted `CopyIgnoredFile` out of experimental status.

Current code can no longer treat ignore loading as an optional experimental side path. The warning is part of normal Dockerfile validation behavior.

### 2026-07 — context-root repair

Commit `3c2df0f506b19d6af80dc99c41bc4d6a4df1b145`, merged through PR #6930, corrected root-source matching such as `COPY . .`.

This adds another preservation requirement: lazy loading must not bypass the special treatment for context-root patterns.

## Current exact source

At `275d6864ff0ce91a06225af5f5b012887bd257cf`:

- Docker ignore patterns are requested near the start of `dispatchStages()` whenever a Docker UI client exists.
- A matcher is created once and placed in every stage's `dispatchOpt`.
- local main-context `COPY` and `ADD` pass that matcher into source validation;
- stage/image copies deliberately do not use it;
- `validateCopySourcePath()` returns early when no matcher exists or exclusions make static determination unsafe;
- finalization constructs or obtains `MainContext()` and assigns it to the mutable context output.

## Updated design problem

The 2022 callback idea remains directionally useful, but the trigger is no longer simply “the converter requested files.” Current conversion may need ignore data for a lint warning before any filesystem operation is executed.

The real trigger is:

> a reachable instruction uses the default main context as a local copy/add source and static ignore validation is applicable.

That is narrower than “any `COPY` or `ADD`” and different from “any main-context consumer.”

A context bind mount needs the main context but does not need `CopyIgnoredFile` validation. Context SBOM scanning also consumes the context for a different reason.

## Consumer classes

| Consumer | Main context required | Ignore matcher required |
|---|---:|---:|
| metadata-only target | no | no |
| unreachable stage local copy | no | no |
| local main-context `COPY` | yes | yes, when statically applicable |
| local main-context `ADD` | yes | yes, when statically applicable |
| `COPY --from=stage` | no default context | no default matcher |
| named-context copy | named input only | not default matcher |
| HTTP/Git `ADD` | no default context | no |
| inline heredoc | no default context | no |
| default-context bind mount | yes | no copy-source lint matcher |
| context SBOM scan | yes | no copy-source lint matcher |
| Dockerfile-specific ignore file | Dockerfile input | reused if precedence selects it |

## Candidate conventions

### Separate two decisions

Do not use one boolean for both:

1. whether default ignore patterns are needed for copy-source validation; and
2. whether the main context is consumed by the result.

The first can be a memoized matcher loader. The second should be represented by explicit graph/context ownership.

### Preserve one matcher identity

When multiple reachable local copies need validation, parse ignore patterns once per Docker UI client/context identity. Multi-platform conversion should not create redundant transfers or divergent parsed matchers.

### Keep source classification local

The decision should be made where a command's source has already been classified as:

- default context;
- stage;
- named context;
- remote source;
- inline source.

Loading patterns before that classification recreates the original eager behavior.

### Do not hide errors for real consumers

When a local copy or default-context bind actually requires the context, missing context, invalid ignore syntax, and transfer failures must remain visible. Laziness applies only to unused inputs.

### Subrequests need explicit contracts

Lint, outline, targets, and convert subrequests may have different needs. A subrequest should not load the main context merely because a full build would, but a lint request that promises `CopyIgnoredFile` diagnostics may legitimately need ignore patterns for reachable local copies.

## Test implications

The current sentinel test proves actual `Walk`/`Open` access and includes positive controls for local copy and context bind.

It does not by itself prove that an unused context is absent from every result/provenance representation if no filesystem method is invoked. A later provenance gate should inspect the exported SLSA predicate or equivalent source capture after the transfer gate passes.

The test sequence should therefore be:

1. no filesystem access for metadata-only target;
2. positive access controls;
3. no context source in provenance for metadata-only target;
4. preserved `CopyIgnoredFile` warnings for used local sources;
5. preserved context-root and exclusion behavior;
6. context-bind and SBOM consumers;
7. multi-platform memoization.

## Evidence boundary

This is source and history analysis. It does not establish whether current unconditional `MainContext()` construction creates an observable source when the mutable context output is never referenced. That question remains a runtime/provenance discriminator rather than a source-only conclusion.

## Authority

No BuildKit issue comment, pull request, review, email, or other canonical-project interaction was created.
