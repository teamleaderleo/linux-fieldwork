# Post-commit rollback

## Metadata

```json
{
  "schema": 1,
  "id": "post-commit-rollback",
  "kind": "bug-species",
  "maturity": "supported",
  "facets": {
    "domains": ["distributed-systems", "virtualization", "migration"],
    "concerns": ["state-consistency", "recovery", "split-brain"],
    "mechanisms": ["commit-point", "rollback", "acknowledgement"],
    "triggers": ["late-cleanup-failure", "partial-failure"]
  },
  "aliases": ["rollback-after-remote-commit"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#606"]
}
```

## In simple words

The system crosses a commit point that makes the new topology/state authoritative, then a later local failure is handled by restoring the old active state as though commit had never happened.

```text
remote side commits + becomes active
→ commit acknowledged
→ source-local cleanup fails
→ generic failure recovery reactivates source
```

The bug is not merely that cleanup failed. The legal recovery set changed at the commit point.

## Hunt it

Identify the protocol or durability event after which rollback is no longer safe. Trace every fallible operation after that point and then inspect generic error recovery. Ask whether errors carry enough state to distinguish pre-commit from post-commit failure.

## Repair shape

Represent commit state explicitly. Move safely movable work before commit; classify unavoidable post-commit failures as committed-with-cleanup-failure; never route them through pre-commit rollback logic.

## Regression shape

Make the commit point undeniable, then force one local failure afterward. Assert that recovery preserves the committed topology and does not resurrect the pre-commit active owner.

## Limits

Some protocols support compensating transactions after commit. That is not ordinary rollback: the compensation is a new committed operation with its own legality and failure semantics.

## Case

Linux Fieldwork #606 maps the Cloud Hypervisor migration `Complete` acknowledgement boundary and source-resume recovery path.
