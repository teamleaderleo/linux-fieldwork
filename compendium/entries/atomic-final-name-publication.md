# Atomic final-name publication

## Metadata

```json
{
  "schema": 1,
  "id": "atomic-final-name-publication",
  "kind": "repair-pattern",
  "maturity": "mature",
  "facets": {
    "domains": ["filesystems", "caching"],
    "concerns": ["data-integrity", "concurrency", "publication"],
    "mechanisms": ["temporary-file", "rename", "validation"],
    "triggers": ["concurrent-reader", "partial-write", "writer-failure"]
  },
  "aliases": ["temp-then-rename"],
  "relations": [],
  "cases": ["notes/reliability/cache-files-must-be-published-atomically.md"]
}
```

## In simple words

Make the final visible filename mean “complete object,” not “a writer has started.”

```text
unique same-directory temporary
→ write complete contents
→ validate
→ close/sync as required
→ atomic rename/replace
→ final name visible
```

## Use it when

Readers discover an object by filename and must never observe partial contents from a writer still constructing that object.

## What it solves

- readers seeing truncated in-progress files;
- a failed writer leaving a final path that looks valid;
- ambiguity between cache hit and cache fill in progress.

## What it does not solve

- duplicate concurrent work;
- changing upstream responses;
- content-integrity validation;
- durability requirements beyond the chosen rename/sync contract;
- cross-filesystem rename behavior.

Those are separate concerns and should not be smuggled into the pattern name.

## Regression shape

Synchronize a writer after its first chunk and start a second reader/request. Before the repair the final path can expose partial bytes. With the repair the final name remains absent until a complete object is ready. Also force writer failure and require no final path and no abandoned temporary.

## Source lesson

`notes/reliability/cache-files-must-be-published-atomically.md` records the retained mmdebstrap caching-proxy example and its negative controls.
