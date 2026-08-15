# Logical representation error falls back to physical state

## Metadata

```json
{
  "schema": 1,
  "id": "logical-representation-error-falls-back-to-physical-state",
  "kind": "bug-species",
  "maturity": "candidate",
  "facets": {
    "domains": ["filesystems", "virtual-filesystems"],
    "concerns": ["truthfulness", "metadata", "cross-layer-contracts"],
    "mechanisms": ["override-metadata", "error-propagation", "fallback"],
    "triggers": ["malformed-metadata", "io-error"]
  },
  "aliases": ["override-failure-exposes-backing-state", "representation-error-becomes-plausible-default"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#656"]
}
```

## In simple words

A representation layer promises logical metadata that differs from the physical backing object. Reading/parsing the logical override fails, but the caller discards that hard error and returns the physical backing metadata as though it were the logical result.

```text
physical stat succeeds
→ required logical override read/parse fails
→ error discarded
→ physical uid/gid/mode returned as valid logical stat
```

The danger is that a representation failure becomes a believable wrong answer rather than an obvious error.

## Hunt it

Look for layered representations where one source supplies a baseline and another source overrides the user-visible truth: xattrs, manifests, sidecars, metadata databases, overlays, translation tables, or compatibility shims.

Ask:

- which override failures mean “override absent” versus “representation broken”;
- whether the caller preserves that distinction;
- whether a fallback value is merely convenient or actually authorized by the format contract;
- which downstream paths consume the plausible wrong result.

## Repair shape

Preserve the lower layer only for explicitly defined “no override” conditions. Propagate malformed/unreadable logical metadata as failure when the representation contract says it is authoritative.

## Regression shape

Keep separate controls for:

```text
override absent by contract       → physical baseline allowed
override valid                    → logical value returned
override malformed                → error
override read hard-fails          → error
```

## Limits

Fallback is legitimate when the format explicitly defines corrupt/missing override data as equivalent to absence. This species requires a contract where the logical representation is authoritative once the mode is enabled.
