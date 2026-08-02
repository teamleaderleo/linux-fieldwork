# Handoff — UV lockfile requirements diagnostic

Handoff date: 2026-08-02  
State: `ACTIVE — SOURCE HOLD; TWO CONTROLLED RUNS QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

```text
controlled repo: teamleaderleo/uv
base branch: main
base commit: 1da26a68629be6ae5fd7f924a7d49ff54763a7df

source branch: fieldwork/uv-lock-requirements-diagnostic
source head: ba55497fe83ea9bb07c04452f8ba190fa4440a05
internal source PR: #12
source disposition: HOLD / REPAIR

current-source execution PR: #15
carrier head: b794c91c9bf50b2ee28cd588cd44e51eb44c1d09
focused run: 30754710006 — queued at last check
ordinary CI: 30754710091 — queued at last check

parse-first experiment PR: #13
experiment head: f0673123cbabe859c12fe6baacc1fff872060f17
focused run: 30755038821 — queued at last check

canonical UV head checked:
79bbface771210df216b738e9bdc7df95e5a9e6b
```

## Current source result

Head `ba55497...` recognizes:

- exact existing `uv.lock`;
- existing `<complete-script-filename>.lock` when the exact sibling parses as PEP 723;
- native non-UTF-8 script filenames on Unix.

Its tests generate project and script lockfiles through UV's real producers and preserve a `.lock` file beside a non-PEP-723 script.

## Newly discovered source defect

Recognition occurs before `RequirementsTxt::parse_with_cache`.

A valid requirements file named `action.py.lock` is therefore rejected whenever `action.py` is a valid PEP 723 script. The filename indicates possible UV provenance, not actual provenance. The current positive control does not cover this because its sibling is deliberately non-PEP-723.

The source PR body now records this defect and supersedes its earlier internal acceptance.

## Alternative design under test

PR #13 checks out exact source `ba55497...` and applies a runner-local experiment:

- add `RequirementsTxtWithUvLockDiagnostic(PathBuf)`;
- return it from `from_requirements_txt`, which serves ordinary requirements files and requirements-syntax exclusion files;
- parse first;
- replace a parse error with the UV-lock hint only on that variant;
- keep constraints and overrides on `RequirementsTxt` through their separate constructors;
- move the filename helper to the parse layer while preserving native path operations.

Additional tests cover:

- valid same-name requirements collision succeeds;
- missing `uv.lock` still reports `File not found`;
- `-c` retains its original parser error;
- existing project, script, non-UTF-8, and arbitrary `.lock` controls remain.

The complete matrix also records the exclusion-file lane; a direct executable exclusion control is still useful after the first compile/test pass.

## First incomplete step

Inspect run `30755038821` and classify the first non-green step. Then inspect run `30754710006` for the current source generation. Queue state is not evidence of success.

## Acceptance decision

If the parse-first experiment passes:

1. revise source branch #12 to the scoped source-variant design;
2. retain producer-backed and non-UTF-8 tests;
3. add the valid same-name collision, missing path, constraint, and exclusion-file controls;
4. create a clean exact-source execution carrier;
5. rerun formatting, affected-crate compile, and focused tests;
6. review the complete source diff again before changing the hold.

If the experiment fails:

1. identify whether the owner is transformation, formatting, exhaustive enum matching, error conversion, or test expectation;
2. repair only that layer;
3. keep source #12 held until the collision has executable evidence.

## Residual ambiguity

After a requirements parse failure, an invalid arbitrary `<script>.lock` beside a PEP 723 script is indistinguishable from a UV-generated script lock without inspecting the lock contents or storing provenance. The parse-first design intentionally accepts this bounded ambiguity because the file is invalid requirements input either way.

## Tooling cleanup note

An attempted carrier-history cleanup created these empty fork-local branches, all pointing at exact source `ba55497...` and containing no changes:

```text
fieldwork/uv-lock-requirements-diagnostic-exec-clean
fieldwork/uv-lock-requirements-diagnostic-exec-clean-2
fieldwork/uv-lock-requirements-diagnostic-exec-clean-3
fieldwork/uv-lock-requirements-diagnostic-exec-clean-4
fieldwork/uv-lock-requirements-diagnostic-exec-clean-final
fieldwork/uv-lock-requirements-diagnostic-exec-clean-actual
fieldwork/uv-lock-requirements-diagnostic-exec-clean-stop
```

The connector exposes branch creation and ref movement but no ref deletion. These refs should be deleted through an authorized interface with delete-ref support. They contain no source delta and triggered no upstream interaction.

## Publication boundary

The canonical issue has prior implementations and an open overlapping attempt. All current PRs are controlled-fork drafts. Do not open, comment on, or update canonical UV issues or pull requests without explicit authorization and a fresh overlap review.

## Separate follow-up

Keep `astral-sh/uv#16209` as a separate unit. Its BusyBox `realpath --` failure intersects relocatable console scripts and activation scripts, and historical symlink behavior must be preserved. A dedicated investigation packet now exists at `investigations/uv-busybox-relocatable-realpath/`.
