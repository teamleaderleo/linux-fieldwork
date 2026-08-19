# Cancellation falls through to success

## Metadata

```json
{
  "schema": 1,
  "id": "cancellation-falls-through-to-success",
  "kind": "bug-species",
  "maturity": "supported",
  "facets": {
    "domains": ["process-lifecycle", "cli"],
    "concerns": ["truthfulness", "lifecycle", "completeness"],
    "mechanisms": ["signal-handling", "cleanup", "exit-status"],
    "triggers": ["cancellation", "signal"]
  },
  "aliases": ["cleaned-up-interruption-reported-as-success"],
  "relations": [],
  "cases": ["notes/processes/cancellation-cleanup-must-not-fall-through-to-success.md", "teamleaderleo/linux-fieldwork#141"]
}
```

## In simple words

The program handles interruption correctly enough to clean resources, but control then falls back into the ordinary success epilogue and exits zero.

```text
signal
→ terminate/reap children
→ remove temporary state
→ break/return into normal epilogue
→ exit 0
```

Clean local state does not mean completed work.

## Hunt it

Read signal/KeyboardInterrupt handlers through to the final process exit, not only through cleanup. Search for `break`, `return`, cleared flags, or swallowed exceptions that rejoin success paths after cancellation.

## Repair shape

Give cancellation an explicit terminal result after cleanup: conventional signal-derived status, re-raised signal, or another documented non-success outcome. Preserve a durable diagnostic that distinguishes cancellation from ordinary failure.

## Regression shape

Test parent-only signal delivery as well as process-group delivery. Assert exit status, absence of success markers, child/grandchild cleanup, temporary-state cleanup, and immediate clean rerun. Keep an unsignaled success control.

## Limits

Some interactive commands intentionally treat user cancellation as a successful no-op. That must be an explicit public contract rather than an accidental fall-through from cleanup code.

## Related family

This is a process-lifecycle specialization of the broader `false-success-after-incomplete-work` family in the Fieldwork compendium.
