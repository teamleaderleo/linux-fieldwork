# Handoff — jq destructuring path context

Handoff date: 2026-08-03  
State: `ACTIVE — INDEX_DESTRUCTURE GREEN; MULTI-BINDING COMPARISON QUEUED`  
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
open equivalent canonical PR: none found
closed prior attempt: jqlang/jq#3384
```

## Completed Linux Fieldwork matrix

```text
repository: teamleaderleo/linux-fieldwork
branch: investigation/cross-ecosystem-round-2026-08-02
workflow: .github/workflows/jq-destructure-path-context.yml
run: 30759715899
```

All four rows checked out exact source, built, ran the semantic/disassembly probe, ran Valgrind, uploaded evidence, and ran complete `make check`.

```text
baseline
  job: 91527946570
  artifact: 8839004841
  digest: sha256:0aeaa6ef5fc2d589b8443f2ff3806285bcc4bc8ac692768d7dff4f180a49eba0
  result: issue reproduced; full suite passes

closed-pr-3384
  job: 91527946593
  artifact: 8838998184
  digest: sha256:fdd831eb6eae95b9a10a250c382278a02c03f352b834e0384bac06c861a583f0
  result: simple output repaired; nested/array bindings become null; alternation and suite fail

issue-end-pop
  job: 91527946594
  artifact: 8839387816
  digest: sha256:e4c9b6007ad4f3685e5ae692ddf9008976af16f15a9c8b90d52aa0a2d2653e7e
  result: bindings survive; all matcher paths become []; suite fails

issue-pop-end
  job: 91527946545
  artifact: 8839419621
  digest: sha256:8f1f3258f701791d48f4c31127c04872716f9aadbd0b4f862dcfca8cdbc9c768
  result: stack assertions and status 134 aborts; suite fails
```

Do not retry additional `SUBEXP_BEGIN`/`SUBEXP_END`/`POP` permutations. The matrix proves that `subexp_nest` suppresses both root validation and path recording, while the desired behavior needs to suppress only the mismatched-root check.

## Leading controlled candidate

```text
controlled repository: teamleaderleo/jq
branch: fieldwork/3128-destructure-index-path
head: d28a5898a470fa3ddd56fb4aa58dca23454d6e79
internal draft PR: #1
focused workflow: Fieldwork jq destructure path candidate
run: 30799807411
job: 91641544586
conclusion: success
artifact: 8853313029
digest: sha256:6f5a898b7350cc136f103b90eceac963ae0f5989578f68c464f64da9cc328d16
```

Ordinary exact-head workflows:

```text
CI:         30799807372 — success
Decnum:     30799807121 — success
Oniguruma:  30799807421 — success
Valgrind:   30799807190 — success
```

The branch commits carrier files only. The disposable product patch adds `INDEX_DESTRUCTURE` and emits it only for object and array destructuring matchers. It bypasses `path_intact()` for that index operation but keeps ordinary `path_append()` and `value_at_path` advancement. Exact issue, nested/array, alternation, backtracking, bound traversal, invalid-result, ordinary binding/path, `setpath`, Valgrind, and complete-suite gates passed.

## Superseded self-review branch

```text
teamleaderleo/jq#2
branch: experiment/3128-destructure-path-rebase
head: 0ae49de7b14142b6ca63830a16a638792c428ddb
state: closed without merge and without product result
```

It proposed a broader matcher-level `value_at_path` save/restore scope. It was closed after review showed #1 had already executed a narrower, green design. Do not reopen it unless the dedicated index operation is disproved and the exact reason requires broader state ownership.

## Current first incomplete step

```text
controlled repository: teamleaderleo/jq
branch: research/3128-destructure-path-semantics
head: ad2be4dabe0e27f31fb1ef9b45a5093cb77a0e31
internal draft PR: #3
comparison run: 30849176240
state at this handoff: queued
pinned comparator: itchyny/gojq@2e210b5c28122b106d4cd1fade3ac9dad0482026
```

When run `30849176240` completes:

1. verify the exact jq candidate contract reran successfully;
2. retain artifact ID/digest and exact jq/gojq binary identities;
3. classify sibling object and array patterns separately from nested patterns;
4. inspect body uses of first binding, second binding, comma/backtracking, and traversal through the second binding;
5. inspect `reduce` and `foreach` results;
6. inspect both `setpath` observations;
7. treat gojq as an independent comparator, not an automatic oracle;
8. determine whether `INDEX_DESTRUCTURE` constructs artificial nested paths from sibling indexes;
9. promote no product source until that rule is explicit.

The branch also triggers the existing candidate, CI, Decnum, Oniguruma, and Valgrind workflows. Their current queued run IDs are:

```text
candidate:  30849175954
CI:         30849176092
comparison: 30849176240
Decnum:     30849176195
Valgrind:   30849176294
Oniguruma:  30849176393
```

## Publication boundary

No canonical jq issue comment, pull request, review, reaction, email, or maintainer contact is authorized or made.

## Cleanup state

All builds and source patches are confined to disposable hosted runners. No local checkout or external state is retained.
