# systemd-oomd reporter collision across user-manager reload

Tracking: Linux Fieldwork issue `#140`, Linux Fieldwork PR `#245`, and upstream report `systemd/systemd#43174`.  
Current review: `INDEPENDENT-REVIEW-2026-08-04.md`  
External contact: `false`

## Current status

`CURRENT-MAIN DEFECT REPRODUCED — POLICY AND REPORTER-LIFECYCLE MODELS EXACT-HEAD GREEN — LIVE INTEGRATION VALIDATION ACTIVE`

The unrelated closed Linux Fieldwork issue `#194` concerns a socat tap/bridge relay. It is not a systemd follow-on.

## What is broken

A continuously running `user@<uid>.service` can disappear from systemd-oomd's monitored set after the nested user manager executes `daemon-reload`.

The service does not restart and its configured policy does not change. The registration is removed because PID 1 and the user manager can describe the same kernel cgroup path while current oomd state retains one effective record per property/path rather than independent source contributions.

## Plain-language model

Two clerks use the same coat-check hook:

```text
/user.slice/user-4711.slice/user@4711.service
```

- PID 1 attaches a card saying `ManagedOOMMemoryPressure=kill`, limit 50%.
- The user manager's root `-.slice` names the same cgroup and later reports its default `auto` state.
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

Derive existing monitored maps as effective runtime state.

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
C-REDUCER.md
INDEPENDENT-REVIEW-2026-08-04.md
```

## Controlled executable lanes

### Baseline and reporter trace — `teamleaderleo/systemd#1`

Evidence-only reproduction and receive-boundary attribution. No product correction is claimed in that lane.

### Integration prototype — `teamleaderleo/systemd#2`

The generated first slice separates system and user contributions and derives effective state with whole-tuple system precedence.

Run `30755664280` proved exact checkout, fail-closed injection, atomicity markers, a clean generated diff, and `systemd-oomd` compilation with `--werror`. It stopped before unit/VM verdict because the workflow ran `test-oomd-util` without building that executable.

The harness was repaired at:

```text
head: fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac
run:  30914358330
```

That run has already compiled `systemd-oomd` and `test-oomd-util` and passed the existing focused unit test. At this checkpoint it is still building the integration image; the two live VM cases remain unproven until their retained artifact is inspected.

### Policy reducer and reporter lifecycle — `teamleaderleo/systemd#3`

Current authoritative exact-head gate:

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
digest:    sha256:a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
build:     567/567
focused:   2/2 passed
```

Focused targets:

```text
test-oomd-policy
test-oomd-reporter-lifecycle
```

Independent review found and repaired:

- insertion-order defeat of higher-ranked system policy;
- invalid snapshot array-macro use;
- acceptance of malformed authorities/property values;
- an incomplete lifecycle target referencing nonexistent files;
- missing Meson wiring after the lifecycle sources were added.

The receipt records `manager_integration=false`. This proves the policy and generation models, not live Varlink or manager behavior.

The lifecycle model retains old active policy while a replacement connection is pending. Live integration therefore depends on an authoritative first snapshot—including empty state—or another bounded handshake mechanism.

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
- Reporter-aware architecture: **selected and executable**.
- Policy reducer and reporter lifecycle models: **exact-head green at `76749bfd…`**.
- Live integration prototype: **unit gate passed; VM gate still active**.
- Submission candidate: **not ready**.
- Upstream contact: **none**.

## Authority

All writes, reviews, and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. Internal review is not upstream systemd approval. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
