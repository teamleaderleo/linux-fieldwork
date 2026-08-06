# ManagedOOM strict message parser

Updated: `2026-08-06`  
Controlled draft: `teamleaderleo/systemd#29`  
Branch: `linux-fieldwork/oomd-managed-oom-parser`  
External contact: `false`

## Why this lane exists

The current live receiver in `src/oom/oomd-manager.c` walks the incoming `cgroups[]` array and deliberately skips malformed elements while continuing to process the rest. That means one wire message can be only partly accepted.

PR `teamleaderleo/systemd#24` supplies an atomic typed-array transaction, but it cannot protect the message boundary unless the complete JSON array is decoded before that transaction is called.

## Selected boundary

```text
Varlink parameters
  -> strict owned OomdManagedOOMMessageBatch
  -> full-array authorization/default resolution
  -> one adapter snapshot or update transaction
```

The parser lane stops after the first arrow. It does not access cgroupfs, mutate reporter state, publish monitored maps, or bind callbacks.

## Parser contract

`oomd-managed-oom-message.[ch]` parses the existing method shape:

```text
io.systemd.oom.ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

The complete message is rejected when any of the following occurs:

- the top-level value is not an object;
- `cgroups` is absent or not an array;
- an array element is not an object;
- a mandatory field is missing or has the wrong type;
- an unknown field or duplicate object key is present;
- the mode or property is unknown;
- a path is relative or not normalized;
- two entries use the same `(property, canonical path)` key;
- an OOMRules entry has an incoherent mode/rules combination;
- allocation or string-copying fails.

An empty path is canonicalized to `/` before duplicate comparison. Therefore `""` and `"/"` cannot create two root contributions.

## Ownership

The returned batch owns:

- each canonical path;
- each rules vector and rule string;
- the message array itself.

The input `sd_json_variant` may be unreferenced immediately after a successful parse. No output is published to the caller until every array element has parsed and validated.

Limit and duration are preserved as wire metadata. Manager defaults are deliberately not resolved in this parser because that requires live manager state. Cgroup-owner authorization is also deferred so parsing remains deterministic and side-effect free.

## Focused matrix

`test-oomd-managed-oom-message` covers:

- authoritative empty report;
- typed memory-pressure, swap, and OOMRules entries;
- ownership after JSON storage release;
- empty-path root canonicalization;
- root-alias duplicate rejection;
- malformed later-element whole-message failure;
- non-object elements;
- unknown properties and fields;
- relative and non-normalized paths;
- duplicate property/path keys;
- inconsistent rule mode/property combinations;
- missing and wrongly typed `cgroups`.

## Current head and gate

```text
head:     3b0b4712612f9dbaa0c26d27b7ccf96f80eb0cae
workflow: Fieldwork OOMD managed message parser
status:   exact-head compile/test receipt pending
```

The standard systemd build for this head is also queued. No pass is claimed.

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
