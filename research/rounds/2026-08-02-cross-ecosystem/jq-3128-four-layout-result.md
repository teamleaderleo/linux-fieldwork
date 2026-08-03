# jq #3128 four-layout and dedicated-index result

Date: 2026-08-03  
State: `FOUR-LAYOUT MATRIX COMPLETE; DEDICATED INDEX GREEN; MULTI-BINDING REVIEW ACTIVE`  
External contact authorized: `false`  
External contact made: `none`

## Exact canonical source

```text
jqlang/jq@603db3f57741d217ba651e61086b550a72148b83
src/compile.c:      80b723c119b45f99c5e847c2a463568eb730f498
src/execute.c:      ced1298764478d565fe9615f83b67171b2f70d53
src/opcode_list.h:  85a8a5805f178819158c7a7b285a9c6abf18da0a
tests/jq.test:      929c7217999f392d1ac536a39bc2c81456e2e6db
```

## Four-layout run

```text
Linux Fieldwork run: 30759715899
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

### Canonical baseline

The baseline passes complete `make check` and reproduces the issue. Constant values on the left of a destructuring `as` do not match the current `value_at_path`, so the first matcher index raises the path-integrity error. The dot/null control happens to remain path-compatible.

### Closed PR #3384 layout

The closed PR's layout repairs simple object, nested, and array outputs, but it is not viable:

- alternation still raises invalid-path errors;
- ordinary nested and array bindings become `null` instead of `1`;
- complete `make check` fails.

The layout discards or reorders data needed by normal matcher/body execution. Its apparently correct simple outputs are not sufficient evidence.

### Delayed `SUBEXP_END`, then `POP`

Running the matcher while `subexp_nest` remains nonzero preserves bindings but suppresses all matcher path components. Object, nested, and array paths become `[]`; complete `make check` fails.

### `POP`, then delayed `SUBEXP_END`

This ordering violates the data-stack contract and aborts with status 134. Observed assertions include:

```text
src/execute.c:981: jq_next: Assertion `jq->stk_top == frame_current(jq)->retdata' failed.
src/execute.c:176: stack_pop: Assertion `jv_is_valid(val)' failed.
```

Six of nine jq test groups fail. The first Valgrind classifier did not treat ordinary abort 134 as a memory gate failure, so no memory-safety inference is taken from that step.

## Runtime finding

`subexp_nest` couples two behaviors:

1. `path_intact()` stops requiring the indexed container to equal `value_at_path`;
2. `path_append()` stops recording the key/index and stops advancing `value_at_path`.

Destructuring inside `path()` needs a third index behavior:

- index a separately produced matcher container without the ordinary mismatched-root rejection;
- still append the matcher key/index;
- still advance `value_at_path` to the matched value, so later traversal through a bound value works;
- retain the normal final-result integrity check.

Existing `SUBEXP_BEGIN`, `SUBEXP_END`, and `POP` arrangements cannot express that split.

## Dedicated index experiment

```text
repository: teamleaderleo/jq
branch: fieldwork/3128-destructure-index-path
head: d28a5898a470fa3ddd56fb4aa58dca23454d6e79
internal draft PR: teamleaderleo/jq#1
```

The branch commits four carrier files and no jq product source. Its disposable patch adds `INDEX_DESTRUCTURE` to `src/opcode_list.h`, emits it from object and array destructuring matchers in `src/compile.c`, and handles it alongside `INDEX` in `src/execute.c`. The only semantic difference from `INDEX` is that the initial `path_intact()` container-equality check is skipped.

Focused receipt:

```text
run: 30799807411
job: 91641544586
conclusion: success
artifact: 8853313029
artifact digest: sha256:6f5a898b7350cc136f103b90eceac963ae0f5989578f68c464f64da9cc328d16
```

Passed:

- exact issue forms;
- nested object and array matchers;
- object, array, and scalar alternatives;
- source backtracking;
- traversal through a bound value;
- expected-invalid non-null final-result controls;
- ordinary bindings and paths;
- `setpath` from the returned path;
- Valgrind;
- complete `make check`.

Ordinary exact-head workflows also passed:

```text
CI          30799807372
Decnum      30799807121
Oniguruma   30799807421
Valgrind    30799807190
```

The exact disposable product diff changes only:

```text
src/compile.c
src/execute.c
src/opcode_list.h
```

## Self-review and remaining boundary

A broader matcher-level path-rebase experiment was opened as `teamleaderleo/jq#2`, then closed without merge or product result after review showed that the dedicated index operation was narrower and already fully executed.

The green candidate is not yet promoted because multi-binding patterns remain under-specified. Object and array destructuring can bind siblings while jq paths are linear. The existing focused matrix primarily uses one binding per successful branch.

Current supplement:

```text
repository: teamleaderleo/jq
branch: research/3128-destructure-path-semantics
head: ad2be4dabe0e27f31fb1ef9b45a5093cb77a0e31
internal draft PR: teamleaderleo/jq#3
comparison run: 30849176240 — queued at last check
pinned comparator: itchyny/gojq@2e210b5c28122b106d4cd1fade3ac9dad0482026
```

It compares sibling object/array bindings, renamed/reversed patterns, nested siblings, source-path exclusion, second-binding traversal, alternatives, backtracking, `reduce`, `foreach`, and `setpath` round-trips. gojq is an independent comparator, not automatically a normative oracle.

## Promotion rule

Promote a clean product source branch only after the multi-binding result establishes a coherent rule and the candidate does not manufacture artificial nested paths from sibling matcher indexes. If that gate fails, retain the exact divergence and change the compiler/runtime design rather than weakening the test.

## Publication boundary

No canonical jq issue comment, pull request, review, reaction, email, or maintainer contact is authorized or made.
