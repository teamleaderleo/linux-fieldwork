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

The batch intentionally retains wire mode and pressure metadata rather than pretending it already contains final policy values. Missing or zero pressure values still require live manager-default resolution.

## Interface compatibility

The existing `ControlGroup` Varlink type has two different extension contracts:

- `mode` is a closed `ManagedOOMMode` enum;
- `property` is an open string.

The parser therefore rejects an unknown mode but ignores and compacts a future property string, matching the current receiver's behavior for property names it does not understand.

It uses:

```text
SD_JSON_STRICT | SD_JSON_ALLOW_EXTENSIONS
```

That keeps known-field type and duplicate-object-key validation strict while allowing future object fields.

## Parser contract

For understood properties, the complete message is rejected when any of the following occurs:

- the top-level value is not an object;
- `cgroups` is absent or not an array;
- an array element is not an object;
- a mandatory known field is missing or has the wrong type;
- a JSON object repeats a key;
- the mode is unknown;
- a path is relative or not normalized;
- two entries use the same `(property, canonical path)` key;
- a kill-mode `OOMRules` entry has no rules;
- allocation or string-copying fails.

An empty understood-property path is canonicalized to `/` before duplicate comparison. Therefore `""` and `"/"` cannot create two root contributions.

Malformed understood entries fail the whole message. Future property entries are not converted to policy, are excluded from duplicate comparison, and do not make an otherwise valid message fail.

## Compatibility normalization

Whole-message validation must not create a new mixed-version failure for wire shapes the existing receiver accepts.

- `auto` always becomes an explicit withdrawal; configured `limit`, `duration`, or `rules` metadata is discarded.
- swap entries discard pressure and rules metadata.
- memory-pressure entries preserve `limit` and `duration` but discard rules metadata.
- rules entries preserve a deduplicated non-empty rules list and discard pressure metadata.
- unknown extension fields are ignored after strict known-field dispatch.
- unknown property strings are ignored and compacted.

The current official sender can include configured pressure fields while switching a memory-pressure property to `auto`, so rejecting that shape would be a product regression.

## Ownership repair

The returned batch owns every canonical path, rules vector, rule string, and the message array itself. The input `sd_json_variant` may be released immediately after a successful parse.

An early version reset the output struct by assignment on entry. Reusing an output object that already owned a valid batch would leak that allocation. The parser now calls its batch destructor before parsing. The focused test first creates a legitimate prior batch, then parses a malformed message into the same output and verifies that the prior storage is released and the result remains empty.

No new output is published until every understood entry has parsed and validated.

## Focused matrix

`test-oomd-managed-oom-message` covers:

- authoritative empty reports;
- typed owned memory-pressure, swap, and OOMRules entries;
- rules deduplication;
- `auto` withdrawal canonicalization with configured metadata;
- extension-field acceptance with strict known-field decoding;
- irrelevant-field normalization for all three properties;
- empty-path root canonicalization;
- root-alias and duplicate property/path rejection;
- duplicate JSON object-key rejection;
- malformed later-element whole-message failure;
- non-object elements;
- ignored future property strings and rejected unknown modes;
- relative and non-normalized understood-property paths;
- missing and empty kill-mode rules;
- missing and wrongly typed `cgroups`;
- safe output reuse and failure cleanup.

## Current head and gate

```text
head:     02b4b14a4f4299ab0441f90a233a1bdf0e0913c0
workflow: Fieldwork OOMD managed message parser
status:   exact-head compile/test receipt pending
```

The standard systemd build is also pending at this checkpoint. No pass is claimed.

## Duplicate cleanup

Draft PR `#30` was opened during a branch-state race after the canonical parser branch temporarily appeared absent. It was closed as superseded. Its useful compatibility findings were consolidated into PR `#29`; no parallel parser implementation remains active.

## Next integration contract

The next lane must:

1. authenticate the reporter link and resolve its authority/generation;
2. parse the entire message into this owned batch;
3. authorize every understood canonical path before any policy mutation;
4. resolve pressure defaults into owned policy values;
5. construct one complete snapshot or incremental update array;
6. call the adapter exactly once;
7. publish derived monitored-map changes only after the registry transaction succeeds;
8. free typed message and policy arrays on every path.

Authorization or default-resolution failure for any later understood entry must reject the whole message just as parser failure does.

## Boundary

This lane does not modify live `oomd-manager.c`, schedule timers, handle disconnects, or prove VM behavior. It is a prerequisite for those changes, not an upstream-shaped fix.

## Authority

All work is confined to `teamleaderleo/systemd` and `teamleaderleo/linux-fieldwork`. No action has occurred in `systemd/systemd`.
