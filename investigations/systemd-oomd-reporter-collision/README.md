# systemd-oomd reporter collision across user-manager reload

Tracking: Linux Fieldwork issue `#140`, Linux Fieldwork PR `#245`, and upstream report `systemd/systemd#43174`.  
Current review: `INDEPENDENT-REVIEW-2026-08-04.md`  
External contact: `false`

## Current status

`CURRENT-MAIN DEFECT REPRODUCED — REPORTER-AWARE REDUCER PROVEN AS A BOUNDED SLICE — INTEGRATION VALIDATION ACTIVE`

This README supersedes the earlier pre-VM status. The historical source-only investigation remains in Git history and in the retained verifier/design documents.

The unrelated closed Linux Fieldwork issue `#194` concerns a socat tap/bridge relay. It is not a systemd follow-on and is not part of this investigation.

## What is broken

A continuously running `user@<uid>.service` can disappear from systemd-oomd's monitored set after the nested user manager executes `daemon-reload`.

The service does not restart and its configured policy does not change. The monitored registration is removed because two reporters describe the same kernel cgroup path while current oomd state retains only one effective record per property/path.

## Plain-language model

Two clerks use the same coat-check hook:

```text
/user.slice/user-4711.slice/user@4711.service
```

- PID 1 attaches a card saying `ManagedOOMMemoryPressure=kill`, limit 50%.
- The user manager's root `-.slice` names the same cgroup and later reports its own default `auto` state.
- oomd remembers the hook, not which clerk contributed each card.
- The user's `auto` removes the shared record, including PID 1's still-live contribution.

The service and cgroup remain alive. The protection record disappears.

## Independently reproduced baseline

```text
run:       30693755971
job:       91352945746
artifact:  8817102322
outcome:   reproduced
sha256:    c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

Stable controls:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

Observed receive order:

```text
9.527279  PID 1: pressure=kill, limit=50%
9.552473  user manager: pressure=auto
10.524699 exact target path absent
```

The user-manager withdrawal arrived 25.194 ms after PID 1's registration.

Retained evidence:

```text
artifacts/2026-08-01-current-main-vm-baseline.md
artifacts/2026-08-01-current-main-vm-receipt.json
artifacts/2026-08-01-current-main-causal-trace.txt
```

## Root cause

Current receive processing chooses a monitored map by property and updates/removes by cgroup path. Peer credentials validate whether a sender may report the cgroup, but reporter identity is not retained as policy ownership.

The user manager's root `-.slice` and PID 1's `user@<uid>.service` can resolve to the same kernel cgroup. A later `auto` update therefore removes the path-level record rather than only the sending reporter's contribution.

## Selected architecture

Store contributions by:

```text
(reporter authority, property, cgroup path)
```

where authority is:

```text
(SYSTEM_MANAGER | USER_MANAGER, uid)
```

Derive the existing monitored maps as effective runtime state.

Required rules:

- `auto` withdraws only the sending authority's contribution;
- system-manager policy has precedence while present;
- one complete pressure tuple or rules list wins;
- fields and rules from different reporters are never mixed;
- system withdrawal reveals an already-live user fallback;
- initial connection messages are complete authoritative snapshots, including empty state;
- stale connection generations cannot update or withdraw current policy;
- current disconnect/stream termination withdraws only that authority;
- failed validation/allocation is atomic;
- identical effective snapshots preserve timing state.

Detailed contracts:

```text
DESIGN.md
IMPLEMENTATION.md
CONNECTION-LIFECYCLE.md
PROTOTYPE-AUDIT.md
```

## Controlled executable lanes

### Baseline and reporter trace — `teamleaderleo/systemd#1`

Evidence-only reproduction and receive-boundary attribution. No product source correction is claimed in that lane.

### Integration prototype — `teamleaderleo/systemd#2`

The generated first slice separates system and user contributions and derives effective state with whole-tuple system precedence.

Previous run `30755664280` proved exact checkout, fail-closed injection, atomicity markers, a clean generated diff, and `systemd-oomd` compilation with `--werror`. It stopped before unit/VM verdict because the workflow ran `test-oomd-util` without building that executable.

The workflow was repaired at:

```text
head: fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac
run:  30914358330
```

That exact-head run is the current integration gate. No unit or VM pass is claimed until its retained result is inspected.

### Standalone policy reducer — `teamleaderleo/systemd#3`

Last proven exact reducer head:

```text
head:      d9b5cd00c0899bacd9637fcc466ac01a9b841bca
run:       30913524283
artifact:  8894149501
digest:    sha256:db18d59e172da1b3d537cbd055685b4b5191d1f48607a845374edae29b52f5bc
build:     564/564
focused:   1/1 passed
```

Independent review found and repaired:

- insertion-order defeat of higher-ranked system policy;
- invalid `FOREACH_ARRAY(candidate + keep, ...)` macro usage;
- acceptance of malformed authorities/property values;
- a later incomplete Meson lifecycle target that referenced two nonexistent source files.

The dangling target was removed at current repair head:

```text
731d633b05d29158ebcb78f59f42d943fab3930f
```

The green receipt belongs to `d9b5cd0…`; the repair head requires its own exact-head run.

Detailed reducer record:

```text
C-REDUCER.md
```

## Executable specifications

Python models and tests cover policy reduction, atomicity, connection generations, authoritative empty snapshots, stale disconnect isolation, current disconnect withdrawal, PID 1 stream loss, fallback, and timing-epoch preservation:

```text
model_policy.py
model_connection_lifecycle.py
test_model_policy.py
test_model_atomicity.py
test_model_connection_lifecycle.py
test_model_snapshot_epochs.py
```

## Disposition

- Baseline defect: **reproduced and causally attributed**.
- Reporter-aware model: **selected and executable**.
- Standalone reducer: **bounded green at exact head `d9b5cd0…`; current repair head pending exact validation**.
- Integration prototype: **corrected exact-head validation active**.
- Submission candidate: **not ready**.
- Upstream contact: **none**.

## Authority

All writes, reviews, and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
