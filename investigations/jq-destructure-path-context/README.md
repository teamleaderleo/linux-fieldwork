# jq destructuring path context

State: `ACTIVE — BROAD INDEX CANDIDATE HELD; SINGLE-BINDING SUCCESSOR QUEUED`  
Canonical issue: `jqlang/jq#3128`  
External contact authorized: `false`  
External contact made: `none`

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

No open canonical equivalent PR was found. Closed PR `jqlang/jq#3384` was withdrawn after incorrect results.

## Completed instruction-layout matrix

Linux Fieldwork run `30759715899` proved that rearranging existing `SUBEXP_BEGIN`, `SUBEXP_END`, and `POP` operations cannot express the required behavior:

- canonical source reproduces the constant-value path error and passes the full suite;
- the closed PR layout repairs simple output but breaks nested/array bindings and alternatives;
- delaying `SUBEXP_END` preserves bindings but erases all matcher path components;
- moving `POP` first corrupts stack state and aborts.

Exact jobs, artifacts, and digests remain in `jq-3128-four-layout-result.md` and this workspace's handoff.

## First dedicated index candidate — green but over-broad

```text
repository: teamleaderleo/jq
branch: fieldwork/3128-destructure-index-path
head: d28a5898a470fa3ddd56fb4aa58dca23454d6e79
internal draft PR: teamleaderleo/jq#1
focused run: 30799807411
job: 91641544586
artifact: 8853313029
digest: sha256:6f5a898b7350cc136f103b90eceac963ae0f5989578f68c464f64da9cc328d16
```

The disposable three-file patch introduced `INDEX_DESTRUCTURE`, which skips only the ordinary requirement that the matcher container equal current `value_at_path`; normal path recording and bound-value advancement remain in place.

The exact issue, nested/array, alternatives, backtracking, bound traversal, invalid-result controls, ordinary bindings/paths, `setpath`, Valgrind, complete `make check`, and ordinary fork workflows all passed.

## Completed multi-binding review

Execution-only supplement `teamleaderleo/jq#3` completed and was closed without merge after evidence transfer:

```text
run: 30849176240
job: 91804761928
artifact: 8871057969
digest: sha256:81ccf773c5f339e9b8670af139151e50bfbfbe029dd570d7e8faba3512287274
pinned comparator: itchyny/gojq@2e210b5c28122b106d4cd1fade3ac9dad0482026
```

The broad candidate is not promotable. Sibling matchers each index the same retained container, but every `INDEX_DESTRUCTURE` advanced one linear path from the prior sibling. This manufactured order-dependent paths such as:

```text
{} as {$a,$b} | .                    -> ["a","b"]
{x:{a:1,b:2}} as {x:{$a,$b}} | $b   -> ["x","a","b"]
[10,20] as [$a,$b] | $a              -> [1,0]
```

Other sibling/body combinations fail final path integrity depending on which binding is returned. That is not a coherent multi-binding contract.

Pinned gojq generally suppresses matcher-path construction and therefore differs even on the issue's single-binding expectation. It was an independent comparator, not a normative oracle.

Two `setpath` rows from the comparison are excluded because the supplement accidentally used the wrong arity; both implementations correctly rejected them during compilation.

`teamleaderleo/jq#1` is now explicitly `HOLD / REPAIR`.

## Current single-binding successor

```text
repository: teamleaderleo/jq
base branch: fieldwork/3128-destructure-index-path
branch: experiment/3128-single-binding-scope
head: 32a2d3fcbb374e74ea7545462848005ecb7be90a
internal draft PR: teamleaderleo/jq#4
focused run: 30853405404 — queued at last check
ordinary workflows:
  CI: 30853405244
  Oniguruma: 30853405626
  Valgrind: 30853405101
  Decnum: 30853405331
```

The successor keeps the same narrow runtime opcode but scopes it in the compiler:

1. matcher builders tag only their own generated indexes;
2. each complete alternative counts unbound `STOREV`/`STOREVN` instructions;
3. exactly one binding retains `INDEX_DESTRUCTURE`;
4. zero or multiple bindings restore the matcher indexes to canonical `INDEX`;
5. alternative branches are scoped independently;
6. dynamic key-expression indexes remain ordinary.

The workflow first builds exact canonical jq and records status/stdout/stderr for 26 canonical-preservation programs. The expanded matrix includes sibling object/array bindings, repeated binding sites, dynamic-key expressions with local bindings, alternatives, backtracking, `reduce`, `foreach`, and valid `setpath` consumers.

After applying the candidate, it requires:

- the original single-binding contract plus a dynamic-key single-binding control and nested alternative to pass;
- every canonical-preservation result to remain byte-identical to canonical jq;
- special opcode present in single-binding disassembly and absent from sibling disassembly;
- Valgrind for both scopes;
- complete `make check`.

The baseline build records canonical behavior before any patch. Because runner Autotools can rewrite tracked generated files, the workflow then resets tracked files to exact HEAD, re-verifies all pinned product blobs, and only then applies and fences the three-file candidate.

## Decision boundary

A clean source candidate may be promoted only if run `30853405404` passes every gate and complete review confirms that binding-count recursion does not misclassify additional dynamic-key or repeated-binding forms. Otherwise retain the exact first divergence and revise the compiler boundary rather than weakening canonical-preservation tests.

## Publication and cleanup boundary

All source transformations execute in disposable controlled-fork runners. No canonical issue comment, pull request, review, reaction, email, or maintainer contact is authorized or made.
