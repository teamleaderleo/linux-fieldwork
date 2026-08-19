# Pair failure and success lifecycle controls

## Metadata

```json
{
  "schema": 1,
  "id": "paired-failure-success-lifecycle-controls",
  "kind": "regression-pattern",
  "maturity": "mature",
  "facets": {
    "domains": ["testing", "resource-management", "storage"],
    "concerns": ["lifecycle", "resource-ownership", "recovery"],
    "mechanisms": ["regression-testing", "state-transition"],
    "triggers": ["partial-failure", "successful-cleanup"]
  },
  "aliases": ["failure-safety-plus-success-release"],
  "relations": [],
  "cases": ["notes/processes/lifecycle-tests-cover-failure-and-success.md", "teamleaderleo/linux-fieldwork#609"]
}
```

## In simple words

When a repair changes when ownership, publication, release, or reuse happens, preserve both sides of the lifecycle:

```text
failure control:
live replacement survives interruption safely

success control:
dead predecessor is eventually released/reusable
```

A failure-only regression can accidentally bless a repair that never releases resources. A success-only test can miss the interruption window that caused corruption.

## Procedure

1. state the live-object safety property under failure;
2. state the dead-object release property under ordinary success;
3. exercise the same ownership transition through both paths;
4. inspect allocator/resource state, not only return codes;
5. delete mechanism-specific tests when review removes the mechanism they existed to preserve.

## Important refinement

Before memorializing a deferred vector, callback, or staging object in tests, ask whether that staging is required at all. If the implementation can remove the intermediate state, keep behavioral lifecycle tests and delete tests that only assert the temporary container exists.

## Source lesson

`notes/processes/lifecycle-tests-cover-failure-and-success.md` records the Cloud Hypervisor QCOW review sequence that produced this rule.
