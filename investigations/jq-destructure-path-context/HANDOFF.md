# Handoff — jq destructuring path context

Handoff date: 2026-08-02  
State: `ACTIVE — CONTROLLED FOUR-VARIANT MATRIX QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact source

```text
canonical repository: jqlang/jq
canonical branch: master
canonical commit: 603db3f57741d217ba651e61086b550a72148b83
src/compile.c blob: 80b723c119b45f99c5e847c2a463568eb730f498
tests/jq.test blob: 929c7217999f392d1ac536a39bc2c81456e2e6db
canonical issue: #3128
open equivalent PR: none found
closed prior attempt: #3384
```

## Linux Fieldwork carrier

```text
repository: teamleaderleo/linux-fieldwork
branch: investigation/cross-ecosystem-round-2026-08-02
workflow: .github/workflows/jq-destructure-path-context.yml
registered run: 30759608059
state at handoff update: queued
workspace: investigations/jq-destructure-path-context/
```

Creation and carrier-repair commits:

```text
ffa9307948585b7ea3786dbc24ea53db794eca7a — exact variant patcher
2876c92faf0d03d8dc521ecd10b1e6cf27842d26 — semantic/bytecode probe
de1787dd7c550185bf52e1a95e263c114a18695b — initial workflow
bfe281587523f0a2e446d12cec2c519c3b613069 — investigation record
688eacbf2e0cfb2b968e7878ef13734ee83175f8 — initial handoff
32570b31838f9f9d8a494e435a43b5f59de7cde6 — fix invalid top-level matrix concurrency context
```

The initial workflow did not register because top-level concurrency referenced `matrix.variant`, which is unavailable outside the job matrix. Commit `32570b3...` changed the workflow-level key to the branch ref. GitHub then registered the named matrix run. No jq result exists from the invalid carrier.

## Matrix

```text
baseline
closed-pr-3384
issue-end-pop
issue-pop-end
```

Every row verifies exact source identities, applies only `src/compile.c` logic, builds jq with builtin Oniguruma, runs seventeen semantic cases, retains disassembly, executes Valgrind discriminators, and runs complete `make check`.

## Required classification order

1. Confirm all four jobs checked out `603db3f...` and matched both pinned blobs.
2. Separate setup/build failures from compiler-semantic failures.
3. Require baseline to reproduce the original constant-object error while ordinary path/binding controls pass.
4. Compare exact issue outputs for the three candidate layouts.
5. Reject a layout that merely exits zero but returns the wrong path.
6. Compare nested object/array path components.
7. Compare first/fallback alternation matcher outputs.
8. Check backtracking outputs for missing, duplicated, or corrupted values.
9. Require Valgrind gates to pass.
10. Require complete `make check` to pass before selecting a candidate.
11. Review bytecode to explain the winning/losing difference rather than choosing by output alone.

## First incomplete step

Read every matrix job in run `30759608059`. Retain artifact IDs and digests. Do not infer a candidate from job color alone.

## Selection rule

A source layout is selectable only if it:

- fixes both exact issue forms;
- preserves matcher-derived path components;
- handles non-alternating and alternating matchers;
- preserves ordinary binding/path controls;
- survives backtracking;
- has no Valgrind errors or gated leaks;
- passes jq's complete suite;
- changes only the three intended compiler assembly points.

If no layout satisfies the full matrix, retain the result and map the runtime `SUBEXP_*`/path stack semantics before writing a fifth candidate.

## Evidence boundary

No jq product result has been executed yet from this workspace. Static source and prior-PR review justify the matrix, not a fix claim.

The local container could not resolve `github.com`; all source execution belongs to the hosted workflow.

## Publication boundary

No canonical jq issue comment, pull request, review, email, or maintainer contact is authorized or made. Keep all communication internal until explicit authorization.

## Cleanup state

No local checkout survived the failed clone attempt. Hosted jobs use disposable checkouts and upload bounded artifacts. No service, mount, device, package state, or credential is retained locally.
