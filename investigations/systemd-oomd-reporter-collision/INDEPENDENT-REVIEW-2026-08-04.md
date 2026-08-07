# Independent internal review — 2026-08-04

Status timestamp: `2026-08-04`  
Investigation: `teamleaderleo/linux-fieldwork#140`  
Fieldwork carrier: `teamleaderleo/linux-fieldwork#245`  
Controlled systemd fork: `teamleaderleo/systemd`  
External contact: `false`

## Review authority and meaning

This is an independent review lane inside repositories owned by `teamleaderleo`. The reviewer is permitted to inspect, test, and repair these internal branches.

A positive result here means that a bounded internal gate has evidence. It is **not** an upstream systemd review, maintainer approval, submission, or acceptance.

## Durable home

The authoritative narrative, receipts, design constraints, and handoff live in **Linux Fieldwork**. The `teamleaderleo/systemd` fork carries executable reproduction, reducer, and integration experiments.

The unrelated closed `linux-fieldwork#194` tracks a socat tap/bridge relay and is not a systemd follow-on. The systemd work remains tracked by `linux-fieldwork#140`, PR `#245`, and controlled-fork PRs `teamleaderleo/systemd#1`, `#2`, and `#3`.

## Baseline verdict

The current-main defect is independently reproduced.

```text
run:       30693755971
job:       91352945746
artifact:  8817102322
outcome:   reproduced
sha256:    c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

Observed controls:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

Observed receive order:

```text
9.527279  PID 1 contribution: pressure=kill, limit=50%
9.552473  user-manager contribution: pressure=auto
10.524699 exact target path absent from effective monitored map
```

The user-manager `auto` arrived 25.194 ms after PID 1's live `kill`. Current oomd state is keyed by property/path and does not retain source ownership, so the later withdrawal removes the shared effective record.

## Product rule under review

The selected architecture is reporter-aware contributions with derived effective state:

```text
authority        = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key = (authority, property, cgroup path)
effective key    = (property, cgroup path)
```

Rules:

- `auto` withdraws only the sending authority's contribution;
- system-manager contribution wins while present;
- one complete pressure tuple or rules list wins; fields are not mixed;
- system withdrawal reveals an already-live lower-ranked user contribution;
- first message on a connection generation is an authoritative complete snapshot, including empty state;
- stale generations cannot update or withdraw current state;
- failed validation/allocation publishes no partial transaction;
- identical effective snapshots preserve timing epochs.

## Controlled-fork PR #3 — standalone reducer

### Last proven reducer head

```text
head:      d9b5cd00c0899bacd9637fcc466ac01a9b841bca
run:       30913524283
artifact:  8894149501
digest:    sha256:db18d59e172da1b3d537cbd055685b4b5191d1f48607a845374edae29b52f5bc
build:     564/564
focused:   1/1 Meson test passed
identity:  direct-controlled-fork-head
```

Receipt confirms `manager_integration=false` and `external_contact=false`.

### Review findings repaired

1. **Highest-rank selection depended on insertion order.** Two conflicting users could trigger `-ENOTUNIQ` before a later system contribution was considered. Ambiguity is now tracked only at the highest rank seen.
2. **Snapshot duplicate iteration did not compile.** `FOREACH_ARRAY(candidate + keep, ...)` was invalid macro usage. It was replaced with an indexed loop.
3. **Malformed typed values were accepted.** The reducer now rejects invalid authorities and property/value mismatches. Incremental and snapshot rejection are tested as atomic.
4. **A later incomplete lifecycle-target commit broke Meson.** Head `fb8fcebb3ab0e8a7d32a6298048e6ba13f02162a` referenced `oomd-reporter-lifecycle.c` and `test-oomd-reporter-lifecycle.c`, but neither file existed. The dangling target was removed at `731d633b05d29158ebcb78f59f42d943fab3930f` to restore the reducer's declared boundary.

### Current reducer disposition

`GREEN FOR THE BOUNDED REDUCER SEMANTIC SLICE AT d9b5cd0; CURRENT REPAIR HEAD 731d633 AWAITS ITS OWN EXACT-HEAD GATE.`

The earlier green receipt must not be attributed to the newer head. This branch is not integrated into `oomd-manager.c` or live Varlink handling.

## Controlled-fork PR #2 — source-precedence integration prototype

The previous authoritative run `30755664280` established:

- exact direct-head checkout;
- fail-closed product/test injection;
- atomicity markers present;
- generated diff clean;
- `systemd-oomd` compiled with `--werror`.

It did **not** establish the unit or VM result. The workflow compiled only `systemd-oomd`, then executed `meson test --no-rebuild test-oomd-util`; the test executable had never been built. VM stages were skipped.

The harness was repaired at:

```text
head: fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac
commit: ci: build oomd unit test before no-rebuild execution
run: 30914358330
```

The workflow now compiles both `systemd-oomd` and `test-oomd-util` before the no-rebuild unit-test step. At this review snapshot, run `30914358330` is in progress and no unit/VM pass is claimed.

### Integration disposition

`ACTIVE — CORRECTED EXACT-HEAD VALIDATION IN PROGRESS.`

Even if the focused unit and VM cases pass, this first integration slice remains incomplete: per-UID authority, connection generations, authoritative empty snapshots, disconnect/stream withdrawal, cgroup disappearance cleanup, dedicated value types, and source diagnostics are follow-on work.

## Documentation defects repaired

The front-door investigation documents had drifted behind the work:

- README still said no current-main VM reproduction existed;
- C reducer note pointed to an obsolete queued head;
- handoff described completed gates as queued;
- PR descriptions attributed green results to old heads;
- issue `#194` was incorrectly named as systemd follow-on work.

This dated review is the authority for the exact state above. Front-door files and draft PR descriptions should link here and preserve older entries only as historical checkpoints.

## Final review position

- Baseline defect: **reproduced and causally attributed**.
- Reporter-aware policy model: **coherent and executable**.
- Standalone reducer: **bounded green at exact head `d9b5cd0…`; repaired current head pending exact gate**.
- Integration prototype: **compiles at the prior head; corrected full gate in progress**.
- Upstream-shaped submission: **not ready**.
- Public upstream contact: **none**.
