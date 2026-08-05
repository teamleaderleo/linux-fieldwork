# Round 003 work checkpoint 05

Date: 2026-08-05  
Worker or variant: `LF-R05`  
External contact authorized: `false`

## Current decision table

| Lane | Current decision | Exact controlled state | Evidence boundary |
| --- | --- | --- | --- |
| uv workspace member index authority, #20678 | `ACTIVE — PUBLIC-CANDIDATE MATRIX EXECUTING` | `teamleaderleo/uv#35`, head `01cf394c470473f98371a86dcf0e11250f9ec1d5`; focused run `30973614465` | exact source-base identity repaired; build/matrix still running |
| uv stub-only initializer, #19663 / #20734 | `ACTIVE — OLD CANDIDATE FOCUSED-GREEN; CURRENT-MAIN RESTACK EXECUTING` | historical scoped PR `teamleaderleo/uv#30`; current-main PR `teamleaderleo/uv#41`, head `ec32d87131f97c07e2f67b0b210d8d0aecd25e0a` | old exact candidate passed 16 cases; current main not yet classified |
| Biome mutable member truthiness, #11174 | `REPRODUCED — SCOPED DIRECT-OBJECT CANDIDATE REPAIR EXECUTING` | losing run `30946698463` / job `92118354511`; candidate `teamleaderleo/biome#4`, head `547603299f9268c92afdb06c92cc3ee069efbffc` before transformer repair | four false positives reproduced; candidate excludes generic `useRef` cases |
| Biome Git-internal watcher paths, #11110 | `ACTIVE — CLEAN CURRENT-BASE LOSING TEST EXECUTING` | superseded PR #3 closed; clean PR `teamleaderleo/biome#5`, head `45ced00cb68bd6a7471735205f6b500aa15f8d0b`; run `30973738984` | stable-feature test selected; no result yet |
| wgpu BLAS lock order, #9981 | `STOP — EXISTING PUBLIC CARRIER` | retained internal provenance only | public draft #9479 owns exact correction |
| safetensors s390x TensorSpec byte order, #812 | `HOLD — NEEDS EXECUTABLE SOURCE ENVIRONMENT` | raw-payload matrix retained | no controlled safetensors fork or current TensorSpec runtime available |

## Biome #11174: exact product reproduction

Focused run `30946698463`, job `92118354511`, reached the intended diagnostic assertion after the fixture-contract repair.

Exact current source emitted four unexpected diagnostics:

1. direct object property initialized with `false` — reported always falsy;
2. `useRef<boolean>(false)` property — reported always falsy;
3. `useRef<number>(0)` property — reported always falsy;
4. direct object property initialized with `true` — reported always truthy.

Ten sibling focused specifications passed. This is a product reproduction, not a fixture, workflow, or feature-selection failure.

The first direct-object candidate run failed before product execution because its stored patch artifact was malformed. The invalid patch was removed. The current carrier uses a fail-closed source transformer with exact anchors and writes the candidate fixture directly.

Candidate scope remains intentionally partial:

- direct mutable boolean, number, and string object-property literals widen;
- `as const` inference remains literal;
- nested direct object members are covered;
- generic-returned properties such as `useRef<T>()` remain unresolved.

A green candidate run must be classified as partial candidate validation, not issue completion.

## uv stubs: exact old-candidate backend boundary established

Focused workflow `30946811586`, job `92118723892`, completed successfully on exact public candidate `082af3c5eb95bbc0f0173ebc67965919c14e1a0a` with the scoped one-file transformation.

Completed:

- exact source/blob and one-file product fence;
- Rust formatting and `cargo check -p uv`;
- native init controls;
- uv binary build;
- 16 generated-project builds: application and library across uv_build, Hatch, Flit, PDM, Poetry, setuptools, Maturin, and Scikit-build.

Observed contract:

- uv_build application/library: hyphenated `src/foo-stubs/__init__.pyi`, no runtime script, build succeeds;
- every non-uv backend: underscore `src/foo_stubs/__init__.py`, build succeeds;
- non-uv applications retain the runtime script; non-uv libraries do not add one.

Artifact `8906912533`, digest `sha256:b72953a59f96b7635d34324302b93e07fcc5205781d6a4aafef7966515d1b9a4`.

Repository CI `30946812859` is not green. Current formatter tools reject unchanged historical documentation in the old candidate base. Ruff also rejected the carrier helper; that helper was formatted separately. The old-base documentation drift is not product evidence and was not rewritten.

Current public uv main `49e2fc5c821bb69a528308a036b17446bb5ab5a6` refactored project initialization and still lacks stub-only initializer behavior. Controlled PR #41 restacks the same scoped contract against exact `init.rs` blob `c9dc1368f3c1f5f6f41098fb22a918cd3a926b4f` with a fresh source transformer and the same 16-case matrix.

## uv #20678: exact ancestry repaired

Public PR #20922 advertised base `92b7185783b56e8ad1dbe0bb7600432708f2c9fb`, but its actual source merge base is `4518994c9c8e3975c0f35db49841f7f5a6d0a577`.

The first internal run failed before build because the carrier conflated PR base and source ancestry. The current workflow records both identities, builds the true source base and exact candidate, and retains the public merge-context relationship separately.

The distinguishing sibling case remains:

> a dependency belongs to one member while an unrelated sibling declares the only usable index.

Candidate success in that case establishes workspace-global member-index search authority. It does not by itself decide whether that authority is desirable.

## Biome #11110: conflicted carrier replaced

Historical PR #3 diverged from the controlled CI base at the workflow file and stopped receiving a generated merge ref. It is closed as provenance for the first empty-feature failure.

Clean PR #5 restacks exactly two files onto current `ci/biome-focused-base`:

- `should_ignore_git_internal_events` with `.git/index.lock` and an ordinary source path in one batch;
- the shipped-feature command:

```sh
cargo test -p biome_service --features stable should_ignore_git_internal_events -- --nocapture
```

A pass requires targeted Git-internal filtering while retaining ordinary project activity.

## First incomplete gates

1. Classify uv PR #35 source-base/candidate matrix and sibling-index authority.
2. Classify uv PR #41 current-main stubs transformer, native control, and 16-case matrix.
3. Classify Biome PR #4 after the exact-anchor transformer reaches formatting, compilation, and analyzer assertions.
4. Classify Biome PR #5 after the stable-feature watcher test runs.
5. Preserve every carrier-owned failure separately and repair only the first owning layer.
6. Do not treat old-base broad formatter drift as current-main product evidence.
7. Continue broad overlap refresh before opening new implementation branches.

## Authority

All writes and hosted execution remain inside controlled `teamleaderleo/*` repositories. No canonical-upstream issue, pull request, comment, review, reaction, email, or other contact occurred.
