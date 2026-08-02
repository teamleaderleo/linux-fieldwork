# jq destructuring path context

State: `ACTIVE — CONTROLLED FOUR-VARIANT MATRIX QUEUED`  
Canonical issue: `jqlang/jq#3128`  
External contact authorized: `false`  
External contact made: `none`

## Question

Which compiler layout correctly prevents the value being destructured from contaminating `path(...)`, while preserving matcher traversal, alternation behavior, ordinary bindings, backtracking, and jq's stack/memory invariants?

## Current canonical source

```text
repository: jqlang/jq
branch: master
commit: 603db3f57741d217ba651e61086b550a72148b83
src/compile.c blob: 80b723c119b45f99c5e847c2a463568eb730f498
tests/jq.test blob: 929c7217999f392d1ac536a39bc2c81456e2e6db
```

The source still compiles destructuring as:

```text
DUP
SUBEXP_BEGIN
<value expression>
SUBEXP_END
POP
<matcher>
<body>
```

through `gen_subexp(var)`, with no separate path subexpression boundary around the complete destructuring operation.

## Reported discriminator

```console
jq -n 'path({} as {$a} | .)'
```

Current behavior reports an invalid path expression while:

```console
jq -n 'path(. as {$a} | .)'
```

returns `["a"]`. The expression on the left of `as` supplies only the value being destructured and should not itself contribute to path traversal.

## Overlap review

No open pull request currently claims the issue.

Closed pull request `jqlang/jq#3384` tried to:

- surround only `gen_subexp(var)` with an extra `SUBEXP_BEGIN`/`SUBEXP_END`;
- add `POP` after matcher completion.

Its author closed it after finding that removing the error did not produce correct path results and that stack/path interactions were more complex than expected.

The issue body contains a different draft arrangement:

- begin the path subexpression before evaluating the destructured value;
- discard that value;
- run the matcher;
- end the path subexpression only after matcher completion;
- discard the matcher result before the body.

It explicitly leaves the order of the final `SUBEXP_END` and `POP` uncertain.

## Controlled variants

The workflow compares four exact source layouts:

1. `baseline` — current canonical source;
2. `closed-pr-3384` — the closed PR's source logic, excluding its unrelated Makefile ordering edit;
3. `issue-end-pop` — the issue draft with `SUBEXP_END` before `POP`;
4. `issue-pop-end` — the issue draft with `POP` before `SUBEXP_END`.

The patcher fails closed unless all three current source anchors appear exactly once.

## Evidence matrix

Each variant builds exact jq source with builtin Oniguruma and runs:

- both original issue expressions;
- nested object destructuring;
- array and array/object destructuring;
- successful and fallback `?//` alternation matchers;
- scalar alternation fallback;
- backtracking values through ordinary and alternative matchers;
- ordinary binding controls;
- ordinary object, nested, and array path controls;
- bytecode disassembly of the highest-value expressions;
- Valgrind with leak/error gates on issue, alternation, and backtracking cases;
- jq's complete `make check` suite.

The workflow records status, stdout/stderr digests, exact filters, compiler/runtime identity, source patch, disassembly, Valgrind outputs, and the complete test log for every row.

## Why this is an investigation, not a patch

The first obvious fix has already failed. A candidate that merely removes the reported error can still:

- return the wrong path;
- lose matcher path components;
- mishandle `?//` preambles and final matchers;
- expose a stack value after backtracking;
- leak or double-free values;
- alter ordinary destructuring outside `path(...)`.

No source proposal should be selected before the four layouts are executed and the complete outputs are compared.

## Environment boundary

The local runtime could not resolve `github.com`, so no local jq checkout or build is claimed. The controlled GitHub workflow checks out the exact public source commit directly and owns all build products.

## Cleanup

Each matrix job uses an isolated hosted runner. No installed service, privileged device, credential, mount, or canonical repository state is changed. Artifacts are retained for 30 days.

## Current decision

Keep active until the exact matrix is complete. Select no source patch from static reasoning alone.
