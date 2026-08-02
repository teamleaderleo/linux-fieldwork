# Handoff — systemd-oomd reporter ownership

Updated: `2026-08-02`  
State: `ACTIVE — DEFECT REPRODUCED; ATOMIC PRODUCT SLICE AND SNAPSHOT LIFECYCLE UNDER VALIDATION`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Controlled evidence PR: `teamleaderleo/systemd#1`  
Controlled product PR: `teamleaderleo/systemd#2`  
External contact: `false`

## Confirmed current-main defect

The reporter collision is independently reproduced in systemd's own `TEST-55-OOMD` VM environment.

```text
run:       30693755971
attempt:   1
artifact:  8817102322
outcome:   reproduced
```

The exact `user@4711.service` path existed before reload with a 50% pressure limit and disappeared by +1 second.

Stable controls:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

Proven receive order:

```text
9.527279  oomd receives PID 1 ManagedOOMMemoryPressure=kill
9.552473  oomd receives user-manager ManagedOOMMemoryPressure=auto
10.524699 +1s target path is absent
```

The user-manager `auto` reaches the receive path `25.194 ms` after PID 1's `kill` and removes the whole property/path entry because current state does not retain reporter ownership.

Retained evidence:

- `artifacts/2026-08-01-current-main-vm-baseline.md`
- `artifacts/2026-08-01-current-main-vm-receipt.json`
- `artifacts/2026-08-01-current-main-causal-trace.txt`

Raw artifact ZIP:

```text
sha256:c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

The first successful baseline used GitHub's synthetic PR merge checkout. Its base product source was canonical:

```text
systemd/main@6a863b4dc31adc49fdfdd5deba32ed1b115adda3
```

and the head contribution contained evidence tooling only. Treat that baseline as merge-derived but product-source exact.

## Evidence lane — reporter identity

Controlled branch:

```text
teamleaderleo/systemd:linux-fieldwork/oomd-reporter-collision-current-main
head: 5ea426a1a68488d661ce913670d254dc72020819
```

Temporary receive-boundary instrumentation records:

```text
reporter channel
peer UID and PID
property and mode
path
limit and duration
```

The workflow verifies direct branch-head checkout and requires both:

```text
system-manager uid=0 pid=1 pressure=kill
user-manager uid=4711 pressure=auto
```

for the exact shared path.

Current trace run:

```text
30754855305 — queued at this handoff update
```

This lane remains evidence-only; no product fix is selected or committed there.

## Product lane — source precedence first slice

Controlled branch:

```text
teamleaderleo/systemd:linux-fieldwork/oomd-reporter-source-precedence
head: 338411d7924a9e9dae78eefff2ededd06858660a
PR:   teamleaderleo/systemd#2
```

The disposable injector adds six source-class contribution maps:

```text
SYSTEM_MANAGER × {swap, memory pressure, rules}
USER_MANAGER   × {swap, memory pressure, rules}
```

The existing monitored maps remain derived effective runtime state.

First-slice rules:

- `auto` removes only the sending source contribution;
- system-manager policy has precedence while present;
- one complete pressure tuple or rules list wins;
- system withdrawal reveals an already-live user contribution;
- hidden lower-authority no-op updates do not reset pressure timing;
- dropped OOMRules timers are cleaned only when rules leave the effective list.

Authoritative direct-head product run:

```text
30755664280 — queued
```

The workflow now:

- checks out and verifies the exact controlled-fork head;
- applies fail-closed source transformations;
- requires atomicity markers in generated C;
- runs `git diff --check`;
- compiles `systemd-oomd` with `--werror`;
- runs existing `test-oomd-util`;
- runs the reported reload regression;
- runs 50%-system versus 70%-user precedence and fallback transitions;
- retains product diff, build logs, VM journal, and a schema-3 direct-head receipt.

Runs `30755078046` and `30755298324` are stale for product conclusions because they predate atomicity or direct-head receipt fixes.

## Prototype atomicity audit

The initial product generator mutated a source contribution before fallible effective-state recomputation. An OOMRules allocation failure could leave source and effective maps divergent.

Head `338411d7...` includes transactional hardening:

- `auto` stages effective reduction with the sender ignored, then removes source state only after success;
- existing pressure/rules tuples are snapshotted and restored on failure;
- newly inserted contributions are removed on failure;
- effective rule lists are allocated before effective-context mutation;
- `-ENOMEM` rolls back and propagates.

Detailed audit:

```text
PROTOTYPE-AUDIT.md
```

## Executable policy specifications

Owned Python specifications now cover both reduction and connection lifecycle:

```text
model_policy.py
model_connection_lifecycle.py
test_model_policy.py
test_model_atomicity.py
test_model_connection_lifecycle.py
```

Reduction coverage includes:

- system/user precedence;
- complete-tuple selection;
- source-specific withdrawal;
- rules-list ownership;
- cgroup disappearance;
- deterministic diagnostics;
- no-op epoch preservation;
- equal-rank conflict rejection;
- atomic update rollback.

Connection coverage includes:

- authoritative empty reconnect snapshots;
- stale-generation update rejection;
- stale disconnect isolation;
- current-generation disconnect withdrawal;
- pending disconnect isolation;
- complete snapshot replacement;
- snapshot rollback;
- PID 1 termination fallback;
- PID 1 empty reconnect snapshot;
- monotonic session generations.

Current fast model gate before this handoff commit:

```text
30755606362 — queued
```

This handoff update will trigger a replacement branch-head run; use the newest run attached to the resulting head.

## Refined connection lifecycle

The earlier “withdraw on last live link” rule is superseded.

Current user-manager code calls the initial builder with `allow_empty=false`; a restarted manager with no explicit policies sends no initial message. Retaining old authority state while any newer link exists can therefore leave stale policy indefinitely.

The required lifecycle is an authoritative first-message snapshot per connection generation:

1. user manager always sends an initial call, including `cgroups: []`;
2. server connect callback creates a pending generation without changing policy;
3. first method call replaces the complete authority snapshot atomically;
4. the new initialized generation becomes current and older links become stale;
5. stale-link updates are ignored;
6. stale/pending disconnects do not change policy;
7. current-generation disconnect withdraws authority contributions immediately;
8. PID 1's first subscription reply is treated as a complete system snapshot;
9. PID 1 stream termination withdraws system contributions and reveals user fallback;
10. reconnect snapshots restore authority without reactivating stale generations.

Detailed contract:

```text
CONNECTION-LIFECYCLE.md
```

## C implementation map

`IMPLEMENTATION.md` defines:

- separate `oomd-policy.[ch]` reducer;
- typed authority, contribution, and effective keys;
- atomic snapshot and incremental update APIs;
- manager connect/disconnect integration;
- effective-map transition and timer rules;
- deterministic source diagnostics;
- focused C unit-test matrix;
- multi-commit review series.

The current generated first slice intentionally uses full `OomdCGroupContext` values and source-class maps. It is a validation vehicle, not the final data model.

## Public overlap

As checked on `2026-08-02`, `systemd/systemd#43174` remains open, unassigned, and has zero comments. No competing patch or maintainer direction was found.

No upstream interaction occurred.

## First incomplete steps

1. Retrieve and inspect the newest executable-model run on the current Linux Fieldwork head.
2. Retrieve reporter trace run `30754855305` and retain its exact artifact.
3. Retrieve direct-head product run `30755664280`; inspect compile, existing unit test, both VM transitions, generated diff, and receipt.
4. If the first product slice is green, begin the dedicated reducer/session implementation rather than expanding six temporary source maps.
5. Add runtime probes for empty user snapshots, reconnect overlap, stale updates, current disconnect, and PID 1 stream loss/reconnect.
6. Keep all work in controlled repositories until separate upstream authorization is explicit.

## Scope guard

Keep this lane on ManagedOOM reporter ownership, snapshot lifecycle, effective-policy reduction, and diagnostics. Do not mix in pressure calculation, victim selection, prekill hooks, generic Varlink refactors, or unrelated cgroup cleanup.

## Authority

All writes and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action was made in `systemd/systemd`.
