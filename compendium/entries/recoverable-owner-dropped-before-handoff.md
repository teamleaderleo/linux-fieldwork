# Recoverable owner dropped before a fallible handoff

## Metadata

```json
{
  "schema": 1,
  "id": "recoverable-owner-dropped-before-handoff",
  "kind": "bug-species",
  "maturity": "supported",
  "facets": {
    "domains": ["storage", "caching"],
    "concerns": ["recovery", "durability", "resource-ownership"],
    "mechanisms": ["cache-eviction", "persistence", "handoff"],
    "triggers": ["io-error", "partial-failure"]
  },
  "aliases": ["drop-retryable-state-before-write"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#645"]
}
```

## In simple words

The system destroys or detaches the only state that can retry an operation before the replacement/persistence step has succeeded.

```text
retryable dirty owner exists
→ remove/drop owner
→ fallible write/handoff
→ failure
→ nothing remains to retry
```

## Hunt it

Look at eviction, queue removal, ownership transfer, cache replacement, and cleanup code. Ask whether removal happens before a fallible callback and whether failure leaves the original object still reachable for retry.

## Repair shape

Retain the predecessor/retryable owner until the successor state is established. Perform the fallible action against a borrowed or otherwise retained object, then retire it only after success.

## Regression shape

Force the handoff write to fail, assert the original dirty state remains available, repair the environmental failure, and retry through the ordinary path. The retry must persist the original state rather than succeeding because the lost state disappeared from bookkeeping.

## Limits

This is related to publication/retirement ordering but intentionally separate from `publication-before-ownership`: the decisive defect here is loss of the only recoverable copy, not a live object being reconstructed as free.

## Case

Linux Fieldwork #645 is the primary evidence carrier.
