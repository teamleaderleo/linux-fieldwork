# Handoff — systemd-oomd reporter ownership

Updated: `2026-08-05`  
State: `ACTIVE — DEFECT REPRODUCED; LIVE BOUNDED CORRECTION GREEN; POLICY/LIFECYCLE/REGISTRY MODELS GREEN; NATIVE MANAGER INTEGRATION NEXT`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Independent review: `INDEPENDENT-REVIEW-2026-08-05.md`  
External contact: `false`

## Durable home

Use Linux Fieldwork for narrative, evidence, design contracts, review checkpoints, and handoff. Use `teamleaderleo/systemd` for executable controlled-fork experiments.

Do not use Linux Fieldwork issue `#194`; it is a closed socat tap/bridge relay item unrelated to systemd.

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
C-REDUCER.md
INDEPENDENT-REVIEW-2026-08-04.md
INDEPENDENT-REVIEW-2026-08-05.md
```

## Lane 1 — baseline and attribution

Controlled PR: `teamleaderleo/systemd#1`

Use this lane only for reproduction and reporter attribution. Do not add product behavior there.

## Lane 2 — live generated source-precedence prototype

Controlled PR: `teamleaderleo/systemd#2`  
Branch: `linux-fieldwork/oomd-reporter-source-precedence`

Authoritative exact-head result:

```text
head:            2f04a87e25df0d56f01cab5de8c99472806929a7
run:             30916547610
artifact:        8895926721
artifact digest: sha256:66ac9ee7c797dd776bb85c8705e93b4343deb8823b6bf6094ced10a6106c39d6
build:           557/557
unit:            test-oomd-util 1/1 passed
integration:     TEST-55-OOMD 1/1 passed in 35.59s
test exit:       0
outcome:         fixed
identity:        direct-controlled-fork-head
```

Guest markers:

```text
FIELDWORK_OOMD_SOURCE_PRECEDENCE=PASSED
FIELDWORK_OOMD_REPORTER_COLLISION=NOT_REPRODUCED
```

Proven in the bounded VM slice:

- reload preserves PID 1's live 50% contribution;
- system 50% wins over conflicting user 70%;
- system withdrawal reveals the existing user 70% contribution;
- user withdrawal removes the effective path;
- service identity/property controls remain stable.

The predecessor run `30914358330` reached the same successful guest verdict but failed during postprocessing because `TEST_RUNNER` was unset. Head `2f04a87e…` repaired that harness contract.

Do not promote this temporary generated six-map implementation as the final architecture. It lacks live per-link generations, authoritative wire snapshots, disconnect/PID 1 stream ownership, cgroup cleanup, and diagnostics.

## Lane 3 — policy reducer and reporter lifecycle

Controlled PR: `teamleaderleo/systemd#3`  
Branch: `linux-fieldwork/oomd-policy-reducer`

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
digest:    sha256:a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
build:     567/567
focused:   2/2 passed
identity:  direct-controlled-fork-head
```

Focused targets:

```text
test-oomd-policy
test-oomd-reporter-lifecycle
```

This is green only as a model layer. The receipt records `manager_integration=false`.

The lifecycle model retains old active policy while a replacement connection is pending. Live integration therefore requires an authoritative first snapshot—including empty state—or another bounded handshake mechanism.

## Lane 4 — transactional reporter registry

Controlled stacked PR: `teamleaderleo/systemd#9`  
Branch: `linux-fieldwork/oomd-reporter-registry`  
Base: `linux-fieldwork/oomd-policy-reducer@76749bfd3dda498c15a88c4e572340d8ade3e82b`

```text
head:      f9bcf18a8ffc6946736791f59c15c35835eba01a
run:       30918135713
artifact:  8896332176
digest:    sha256:fcd64484c5fd50cfdc8c25bea506ca3364fbc75564c93b2e0b9dd567e6136e0c
build:     566/566
focused:   test-oomd-reporter-registry 1/1 passed
identity:  direct-controlled-fork-head
```

The registry encapsulates policy and lifecycle state. Snapshot replacement and disconnect stage policy changes in a clone, commit lifecycle state only after policy work succeeds, and publish the candidate policy store only when the complete operation succeeds.

Independent review verdict: positive for the declared synchronous single-threaded boundary.

Important integration invariant: the validate-then-commit lifecycle pairing asserts that lifecycle state cannot change between validation and commit. Live manager integration must enforce single-event-loop serialized ownership with no re-entrant mutation, or replace the split calls with a version-checked/atomic transaction token.

The registry receipt records `manager_integration=false` and `external_contact=false`.

## Wire gap to close

Current user-manager reconnect reporting uses `allow_empty=false`. With no explicit policies it sends no reconnect report, so the server cannot distinguish:

```text
authoritative empty snapshot
```

from:

```text
generation not initialized
```

The next live lane needs an explicit authoritative snapshot operation that accepts `cgroups: []`. Incremental updates should be accepted only from the active initialized generation.

## Immediate next actions

1. Open a native manager/Varlink integration lane based on the registry contract, not by indefinitely expanding the temporary six-map injector.
2. Add an authoritative first-snapshot wire operation, including empty state.
3. Bind each live Varlink link to `(authority, generation)`.
4. Enforce serialized or version-checked registry transactions.
5. Accept incrementals only from the active initialized generation.
6. Withdraw current policy on current disconnect and PID 1 subscription loss; ignore stale teardown.
7. Promote reconnect only after complete policy replacement succeeds.
8. Add cgroup-disappearance cleanup, timing preservation, and contributor diagnostics.
9. Keep exact-head attribution after every branch movement.
10. Keep all writes internal until upstream contact is separately authorized.

## Review guard

Internal reviewers may find and repair defects. They must preserve evidence discipline:

- a green result belongs only to the tested commit;
- internal self-review is not upstream acceptance;
- queued/skipped stages are not passes;
- harness failures are not product failures, but they still block a missing verdict;
- branch movement after a receipt requires a new exact-head gate;
- model-layer success is not live manager integration.

## Authority

All writes and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
