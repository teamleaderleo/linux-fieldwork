# Independent internal review — 2026-08-05

Status timestamp: `2026-08-05`  
Investigation: `teamleaderleo/linux-fieldwork#140`  
Fieldwork carrier: `teamleaderleo/linux-fieldwork#245`  
Controlled systemd fork: `teamleaderleo/systemd`  
External contact: `false`

## Review authority and meaning

This is an independent review lane inside repositories owned by `teamleaderleo`. The reviewer is permitted to inspect, test, document, and repair these internal branches.

A positive result here means that a bounded internal gate has attributable evidence. It is **not** an upstream systemd review, maintainer approval, submission, or acceptance.

Linux Fieldwork remains the durable home for narrative, receipts, architecture constraints, review findings, and handoff. The controlled `teamleaderleo/systemd` fork carries executable experiments.

## Current progression

The work has moved through four distinct stages:

1. reproduce and causally attribute the current-main registration-loss defect;
2. prove a live source-precedence correction in a disposable product checkout;
3. compile and test isolated policy-reducer and reporter-lifecycle components;
4. compose those model components behind a transactional reporter-registry API before touching live Varlink callbacks.

These stages are related but not interchangeable. A receipt belongs only to its exact tested commit and declared layer.

## Baseline defect — reproduced

```text
run:       30693755971
job:       91352945746
artifact:  8817102322
outcome:   reproduced
sha256:    c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

The exact `user@4711.service` registration existed with a 50% pressure limit, then disappeared after the nested user manager reported `auto` for the same kernel cgroup path.

Controls remained stable:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

Receive order:

```text
9.527279  PID 1 pressure=kill, limit=50%
9.552473  user manager pressure=auto
10.524699 exact monitored path absent
```

The defect is a reporter-identity collision: current effective state is keyed by property/path, while peer identity is used for authorization but is not retained as contribution ownership.

## Live source-precedence prototype — exact-head green

Controlled draft: `teamleaderleo/systemd#2`

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

Guest evidence contains both required markers:

```text
FIELDWORK_OOMD_SOURCE_PRECEDENCE=PASSED
FIELDWORK_OOMD_REPORTER_COLLISION=NOT_REPRODUCED
```

The VM proved the bounded behavior:

- user-manager reload did not delete PID 1's live 50% registration;
- a conflicting user 70% contribution did not override PID 1's 50%;
- system withdrawal revealed the already-live user 70% contribution without another user update;
- final user withdrawal removed the effective path;
- service identity and configured-property controls remained stable.

The previous run `30914358330` had already produced the same guest-success markers but crashed during postprocessing because `TEST_RUNNER` was unset. Exact head `2f04a87e…` repaired that harness contract, and run `30916547610` completed successfully. The red predecessor is retained as historical evidence, not presented as a product failure.

This lane is still a generated first integration slice. It does not implement per-connection generations, authoritative snapshots on the wire, disconnect ownership, PID 1 stream loss, cgroup cleanup, or source diagnostics.

## Policy reducer and reporter lifecycle — exact-head green

Controlled draft: `teamleaderleo/systemd#3`

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

This result proves the bounded C model for reporter-aware policy reduction, complete/empty authority snapshots, atomic rejection, whole-value precedence and fallback, connection generations, pending/active transitions, stale-generation isolation, and current-generation withdrawal.

The receipt records `manager_integration=false`. No live manager or Varlink behavior is claimed by this result.

## Transactional reporter registry — new exact-head green lane

Controlled stacked draft: `teamleaderleo/systemd#9`  
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

The retained receipt identifies the model as:

```text
transactional policy-plus-lifecycle reporter registry
manager_integration=false
external_contact=false
```

### Independent code-review verdict

`OomdReporterRegistry` is a coherent composition layer for the declared single-threaded model boundary.

For complete snapshot replacement it:

1. validates the reporter connection against lifecycle state;
2. clones the live policy store;
3. applies the complete authority snapshot to the clone;
4. commits lifecycle promotion only after policy replacement succeeds;
5. swaps the candidate store into the live registry.

For disconnect it clones and withdraws authority policy before committing the lifecycle transition, then publishes the candidate store only when both operations succeed.

Focused tests cover invalid snapshot rollback, valid replacement and old-generation rejection, authoritative empty replacement, old/pending/current disconnect distinctions, late stale disconnect isolation, and system-withdrawal fallback to existing user policy.

### Integration prerequisite found by review

The registry uses a validate-then-commit lifecycle pairing and asserts that commit cannot fail after validation. That is valid only while registry mutation is serialized and no second actor can alter lifecycle state between those calls. The current component enforces this by encapsulating both inner objects behind a synchronous single-threaded API.

Before live manager/Varlink integration, one of these conditions must be made explicit and mechanically true:

- all registry operations remain owned by one serialized event-loop context with no re-entrant mutation between validation and commit; or
- lifecycle prepare returns a versioned transaction token that commit verifies atomically; or
- validation and lifecycle commit are collapsed into one registry-internal transaction operation.

This is not a failing result for PR `#9`; it is a production-integration invariant that must not be lost when callbacks and link teardown are wired around the model.

## Wire-protocol gap

Current user managers construct reconnect reporting with `allow_empty=false`, while `io.systemd.oom.ReportManagedOOMCGroups` carries only a `cgroups` array. A user manager with no explicit policies therefore sends no reconnect message.

A server cannot safely distinguish:

```text
this generation has an authoritative empty snapshot
```

from:

```text
this generation has not initialized yet
```

The next live lane needs an explicit authoritative snapshot operation that can carry `cgroups: []`. Incremental updates can remain a separate active-generation method.

## Current review disposition

- Baseline defect: **reproduced and causally attributed**.
- Live source-precedence prototype: **exact-head green for the bounded VM slice at `2f04a87e…`**.
- Policy reducer and lifecycle model: **exact-head green at `76749bfd…`**.
- Transactional reporter registry: **exact-head green at `f9bcf18a…`; positive bounded review with a required serialization/transaction invariant for live integration**.
- Native manager/Varlink integration: **not implemented**.
- Upstream-shaped submission: **not ready**.
- Public upstream contact: **none**.

## Next engineering lane

Do not keep expanding the temporary six-map injector as the final architecture. The next controlled branch should natively integrate the registry contract into manager and Varlink handling:

1. explicit authoritative first snapshot, including empty state;
2. per-link `(authority, generation)` identity;
3. serialized or version-checked registry transactions;
4. incremental updates only from the active initialized generation;
5. current disconnect and PID 1 subscription-loss withdrawal;
6. reconnect promotion only after successful policy replacement;
7. cgroup-disappearance cleanup;
8. effective-state timer preservation;
9. source/contributor diagnostics.

Every branch movement requires a new exact-head gate. Internal reviewers may repair defects, but internal review remains distinct from upstream approval.

## Authority

All writes, reviews, and execution remain confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
