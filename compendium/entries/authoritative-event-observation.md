# Authoritative-event observation

## Metadata

```json
{
  "schema": 1,
  "id": "authoritative-event-observation",
  "kind": "hunting-technique",
  "maturity": "mature",
  "facets": {
    "domains": ["testing", "lifecycle", "controllers"],
    "concerns": ["ordering", "state-consistency"],
    "mechanisms": ["observation", "event-monitoring"],
    "triggers": ["asynchrony", "reuse"]
  },
  "aliases": ["observe-owner-issued-completion"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#423"]
}
```

## In simple words

When a test or controller needs to know that a transition is complete, identify the component that owns the transition and observe the state/event it emits at completion.

Do not begin with the most convenient symptom.

## Procedure

1. name the transition;
2. identify its operation owner;
3. list observable symptoms and owner-issued terminal evidence;
4. compare their ordering;
5. if possible, delay the owner-issued event after making the proxy symptom happen;
6. gate the next destructive/reuse transition on the strongest available evidence.

## Useful pair

```text
proxy symptom        authoritative state
--------------       -------------------
SSH disappears       VMM shutdown event
socket exists        service ready event
producer EOF         validated complete object
process exits        owned child/resource set empty
```

The right column is illustrative. The actual owner contract decides what is authoritative.

## Negative control

A good test should also demonstrate a case where the proxy and authoritative event occur together, so the fixture proves ordering rather than merely adding delay.
