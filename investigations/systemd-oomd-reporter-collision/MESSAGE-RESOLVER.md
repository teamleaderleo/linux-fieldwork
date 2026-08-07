# ManagedOOM batch authorization and default resolution

Updated: `2026-08-06`  
Controlled draft: `teamleaderleo/systemd#31`  
Branch: `linux-fieldwork/oomd-managed-oom-resolver`  
External contact: `false`

## Why this lane exists

The owned parser in `teamleaderleo/systemd#29` protects the JSON message boundary, and the transactional APIs in `#24` protect the policy mutation boundary. A security and value-resolution gap remains between them.

The live receiver currently resolves memory-pressure defaults and checks user-manager cgroup ownership while walking individual array elements. Moving the parser into that loop without a second whole-batch stage would still allow a later unauthorized path or unusable value to fail after earlier entries had already been prepared or published.

## Selected boundary

```text
owned OomdManagedOOMMessageBatch
  -> validate every typed entry
  -> validate all required defaults
  -> authorize every user-manager path
  -> allocate one owned OomdPolicySnapshotEntry[] batch
  -> one adapter snapshot or update transaction
```

No policy output exists until all validation, default checks, and authorization callbacks have succeeded.

## Authority contract

```text
SYSTEM_MANAGER authority: kind=SYSTEM_MANAGER, uid=0
USER_MANAGER authority:   kind=USER_MANAGER, valid uid
```

System-manager batches bypass user cgroup-owner authorization, matching the current receiver. A nonempty user-manager batch requires a read-only path-authorizer callback. An authoritative empty user-manager snapshot requires no path authorization because it names no cgroup.

Withdrawals are still authorized. This preserves the current security boundary: a user manager cannot remove policy for a path it does not own merely by reporting `auto`.

## Default-resolution contract

For a kill-mode memory-pressure entry:

- a nonzero wire limit is explicit;
- a zero wire limit uses the supplied manager default;
- a finite wire duration is explicit;
- `USEC_INFINITY` uses the supplied manager duration default.

A zero manager limit is a valid resolved value. Pointer presence, not the numeric value, distinguishes whether a limit default was supplied. An omitted duration requires a finite default.

The model uses the wire-scale `uint32_t` limit. Live integration must convert the manager's `loadavg_t` default into that scale—or introduce an explicitly typed conversion boundary—before calling this resolver.

## Output contract

`OomdManagedOOMPolicyBatch` owns:

- a contiguous `OomdPolicySnapshotEntry[]` array;
- every canonical path;
- every policy value;
- every copied rules vector and string.

The parsed wire batch may be freed immediately after resolution. Reusing a policy output object first releases its prior valid contents. Every failure leaves the output empty.

## Recovery and review repairs

The first resolver implementation remained recoverable at commit `22a76ef4a41f4c0dd8dde2942dbd2a92041ab646`, but its branch was reset during a branch-state race and PR `#31` temporarily closed with an empty diff.

The lane was reconstructed on parser head `02b4b14a4f4299ab0441f90a233a1bdf0e0913c0` and repaired before its first verdict:

1. add the direct `<stdbool.h>` dependency;
2. release prior valid output before any new success or failure;
3. reject the NUL-terminated path-vector `n_items + 1` overflow edge;
4. accept a legitimate zero pressure-limit default;
5. replace sentinel-pointer cleanup testing with reuse of a real valid output batch.

## Focused matrix

`test-oomd-managed-oom-resolver` covers:

- authoritative empty user snapshot without an authorizer;
- later-path authorization failure before output allocation;
- default pressure tuple resolution;
- zero pressure-limit default;
- explicit pressure tuple without defaults;
- missing or infinite duration defaults rejected before authorization;
- `auto` as a source-specific withdrawal;
- output ownership after the parsed batch is freed;
- system-authority authorization bypass;
- required authorizer for nonempty user batches;
- forged duplicate typed keys rejected before authorization;
- prior valid output released when a later resolution fails.

## Current head and gate

```text
head:     5e1932882d56684aa2d5596746001034ac3033a0
workflow: Fieldwork OOMD managed message resolver
status:   exact-head compile/test receipt pending
```

The generic systemd build is also pending. No pass is claimed.

## Next native integration contract

The next lane must bind these pure stages to the live manager without weakening their ordering:

1. resolve the Varlink link to its `(authority, generation)` session;
2. parse the complete JSON message;
3. provide live manager defaults in the resolver's exact units;
4. bind the path authorizer to `cg_path_get_owner_uid()` without side effects;
5. resolve the complete policy batch;
6. classify first snapshot versus incremental update;
7. call the adapter exactly once;
8. publish effective monitored-map changes only after registry success;
9. schedule or cancel generation-keyed grace timers from the returned adapter event;
10. free both owned batches on every path.

The first live lane should still avoid replacing all existing map publication at once. It needs a bounded synchronization layer or a disposable source injector so rollback remains straightforward.

## Boundary

This resolver does not modify `oomd-manager.c`, perform real cgroupfs authorization, convert `loadavg_t`, invoke the adapter, schedule timers, or prove VM behavior. It establishes the final pure whole-message stage before native callbacks.

## Authority

All work is confined to `teamleaderleo/systemd` and `teamleaderleo/linux-fieldwork`. No action has occurred in `systemd/systemd`.
