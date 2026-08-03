# jq destructuring path context

State: `ACTIVE — DEDICATED INDEX CANDIDATE GREEN; MULTI-BINDING REVIEW QUEUED`  
Canonical issue: `jqlang/jq#3128`  
External contact authorized: `false`  
External contact made: `none`

## Question

How should destructuring matchers participate in `path(...)` when the value on the left of `as` is produced separately from the current path root?

The required behavior is narrower than a general subexpression:

- evaluate the value being destructured without adding its traversal to the path;
- allow object and array matcher indexes to become path components;
- preserve normal path advancement through a bound value;
- retain the final-result integrity check;
- preserve ordinary destructuring, alternation, backtracking, assignments, and memory invariants.

## Exact canonical source

```text
repository: jqlang/jq
branch: master
commit: 603db3f57741d217ba651e61086b550a72148b83
src/compile.c blob: 80b723c119b45f99c5e847c2a463568eb730f498
src/execute.c blob: ced1298764478d565fe9615f83b67171b2f70d53
src/opcode_list.h blob: 85a8a5805f178819158c7a7b285a9c6abf18da0a
tests/jq.test blob: 929c7217999f392d1ac536a39bc2c81456e2e6db
```

No open canonical pull request was found. Closed PR `jqlang/jq#3384` attempted an instruction-layout repair and was withdrawn after incorrect results.

## Completed four-layout matrix

Linux Fieldwork run `30759715899` executed exact canonical source under four compiler layouts:

```text
baseline          job 91527946570  artifact 8839004841
closed-pr-3384    job 91527946593  artifact 8838998184
issue-end-pop     job 91527946594  artifact 8839387816
issue-pop-end     job 91527946545  artifact 8839419621
```

GitHub artifact digests:

```text
baseline          sha256:0aeaa6ef5fc2d589b8443f2ff3806285bcc4bc8ac692768d7dff4f180a49eba0
closed-pr-3384    sha256:fdd831eb6eae95b9a10a250c382278a02c03f352b834e0384bac06c861a583f0
issue-end-pop     sha256:e4c9b6007ad4f3685e5ae692ddf9008976af16f15a9c8b90d52aa0a2d2653e7e
issue-pop-end     sha256:8f1f3258f701791d48f4c31127c04872716f9aadbd0b4f862dcfca8cdbc9c768
```

Classification:

- **baseline:** reproduces the constant-value invalid-path error and passes complete `make check`;
- **closed PR #3384:** simple paths appear repaired, but nested and array bindings become `null`, alternation fails, and the full suite fails;
- **delayed `SUBEXP_END`, then `POP`:** bindings survive, but every matcher path is suppressed to `[]`; full suite fails;
- **`POP`, then delayed `SUBEXP_END`:** corrupts stack shape and aborts with assertions; full suite fails.

`subexp_nest` couples two behaviors that this problem needs to separate: it disables the mismatched-root check and also disables path recording/value advancement. Moving existing `SUBEXP_*` and `POP` operations cannot express the required semantics.

Complete interpretation: `research/rounds/2026-08-02-cross-ecosystem/jq-3128-four-layout-result.md`.

## Green controlled candidate

Controlled fork:

```text
repository: teamleaderleo/jq
branch: fieldwork/3128-destructure-index-path
head: d28a5898a470fa3ddd56fb4aa58dca23454d6e79
internal draft PR: teamleaderleo/jq#1
```

The branch commits test infrastructure only. Its disposable runner patch introduces `INDEX_DESTRUCTURE`, emitted only by object and array destructuring matchers. The opcode skips only `path_intact()`'s requirement that the matcher container equal the current `value_at_path`; it retains ordinary `path_append()` behavior, including advancement to the bound value for later traversal.

Focused result:

```text
run: 30799807411
job: 91641544586
conclusion: success
artifact: 8853313029
artifact digest: sha256:6f5a898b7350cc136f103b90eceac963ae0f5989578f68c464f64da9cc328d16
```

Passed gates:

- exact issue forms;
- nested object and array matchers;
- object, array, and scalar `?//` alternatives;
- source backtracking;
- traversal through bound values;
- expected-invalid non-null final-result controls;
- ordinary object, nested, and array bindings;
- ordinary paths;
- `setpath` consumer;
- Valgrind;
- complete `make check`.

Ordinary fork workflows on exact head all passed:

```text
CI          30799807372
Decnum      30799807121
Oniguruma   30799807421
Valgrind    30799807190
```

The exact disposable product diff changes three files:

```text
src/compile.c
src/execute.c
src/opcode_list.h
```

No clean product source branch is promoted yet.

## Self-review and residual semantic gate

A later, broader matcher-path-rebase experiment was opened as `teamleaderleo/jq#2`, then closed without merge or result after review showed that #1 was narrower and already green. No duplicate candidate remains active.

The leading candidate still needs one semantic review before promotion: destructuring patterns can bind sibling fields or array elements while jq paths are linear. A green single-binding matrix does not by itself define how patterns such as `{$a,$b}` should interact with `path`, bound-variable traversal, `reduce`, `foreach`, or `setpath`.

Execution-only supplement:

```text
repository: teamleaderleo/jq
branch: research/3128-destructure-path-semantics
head: ad2be4dabe0e27f31fb1ef9b45a5093cb77a0e31
internal draft PR: teamleaderleo/jq#3
focused comparison run: 30849176240 — queued at last check
```

The supplement reruns the green candidate contract and compares candidate behavior with pinned `itchyny/gojq@2e210b5c28122b106d4cd1fade3ac9dad0482026` across sibling object/array patterns, renamed and reversed bindings, nested siblings, source-path exclusion, second-sibling traversal, alternatives, backtracking, `reduce`, `foreach`, and assignment round-trips. gojq is retained as an independent comparator, not treated automatically as the normative jq contract.

## Decision boundary

Promote a clean source candidate only if the multi-binding review establishes a coherent path rule and does not expose artificial sibling-to-nested path construction. If a divergence appears, retain exact candidate and comparator outputs and map the compiler/runtime ownership before changing the opcode.

## Cleanup and publication boundary

All execution uses disposable hosted runners. No local checkout, service, device, mount, credential, or canonical repository state is retained. No canonical jq comment, pull request, review, reaction, email, or maintainer contact is authorized or made.
