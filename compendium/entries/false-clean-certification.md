# False clean-state certification

## Metadata

```json
{
  "schema": 1,
  "id": "false-clean-certification",
  "kind": "bug-species",
  "maturity": "mature",
  "facets": {
    "domains": ["storage", "lifecycle"],
    "concerns": ["durability", "truthfulness", "recovery"],
    "mechanisms": ["synchronization", "status-publication"],
    "triggers": ["io-error", "partial-failure"]
  },
  "aliases": ["clean-marker-after-failed-sync"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#611", "teamleaderleo/fieldwork#626"]
}
```

## In simple words

A required synchronization or validation step fails, but the system still publishes the marker that says the state is clean, current, complete, or successfully checked.

```text
required work fails
→ failure is ignored/downgraded
→ CLEAN / SUCCESS marker published
```

## Hunt it

Trace every marker that changes recovery behavior: clean bits, current generations, successful audit summaries, ready states, and cache-valid stamps. Ask which prerequisite operations make the marker truthful and whether any of their errors can be swallowed before publication.

## Repair shape

Publish the certification only after all contract-required work succeeds, or represent partial/unknown state explicitly.

## Regression shape

Force the prerequisite failure and inspect the raw marker/result. Then reopen/restart or invoke the downstream consumer that relies on the marker.

## Limits

A best-effort operation may intentionally define success without complete coverage. That is valid only when the contract and machine-readable result preserve the weaker meaning.

## Cases

Linux Fieldwork #611 is the storage specialization. Fieldwork #626 provides an unrelated developer-tool analogue and supports the more general `false-success-after-incomplete-work` species.
