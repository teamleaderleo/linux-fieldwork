# Handoff — systemd-oomd reporter collision

Updated: `2026-08-02`  
State: `ACTIVE — CURRENT-MAIN DEFECT REPRODUCED; EXACT-HEAD REPORTER TRACE QUEUED`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Controlled systemd fork PR: `teamleaderleo/systemd#1`  
External contact: `false`

## Confirmed result

The defect is independently reproduced in systemd's own `TEST-55-OOMD` integration environment.

Focused controlled-fork run:

```text
run:       30693755971
attempt:   1
artifact:  8817102322
outcome:   reproduced
```

The baseline existed before reload with a 50% pressure limit. At +1 second after the user-manager reload, the exact `user@4711.service` path was absent from `oomctl`.

Controls remained stable:

```text
ActiveEnterTimestampMonotonic before=6615081 after=6615081
NRestarts before=0 after=0
ManagedOOMMemoryPressure before=kill after=kill
```

## Exact causal ordering

The preserved guest journal proves the receive order:

```text
9.523264  user manager queues AUTO for the shared root path
9.526873  PID 1 queues KILL, limit=50%, for the same path
9.527279  oomd receives PID 1 KILL
9.552473  oomd receives user-manager AUTO
10.524699 +1s lookup is empty
```

The destructive user-manager update reaches oomd `25.194 ms` after PID 1's explicit `kill` and removes the whole path because current state is keyed by property/path rather than reporter.

Retained evidence:

- `artifacts/2026-08-01-current-main-vm-baseline.md`
- `artifacts/2026-08-01-current-main-vm-receipt.json`
- `artifacts/2026-08-01-current-main-causal-trace.txt`

Raw artifact ZIP digest:

```text
sha256:c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

## Execution identity qualification

The first successful workflow used GitHub's default pull-request checkout and therefore recorded synthetic merge commit:

```text
ef608bce10e19f55ff355ec893945ec77bd09ab6
```

Its base product source was canonical systemd main:

```text
6a863b4dc31adc49fdfdd5deba32ed1b115adda3
```

The head contribution contained only Fieldwork workflow/injector files, so product source was unchanged. The next workflow explicitly checks out and verifies the controlled-fork branch head before building.

## Lightweight source gate correction

Runs `30591852103` and `30693896488` both exposed a malformed retained mail patch at its trailer boundary. Source verification itself passed on exact current main, but `git apply` correctly rejected the hand-written patch.

The retained patch has now been replaced byte-for-byte with the exact unified diff produced by the successful VM experiment:

```text
regression.diff sha256 057b19dd2a184e411ff6454eddda9c38ed98159f0440382ad564365da6bc0ea4
```

Replacement gates on Linux Fieldwork head `108fe2df24b21d3e43709e5ff98e1770c0b02e95`:

- source/patch verification `30754788151` — queued at this update;
- repository CI `30754788144` — queued.

## Reporter-identity trace

Controlled systemd fork branch:

```text
linux-fieldwork/oomd-reporter-collision-current-main
```

Current head:

```text
5ea426a1a68488d661ce913670d254dc72020819
```

New temporary evidence tooling:

- `tools/fieldwork-inject-oomd-reporter-trace.py`
- `.github/workflows/fieldwork-oomd-reporter-trace-vm.yml`

The trace modifies product source only inside the ephemeral build and records:

```text
reporter channel
peer UID
peer PID
property
mode
path
limit
duration
```

The workflow refuses to pass unless it captures both:

```text
system-manager uid=0 pid=1 ManagedOOMMemoryPressure=kill
user-manager uid=4711 ManagedOOMMemoryPressure=auto
```

for the exact shared path. It also verifies that the checked-out Git commit equals the pull-request head SHA before injection.

Trace run:

```text
30754855305 — queued
```

## Public overlap

As checked on `2026-08-02`, `systemd/systemd#43174` remains open, unassigned, and has zero comments. No competing patch or maintainer direction is present. This was read-only verification; no upstream interaction occurred.

## Product architecture

`DESIGN.md` specifies source-aware subscriptions:

```text
reporter authority = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key   = (reporter authority, property, cgroup path)
```

Keep existing path-to-`OomdCGroupContext` maps as derived effective runtime state.

Rules:

- `auto` removes only the sending authority's contribution;
- explicit updates replace only that authority's complete tuple;
- recompute only the affected `(property, path)`;
- connections are liveness generations, not durable policy identity;
- last-link disconnect withdraws that authority's contributions;
- PID 1 subscription loss withdraws system contributions and reveals surviving user policy;
- system-manager policy has precedence while present;
- never combine limit/duration/rules fields from different reporters.

## First incomplete step

Retrieve reporter trace run `30754855305` and retain its exact artifact.

Then:

1. confirm UID/PID/channel identity at the receive boundary;
2. add a pure recomputation model with unit tests before changing runtime maps;
3. cover system/user conflict, withdrawal, disconnect, reconnect generation overlap, PID 1 reconnect, OOMRules timers, cgroup disappearance, diagnostics, and no-op timing preservation;
4. shape the implementation as a reviewable multi-commit series in the controlled fork;
5. run focused integration, unit, sanitizer, lint, and mkosi gates;
6. do not contact upstream without separate explicit authorization.

## Scope guard

Keep this lane on ManagedOOM reporter ownership and effective policy. Do not mix in pressure calculation, victim selection, prekill hooks, swap-policy behavior, generic Varlink refactors, or unrelated cgroup cleanup.

## Authority

All writes and execution are within `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action was made in `systemd/systemd`.
