# Persisted cleanup instruction outlives validation

## Metadata

```json
{
  "schema": 1,
  "id": "persisted-cleanup-instruction-outlives-validation",
  "kind": "bug-species",
  "maturity": "candidate",
  "facets": {
    "domains": ["filesystems", "privileged-tools", "lifecycle"],
    "concerns": ["authority", "path-identity", "recovery"],
    "mechanisms": ["cleanup-marker", "path-resolution", "deferred-action"],
    "triggers": ["filesystem-change", "restart", "cleanup"]
  },
  "aliases": ["validated-path-reinterpreted-at-cleanup"],
  "relations": [],
  "cases": ["notes/filesystems/cleanup-markers-must-carry-contained-relative-paths.md", "teamleaderleo/linux-fieldwork#164"]
}
```

## In simple words

Setup validates an object correctly, then stores text that will be reinterpreted later as a destructive cleanup instruction. The stored text or the filesystem can change meaning before cleanup runs.

```text
validate destination now
→ persist marker text
→ time / restart / filesystem mutation
→ cleanup interprets marker again
→ action may target a different object
```

## Typical signatures

- marker files contain absolute paths or `..` components;
- cleanup concatenates a trusted root with persisted text without complete preflight;
- symlinks can change between setup and cleanup;
- cleanup validates entries one by one and performs partial destructive work before discovering a later invalid entry;
- a marker is deleted even when cleanup fails, destroying recovery evidence.

## Hunt it

Treat durable cleanup markers as untrusted programs, not passive metadata. Ask what identity was validated during setup, what identity is actually persisted, how cleanup resolves it under current filesystem state, and whether every entry is validated before any destructive action begins.

## Repair shape

Persist the least ambiguous identifier needed for later action, such as a canonical root-relative path. On cleanup, validate the complete marker before acting, resolve current identity again, require containment, then revalidate immediately before each destructive operation. Retain the marker when validation/action fails so remaining state stays diagnosable.

## Regression shape

Cover traversal, absolute entries, symlink changes, a valid entry followed by an invalid entry with zero actions, rejected-marker preservation, correction + immediate rerun, and a normal contained case. Use fake/non-destructive cleanup operations in the fixture.

## Limits

Path revalidation remains a check-then-act contract. Strong hostile-race boundaries may require descriptor-relative APIs, no-follow policies, or namespace isolation instead of repeated pathname checks.
