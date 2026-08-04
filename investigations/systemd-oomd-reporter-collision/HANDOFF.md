# Handoff — systemd-oomd reporter ownership

Updated: `2026-08-04`  
State: `ACTIVE — DEFECT REPRODUCED; REDUCER BOUNDED-GREEN; INTEGRATION EXACT-HEAD GATE ACTIVE`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Independent review: `INDEPENDENT-REVIEW-2026-08-04.md`  
External contact: `false`

## Durable home

Use Linux Fieldwork for narrative, evidence, design contracts, review checkpoints, and handoff. Use `teamleaderleo/systemd` for executable controlled-fork experiments.

Do not use Linux Fieldwork issue `#194` for this work. It is a closed socat tap/bridge relay item and is unrelated to systemd.

## Proven baseline

```text
run:       30693755971
job:       91352945746
artifact:  8817102322
outcome:   reproduced
sha256:    c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

The exact `user@4711.service` registration existed with a 50% pressure limit, then disappeared after the user manager reported `auto` for the same kernel cgroup path.

Controls remained stable:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

Receive order:

```text
9.527279  PID 1 pressure=kill
9.552473  user manager pressure=auto
10.524699 exact path absent
```

Root cause: current oomd state is keyed by property/path and does not retain reporter ownership. One manager's withdrawal removes another manager's still-live contribution.

## Architecture contract

```text
authority        = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key = (authority, property, cgroup path)
effective key    = (property, cgroup path)
```

Rules:

- sender-specific withdrawal;
- system-manager precedence while present;
- complete tuple/list selection;
- lower-ranked fallback on higher-ranked withdrawal;
- authoritative complete first snapshot, including empty;
- monotonic connection generations;
- stale update/disconnect isolation;
- current disconnect/stream withdrawal;
- atomic validation/allocation failure;
- identical effective state preserves timing epochs.

Read:

```text
DESIGN.md
IMPLEMENTATION.md
CONNECTION-LIFECYCLE.md
PROTOTYPE-AUDIT.md
```

## Lane 1 — baseline and attribution

Controlled PR: `teamleaderleo/systemd#1`

Use this lane only for reproduction and reporter attribution. Do not add product behavior there.

## Lane 2 — integration prototype

Controlled PR: `teamleaderleo/systemd#2`  
Branch: `linux-fieldwork/oomd-reporter-source-precedence`  
Current head at this handoff: `fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac`

Previous run `30755664280` proved:

- direct controlled-fork head identity;
- fail-closed source/test injection;
- atomicity markers;
- clean generated diff;
- `systemd-oomd` compilation with `--werror`.

It did not prove the unit or VM cases. The workflow attempted `meson test --no-rebuild test-oomd-util` without first building `test-oomd-util`, so the unit step failed as a harness defect and VM steps were skipped.

Repair commit:

```text
fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac
ci: build oomd unit test before no-rebuild execution
```

Current focused run:

```text
30914358330 — in progress at this handoff snapshot
```

Inspect, in order:

1. exact-head identity;
2. product/test injection;
3. `git diff --check` and atomicity markers;
4. `systemd-oomd` and `test-oomd-util` compile;
5. existing focused unit test;
6. integration image build;
7. reload-preservation VM case;
8. 50%-system versus 70%-user precedence/fallback case;
9. receipt, generated product diff, and guest journal.

Do not call the integration slice green unless all required stages ran and the retained evidence matches `fea4fe7…`.

## Lane 3 — standalone reducer

Controlled PR: `teamleaderleo/systemd#3`  
Branch: `linux-fieldwork/oomd-policy-reducer`

Last proven exact reducer result:

```text
head:      d9b5cd00c0899bacd9637fcc466ac01a9b841bca
run:       30913524283
artifact:  8894149501
digest:    sha256:db18d59e172da1b3d537cbd055685b4b5191d1f48607a845374edae29b52f5bc
build:     564/564
focused:   1/1 passed
```

Independent review repairs already present in that reducer lineage:

- highest-rank ambiguity no longer depends on insertion order;
- invalid array-macro iteration replaced by indexed duplicate detection;
- invalid authorities and property/value mismatches rejected;
- malformed incremental/snapshot rejection proven atomic.

A later incomplete commit at `fb8fcebb…` referenced two nonexistent lifecycle source files and broke the branch. The dangling target was removed at:

```text
731d633b05d29158ebcb78f59f42d943fab3930f
```

Current repair run:

```text
30914688124 — queued at this handoff snapshot
```

The older green receipt proves `d9b5cd0…`, not `731d633…`. Inspect the new exact-head receipt before updating the bounded-green head.

Detailed record:

```text
C-REDUCER.md
```

## Immediate next actions

1. Finish and inspect integration run `30914358330`.
2. Finish and inspect reducer repair run `30914688124`.
3. Update exact heads/runs/artifact digests in README, C-REDUCER, PR #245, and the two controlled-fork PR descriptions.
4. If integration is green, begin a separate generation/snapshot integration lane rather than expanding the temporary six-map prototype.
5. Test authoritative empty snapshots, stale generations, current disconnect, PID 1 stream termination/reconnect, cgroup disappearance, and source diagnostics.
6. Keep all writes internal until upstream contact is separately authorized.

## Review guard

Internal review may find and repair defects. It must still preserve exact attribution:

- a green result belongs only to the tested commit;
- a self-authored review is not upstream acceptance;
- queued/skipped stages are not passes;
- harness failures are not product failures, but they still block the missing product verdict;
- branch movement after a receipt requires a new exact-head gate.

## Authority

All writes and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
