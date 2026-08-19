# Completed result overwritten by cleanup

## Metadata

```json
{
  "schema": 1,
  "id": "completed-result-overwritten-by-cleanup",
  "kind": "bug-species",
  "maturity": "mature",
  "facets": {
    "domains": ["process-lifecycle", "async-runtime"],
    "concerns": ["error-semantics", "lifecycle", "truthfulness"],
    "mechanisms": ["cleanup", "terminal-state", "signals"],
    "triggers": ["cleanup-failure", "late-signal"]
  },
  "aliases": ["late-cleanup-replaces-primary-result"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#297", "teamleaderleo/fieldwork#76", "teamleaderleo/fieldwork#882"]
}
```

## In simple words

The primary operation has already completed with an authoritative result, but a later signal or cleanup failure becomes the result reported to the caller.

```text
primary result R complete
→ cleanup happens
→ secondary outcome C
→ caller incorrectly receives C instead of R
```

## Hunt it

Write the intended precedence table before reading the final error-handling code. Then inject cleanup failure and late signals after primary completion. Look for generic `?`, `finally`, trap, or last-error-wins behavior that erases the earlier result.

## Repair shape

Capture the selected primary result, perform cleanup under its own policy, and report cleanup problems separately unless cleanup is explicitly part of the primary success contract.

## Regression shape

Test the cross-product of primary success/failure and cleanup success/failure, plus signals arriving before versus after primary completion. Make precedence explicit.

## Limits

This species is about **which result wins**. It is distinct from cleanup that never settles and therefore prevents an already-selected result from being published at all.

## Case

Linux Fieldwork #297 contains a concrete process/signal ordering and selected precedence. Fieldwork #76 and #882 support the generic cross-domain family.
