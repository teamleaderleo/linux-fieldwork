# Implicit granularity mismatch

## Metadata

```json
{
  "schema": 1,
  "id": "implicit-granularity-mismatch",
  "kind": "bug-species",
  "maturity": "candidate",
  "facets": {
    "domains": ["virtualization", "memory-management", "systems"],
    "concerns": ["data-integrity", "compatibility", "cross-layer-contracts"],
    "mechanisms": ["unit-conversion", "bitmap", "backend-contract"],
    "triggers": ["non-default-platform", "architecture-variation"]
  },
  "aliases": ["magic-unit-at-cross-layer-boundary"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#617"]
}
```

## In simple words

Two layers exchange positions, counts, bitmaps, offsets, or sizes but disagree about the unit represented by each number. The common platform happens to use the hard-coded unit, so the bug appears only on a valid non-default configuration.

```text
backend bit 1 = one backend page
consumer interprets bit 1 = one fixed 4K page
```

## Hunt it

At every cross-layer numeric boundary, write the quantity with its unit. Search for magic page sizes, sector sizes, tick durations, alignment assumptions, byte/element confusion, and architecture-derived constants. Then run the smallest synthetic case with a valid non-default granule.

## Repair shape

Make the unit part of the producing interface or derive it from the layer that owns the representation. Validate compatibility before combining data from two producers with potentially different granularity.

## Regression shape

Keep the default-unit control and add at least one valid non-default unit. Use a position where multiplying by the wrong unit changes both address and length, not merely a boundary assertion.

## Limits

A fixed constant is correct when the protocol itself fixes the unit. The repair should not replace a protocol-owned 4K granule with host page size merely because another backend uses host pages.

## Case

Linux Fieldwork #617 maps a KVM dirty-bitmap page-size contract and explicitly separates it from a backend whose protocol uses fixed 4K PFNs.
