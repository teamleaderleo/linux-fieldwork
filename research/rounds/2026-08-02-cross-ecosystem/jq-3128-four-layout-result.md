# jq #3128 four-layout result

Date: 2026-08-03  
State: `COMPLETE NEGATIVE MATRIX — DEDICATED INDEX EXPERIMENT ACTIVE`  
External contact authorized: `false`  
External contact made: `none`

## Exact run

```text
Linux Fieldwork run: 30759715899
source: jqlang/jq@603db3f57741d217ba651e61086b550a72148b83
src/compile.c blob: 80b723c119b45f99c5e847c2a463568eb730f498
tests/jq.test blob: 929c7217999f392d1ac536a39bc2c81456e2e6db
```

Artifacts:

```text
baseline
  job: 91527946570
  artifact: 8839004841
  digest: sha256:0aeaa6ef5fc2d589b8443f2ff3806285bcc4bc8ac692768d7dff4f180a49eba0
closed-pr-3384
  job: 91527946593
  artifact: 8838998184
  digest: sha256:fdd831eb6eae95b9a10a250c382278a02c03f352b834e0384bac06c861a583f0
issue-end-pop
  job: 91527946594
  artifact: 8839387816
  digest: sha256:e4c9b6007ad4f3685e5ae692ddf9008976af16f15a9c8b90d52aa0a2d2653e7e
issue-pop-end
  job: 91527946545
  artifact: 8839419621
  digest: sha256:8f1f3258f701791d48f4c31127c04872716f9aadbd0b4f862dcfca8cdbc9c768
```

## Classification

### Canonical baseline

The baseline passes complete `make check` and reproduces the issue. A destructuring matcher succeeds only when the value being destructured remains identical to `value_at_path`. Constant object and array expressions therefore fail the path-integrity check, while the dot/null control succeeds.

### Closed PR #3384 layout

This layout wraps the destructured expression in an additional subexpression and appends `POP` after matcher execution.

It repairs the simple constant object, nested object, and array shapes, but it is not viable:

- alternation still raises invalid-path errors;
- ordinary nested and array destructuring bindings become `null` instead of `1`;
- complete `make check` fails.

The extra `POP` discards data needed by ordinary matcher/body execution. The layout is mechanically close to the report but semantically wrong.

### Delayed `SUBEXP_END`, then `POP`

This layout runs matchers while `subexp_nest` remains nonzero. Every matcher path becomes the empty path `[]`, including nested and array cases. Ordinary bindings survive, but complete `make check` fails.

This proves that existing subexpression state suppresses both path validation and path component recording; it cannot represent the desired third behavior.

### `POP`, then delayed `SUBEXP_END`

This layout is unsafe. Every destructuring/path case aborts with status 134. Observed assertions include:

```text
src/execute.c:981: jq_next: Assertion `jq->stk_top == frame_current(jq)->retdata' failed.
src/execute.c:176: stack_pop: Assertion `jv_is_valid(val)' failed.
```

Six of nine jq test groups fail. The original Valgrind gate only treated statuses 97 and 124 as failures, so its green step was a false negative for ordinary abort status 134. No memory-safety claim is retained from that gate.

## Runtime finding

`subexp_nest` has two coupled effects:

1. `path_intact()` stops requiring the indexed value to equal `value_at_path`;
2. `path_append()` stops recording the key/index and stops advancing `value_at_path`.

Destructuring inside `path()` needs a distinct operation:

- index the separately produced value for binding;
- do not require that value to equal the current path root;
- record the matcher component;
- do not replace `value_at_path`, because the expression to the right of `as` still receives the original input.

Moving `SUBEXP_BEGIN`, `SUBEXP_END`, and `POP` cannot express that contract without losing paths or corrupting the stack.

## Controlled fork experiment

```text
repository: teamleaderleo/jq
branch: fieldwork/3128-destructure-index-path
head: 2b1f443fffbb1e629cc53ebef8884fcaa81a5a02
internal draft PR: teamleaderleo/jq#1
focused run: 30799146702 — queued at record creation
ordinary runs: CI 30799146647; oniguruma 30799146694; decnum 30799146753; valgrind 30799146918
```

The branch commits test infrastructure only. Its disposable runner patch introduces `INDEX_DESTRUCTURE`, emitted only by object and array destructuring matchers. The semantic matrix includes null and non-null roots, nested and array matchers, alternation, backtracking, ordinary bindings, plain paths, and a `setpath` consumer. Product source is not committed unless this experiment passes its focused gate, jq's complete suite, and ordinary workflows.

## First incomplete step

Classify focused run `30799146702` by the first failing step. If the semantic probe passes, retain the exact patch, disassembly, source hashes, artifact digest, full-suite status, and ordinary workflow results. If it fails, use the first incorrect case to decide whether matcher components should preserve or transform `value_at_path`; do not return to blind `SUBEXP` permutations.

## Publication boundary

No canonical jq issue comment, pull request, review, reaction, or maintainer contact is authorized or made.
