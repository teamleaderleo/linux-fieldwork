# ManagedOOM owned message parser

Updated: `2026-08-06`  
Controlled draft: `teamleaderleo/systemd#29`  
Branch: `linux-fieldwork/oomd-managed-oom-parser`  
Superseded duplicate: `teamleaderleo/systemd#30` (closed)  
External contact: `false`

## Why this lane exists

The current live receiver in `src/oom/oomd-manager.c` walks the incoming `cgroups[]` array and skips malformed elements while continuing to process the rest. One wire message can therefore be only partly accepted.

PR `teamleaderleo/systemd#24` supplies an atomic typed-array transaction, but it cannot protect the message boundary unless the complete JSON array is decoded before that transaction is called.

## Selected boundary

```text
Varlink parameters
  -> owned OomdManagedOOMMessageBatch
  -> full-array authorization/default resolution
  -> one adapter snapshot or update transaction
```

The parser lane stops after the first arrow. It does not access cgroupfs, mutate reporter state, publish monitored maps, or bind callbacks.

## Parser contract

`oomd-managed-oom-message.[ch]` parses the existing method shape:

```text
io.systemd.oom.ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

The parser uses:

```text
SD_JSON_STRICT | SD_JSON_ALLOW_EXTENSIONS
```

That combination keeps strict validation of known fields and duplicate JSON object-key rejection while preserving forward compatibility with additional fields.

The complete message is rejected when any of the following occurs:

- the top-level value is not an object;
- `cgroups` is absent or not an array;
- an array element is not an object;
- a mandatory known field is missing or has the wrong type;
- a JSON object repeats a key;
- the mode or property is unknown;
- a path is relative or not normalized;
- two entries use the same `(property, canonical path)` key;
- a kill-mode `OOMRules` entry has no rules;
- allocation or string-copying fails.

An empty path is canonicalized to `/` before duplicate comparison. Therefore `""` and `"/"` cannot create two root contributions.

## Compatibility normalization

Whole-message validation must not create a new mixed-version failure for wire shapes the existing receiver accepts.

- `auto` always becomes an explicit withdrawal; configured `limit`, `duration`, or `rules` metadata is discarded.
- swap entries discard pressure and rules metadata.
- memory-pressure entries preserve `limit` and `duration` but discard rules metadata.
- rules entries preserve a deduplicated non-empty rules list and discard pressure metadata.
- unknown extension fields are ignored after strict known-field dispatch.

The current official sender can include configured pressure fields while switching a memory-pressure property to `auto`, so rejecting that shape would be a product regression.

## Ownership

The returned batch owns:

- each canonical path;
- each rules vector and rule string;
- the message array itself.

The input `sd_json_variant` may be unreferenced immediately after a successful parse. No output is published to the caller until every array element has parsed and validated. The output batch is reset on every failure.

Manager defaults are deliberately not resolved in this parser because that requires live manager state. Cgroup-owner authorization is also deferred so parsing remains deterministic and side-effect free.

## Focused matrix

`test-oomd-managed-oom-message` covers:

- authoritative empty report;
- typed memory-pressure, swap, and OOMRules entries;
- ownership after JSON storage release;
- `auto` withdrawal canonicalization with configured metadata;
- extension-field acceptance with strict known-field decoding;
- irrelevant-field normalization for all three properties;
- empty-path root canonicalization;
- root-alias and duplicate property/path rejection;
- duplicate JSON object-key rejection;
- malformed later-element whole-message failure;
- non-object elements;
- unknown modes and properties;
- relative and non-normalized paths;
- missing and empty kill-mode rules;
- missing and wrongly typed `cgroups`;
- output-batch clearing on failure.

## Current head and gate

```text
head:     2284cac72f5319a47cfd2cf6c6dc58900374e803
workflow: Fieldwork OOMD managed message parser
status:   exact-head compile/test receipt pending
```

The standard systemd build for this head is also pending. No pass is claimed.

## Duplicate cleanup

Draft PR `#30` was opened during a branch-state race after the canonical parser branch temporarily appeared absent. It was closed as superseded. Its useful compatibility findings were ported into PR `#29`; no parallel parser implementation remains active.

## Next integration contract

The next lane must:

1. authenticate the reporter link and resolve its authority/generation;
2. parse the entire message into this owned batch;
3. authorize every canonical path before any policy mutation;
4. resolve pressure defaults into owned policy values;
5. construct one complete snapshot or incremental update array;
6. call the adapter exactly once;
7. publish derived monitored-map changes only after the registry transaction succeeds;
8. free the typed message and policy arrays on every path.

Authorization or default-resolution failure for any later element must reject the whole message just as parser failure does.

## Boundary

This lane does not modify live `oomd-manager.c`, schedule timers, handle disconnects, or prove VM behavior. It is a prerequisite for those changes, not an upstream-shaped fix.

## Authority

All work is confined to `teamleaderleo/systemd` and `teamleaderleo/linux-fieldwork`. No action has occurred in `systemd/systemd`.
