# Publication before ownership

## Metadata

```json
{
  "schema": 1,
  "id": "publication-before-ownership",
  "kind": "bug-species",
  "maturity": "supported",
  "facets": {
    "domains": ["storage", "filesystems"],
    "concerns": ["resource-ownership", "recovery", "state-consistency"],
    "mechanisms": ["publication", "reference-counting", "allocation"],
    "triggers": ["resource-exhaustion", "partial-failure", "restart"]
  },
  "aliases": ["reachable-before-owned"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#609"]
}
```

## In simple words

A newly allocated object becomes reachable before the metadata that prevents allocator reuse records it as owned.

```text
allocate
→ publish pointer
→ ownership update later
```

If the later step fails, a restart can reconstruct a live object as reusable.

## Hunt it

Ask what makes the object reachable, what excludes it from reuse, whether those operations are separated by fallible work, and what a clean reopen concludes if execution stops between them.

## Repair shape

```text
prepare
→ own
→ publish
→ retire predecessor
```

Prefer conservative failure residue such as an unreachable object remaining owned over a reachable object becoming reusable.

## Regression shape

Force failure in the ordering window, reopen from durable state, and prove the live object cannot be reallocated. Pair it with a normal-success control showing that the retired predecessor eventually becomes reusable.

## Limits

The pattern does not apply when one atomic primitive simultaneously establishes reachability and exclusion from reuse.

## Case

Linux Fieldwork #609 is the primary evidence carrier. The reusable source note is `notes/processes/ownership-is-part-of-publication.md`.
