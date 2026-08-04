# systemd-oomd reporter collision across user-manager reload

Tracking: Linux Fieldwork issue `#140`, Linux Fieldwork PR `#245`, and upstream report `systemd/systemd#43174`.  
Current review: `INDEPENDENT-REVIEW-2026-08-05.md`  
External contact: `false`

## Current status

`CURRENT-MAIN DEFECT REPRODUCED — LIVE BOUNDED CORRECTION GREEN — POLICY/LIFECYCLE/REGISTRY MODELS EXACT-HEAD GREEN — NATIVE MANAGER INTEGRATION NEXT`

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
INDEPENDENT-REVIEW-2026-08-05.md
```

## Controlled executable lanes

### Baseline and reporter trace — `teamleaderleo/systemd#1`

Evidence-only reproduction and receive-boundary attribution. No product correction is claimed in that lane.

### Live integration prototype — `teamleaderleo/systemd#2`

Authoritative exact-head result:

```text
head:            2f04a87e25df0d56f01cab5de8c99472806929a7
run:             30916547610
artifact:        8895926721
artifact digest: sha256:66ac9ee7c797dd776bb85c8705e93b4343deb8823b6bf6094ced10a6106c39d6
build:           557/557
unit:            test-oomd-util 1/1 passed
integration:     TEST-55-OOMD 1/1 passed in 35.59s
outcome:         fixed
identity:        direct-controlled-fork-head
```

Guest evidence contains:

```text
FIELDWORK_OOMD_SOURCE_PRECEDENCE=PASSED
FIELDWORK_OOMD_REPORTER_COLLISION=NOT_REPRODUCED
```

This bounded generated slice proved reload preservation, system-over-user precedence, live fallback after system withdrawal, and final removal after user withdrawal.

The predecessor run `30914358330` produced the same guest-success markers but failed after guest completion because `TEST_RUNNER` was unset. Head `2f04a87e…` repaired the postprocessing contract and produced the authoritative green receipt.

This lane remains deliberately incomplete: it does not provide live per-link generations, authoritative snapshots on the wire, disconnect/PID 1 stream withdrawal, cgroup cleanup, or source diagnostics.

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

Independent review found and repaired insertion-order precedence, invalid array iteration, malformed typed values, dangling lifecycle targets, missing Meson wiring, and stale exact-head attribution.

The receipt records `manager_integration=false`. This proves the policy and generation models, not live Varlink or manager behavior.

### Transactional reporter registry — `teamleaderleo/systemd#9`

This stacked draft composes the reducer and lifecycle components behind one synchronous registry API.

```text
base:      linux-fieldwork/oomd-policy-reducer@76749bfd3dda498c15a88c4e572340d8ade3e82b
head:      f9bcf18a8ffc6946736791f59c15c35835eba01a
run:       30918135713
artifact:  8896332176
digest:    sha256:fcd64484c5fd50cfdc8c25bea506ca3364fbc75564c93b2e0b9dd567e6136e0c
build:     566/566
focused:   test-oomd-reporter-registry 1/1 passed
identity:  direct-controlled-fork-head
```

It stages policy replacement or withdrawal in a cloned store, commits lifecycle state only after policy work succeeds, and publishes the candidate store only when the full operation succeeds.

Independent review is positive for the declared single-threaded model boundary. The validate-then-commit pairing relies on serialized registry ownership: no second actor may mutate lifecycle state between validation and commit. Live integration must enforce that event-loop invariant or replace the split calls with a version-checked/atomic transaction primitive.

The receipt records `manager_integration=false` and `external_contact=false`.

## Wire-protocol boundary

Current user-manager reconnect reporting uses `allow_empty=false`. A manager with no explicit policies sends no reconnect message, so the server cannot distinguish an authoritative empty snapshot from an uninitialized connection generation.

The next live lane needs an explicit authoritative snapshot operation that can carry:

```text
cgroups: []
```

Incremental updates should remain separate and accepted only from the initialized active generation.

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
- Live bounded source-precedence correction: **exact-head green at `2f04a87e…`**.
- Policy reducer and reporter lifecycle models: **exact-head green at `76749bfd…`**.
- Transactional reporter registry: **exact-head green at `f9bcf18a…`**.
- Native manager/Varlink integration: **not implemented**.
- Submission candidate: **not ready**.
- Upstream contact: **none**.

## Next engineering move

Open a native manager/Varlink integration lane rather than expanding the temporary six-map injector indefinitely. It must include authoritative empty snapshots, per-link generations, serialized or version-checked transactions, current disconnect and PID 1 stream-loss withdrawal, reconnect promotion after successful replacement, cgroup cleanup, timer preservation, and source diagnostics.

## Authority

All writes, reviews, and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. Internal review is not upstream systemd approval. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
