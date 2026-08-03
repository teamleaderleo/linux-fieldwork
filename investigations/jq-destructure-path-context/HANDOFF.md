# Handoff — jq destructuring path context

Handoff date: 2026-08-03  
State: `ACTIVE — SINGLE-BINDING SUCCESSOR QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact canonical source

```text
canonical repository: jqlang/jq
canonical branch: master
canonical commit: 603db3f57741d217ba651e61086b550a72148b83
src/compile.c blob: 80b723c119b45f99c5e847c2a463568eb730f498
src/execute.c blob: ced1298764478d565fe9615f83b67171b2f70d53
src/opcode_list.h blob: 85a8a5805f178819158c7a7b285a9c6abf18da0a
tests/jq.test blob: 929c7217999f392d1ac536a39bc2c81456e2e6db
canonical issue: jqlang/jq#3128
open canonical equivalent PR: none found
closed prior attempt: jqlang/jq#3384
```

## Completed evidence

### Four-layout instruction matrix

```text
Linux Fieldwork run: 30759715899
```

```text
baseline
  job 91527946570
  artifact 8839004841
  digest sha256:0aeaa6ef5fc2d589b8443f2ff3806285bcc4bc8ac692768d7dff4f180a49eba0

closed-pr-3384
  job 91527946593
  artifact 8838998184
  digest sha256:fdd831eb6eae95b9a10a250c382278a02c03f352b834e0384bac06c861a583f0

issue-end-pop
  job 91527946594
  artifact 8839387816
  digest sha256:e4c9b6007ad4f3685e5ae692ddf9008976af16f15a9c8b90d52aa0a2d2653e7e

issue-pop-end
  job 91527946545
  artifact 8839419621
  digest sha256:8f1f3258f701791d48f4c31127c04872716f9aadbd0b4f862dcfca8cdbc9c768
```

Do not retry additional `SUBEXP_*`/`POP` arrangements. They cannot separate root validation from path recording.

### Broad dedicated index candidate

```text
controlled PR: teamleaderleo/jq#1
branch: fieldwork/3128-destructure-index-path
head: d28a5898a470fa3ddd56fb4aa58dca23454d6e79
run: 30799807411
job: 91641544586
artifact: 8853313029
digest: sha256:6f5a898b7350cc136f103b90eceac963ae0f5989578f68c464f64da9cc328d16
```

Single-binding contract, Valgrind, complete suite, and ordinary workflows passed. The PR is now `HOLD / REPAIR` because its compiler scope was disproved by the next review.

### Multi-binding review

```text
closed execution PR: teamleaderleo/jq#3
branch: research/3128-destructure-path-semantics
head: ad2be4dabe0e27f31fb1ef9b45a5093cb77a0e31
run: 30849176240
job: 91804761928
artifact: 8871057969
digest: sha256:81ccf773c5f339e9b8670af139151e50bfbfbe029dd570d7e8faba3512287274
```

The broad opcode fabricated cumulative sibling paths:

```text
["a","b"]
["x","a","b"]
[1,0]
```

Sibling matchers index the same retained container and must not be interpreted as one nested path. Other sibling/body combinations fail depending on matcher order and returned binding.

Pinned gojq was an independent comparator, not an oracle. Two setpath rows are excluded because the supplement used the wrong arity.

The broader matcher-path-rebase branch `teamleaderleo/jq#2` also remains closed without result and must not be reopened unless a future finding specifically requires runtime-state ownership.

## Current controlled successor

```text
repository: teamleaderleo/jq
base branch: fieldwork/3128-destructure-index-path
branch: experiment/3128-single-binding-scope
head: 37cd514ad0b40ba857168966af80854453e42da5
internal draft PR: #4
focused workflow: Fieldwork jq single-binding destructure path
focused run: 30852982042
focused state at handoff: queued
```

Ordinary exact-head runs:

```text
CI:         30852981456 — queued
Oniguruma:  30852981509 — queued
Valgrind:   30852981523 — queued
Decnum:     30852981574 — queued
```

## Successor design

Matcher builders emit `INDEX_DESTRUCTURE` only for matcher-owned index operations. Before each complete alternative is bound:

- count unbound `STOREV`/`STOREVN` instructions recursively;
- exactly one binding keeps the special index;
- zero or multiple bindings restore matcher-owned special indexes to ordinary `INDEX`;
- scope alternative branches independently;
- leave indexes inside dynamic key expressions untouched.

The runtime opcode is unchanged from the first candidate. Only its compiler scope changes.

## Execution contract

The workflow:

1. verifies exact product blobs and five-file carrier fence;
2. builds canonical jq before applying any product patch;
3. records exact status/stdout/stderr for 24 multi-binding programs;
4. applies the three-file candidate;
5. rebuilds incrementally;
6. reruns the original single-binding semantic probe;
7. requires every multi-binding observation to be byte-identical to baseline;
8. requires `INDEX_DESTRUCTURE` in single-binding disassembly and absent from sibling disassembly;
9. runs Valgrind across single and multi scopes;
10. runs complete `make check`;
11. uploads exact baseline/candidate identities and patch.

## First incomplete step

Read focused run `30852982042` in this order:

1. exact product/carrier fence and Python compilation;
2. canonical build and baseline-recording phase;
3. source transformation and exact three-file product fence;
4. candidate rebuild;
5. original single-binding probe;
6. first canonical multi-binding divergence, if any;
7. disassembly scope gates;
8. first Valgrind failure;
9. complete suite;
10. artifact ID/digest and ordinary workflow status.

If green, review the resulting product patch for:

- dynamic object-key expressions containing their own bindings;
- repeated uses of the same variable name in one pattern;
- nested alternatives;
- binding-count recursion into subfunctions.

Promote no clean source branch until that complete review is retained.

## Publication and cleanup boundary

All source patches and builds are confined to controlled disposable runners. No canonical jq contact or mutation is authorized or made.
