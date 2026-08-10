# Optimizer keys must track execution semantics

## In simple words

When code removes “duplicate” or “redundant” operations before executing them, its idea of sameness becomes part of program behavior. A new flag that changes execution can create a bug even when the execution code itself is correct if the flag is missing from deduplication, containment, caching, ordering, or equality logic.

Literal shape:

```text
operation A: source=/src destination=/dst mode=normal
operation B: source=/src destination=/dst mode=idmapped

optimizer key: (source, destination)
result: one operation disappears before mode is consulted
```

## Why care

Optimizers are easy to review as performance-only code, but they can silently become semantic owners. The dangerous case is a component that first canonicalizes or removes operations and only later interprets behavior-changing fields.

A missing field can produce:

- first-or-last operation accidentally winning;
- a nested override being classified as redundant;
- a cache entry being reused across incompatible modes;
- setup being skipped because the only operation requesting it disappeared;
- intended ordering rules never being reached because deduplication ran first.

## Review method

When a new execution property appears, trace it through every pre-execution transformation:

1. construction and parsing;
2. equality and hash keys;
3. dictionary/set deduplication;
4. parent/child or subset redundancy tests;
5. sorting and precedence;
6. grouping, batching, memoization, and cache keys;
7. global setup decisions derived from surviving operations;
8. execution itself.

Use an adjacent semantic flag as a control when possible. If a newer field that changes behavior was deliberately added to equality plus redundancy checks, while an older field with similar execution weight is missing, that history is useful intent evidence.

## Distinguishing probe

For each semantic axis, include both exact-identity and containment cases when applicable:

```text
same shape, semantics A then B
same shape, semantics B then A
parent A + matching child B
parent B + matching child A
same-semantics parent + child negative control
```

The negative control matters: a candidate should preserve meaningful variants without disabling legitimate optimization.

## Evidence discipline

Separate these claims:

- **source fact:** a field is absent from a key or predicate;
- **reduced behavior:** the optimizer drops the variant in an executable fixture;
- **intent evidence:** history, tests, comments, or sibling fields show the distinction should survive;
- **runtime behavior:** the complete program produces a visible consequence;
- **candidate design:** which identity surfaces should change.

Do not promote a source-level mismatch into a broad runtime or security claim without the runtime discriminator.

## Origin

This lesson was retained while investigating `systemd/mkosi` sandbox bind optimization at commit `f7401bdc8d23486bb346790dc92508381a062f3b`. The target-specific evidence remains in `investigations/mkosi-bind-operation-identity/`; this note preserves only the reusable review method.
