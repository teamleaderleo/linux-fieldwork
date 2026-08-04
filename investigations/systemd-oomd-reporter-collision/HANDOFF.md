# Handoff — systemd-oomd reporter ownership

Updated: `2026-08-04`  
State: `ACTIVE — DEFECT REPRODUCED; POLICY/LIFECYCLE MODELS EXACT-HEAD GREEN; LIVE INTEGRATION VM GATE ACTIVE`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Independent review: `INDEPENDENT-REVIEW-2026-08-04.md`  
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
C-REDUCER.md
INDEPENDENT-REVIEW-2026-08-04.md
```

## Lane 1 — baseline and attribution

Controlled PR: `teamleaderleo/systemd#1`

Use this lane only for reproduction and reporter attribution. Do not add product behavior there.

## Lane 2 — live integration prototype

Controlled PR: `teamleaderleo/systemd#2`  
Branch: `linux-fieldwork/oomd-reporter-source-precedence`  
Current exact head: `fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac`

Run `30755664280` proved:

- direct controlled-fork head identity;
- fail-closed source/test injection;
- atomicity markers;
- clean generated diff;
- `systemd-oomd` compilation with `--werror`.

It did not prove unit or VM behavior because the workflow attempted `meson test --no-rebuild test-oomd-util` without first building the test executable.

Repair commit:

```text
fea4fe7f2c09ca2e33a2870fa7425e87d81a42ac
ci: build oomd unit test before no-rebuild execution
```

Current focused run:

```text
30914358330
```

Already passed at this handoff snapshot:

- exact direct-head checkout;
- fail-closed product/test injection;
- atomicity markers;
- clean generated diff;
- Meson configure;
- `systemd-oomd` and `test-oomd-util` compilation;
- existing focused `test-oomd-util` execution.

Still active:

- integration image build;
- reload-preservation VM case;
- 50%-system versus 70%-user precedence/fallback VM case;
- retained receipt, generated product diff, and guest journal.

Do not call the live integration slice green unless the required VM stages run and the retained evidence matches `fea4fe7…`.

## Lane 3 — policy reducer and reporter lifecycle

Controlled PR: `teamleaderleo/systemd#3`  
Branch: `linux-fieldwork/oomd-policy-reducer`

Current authoritative exact-head result:

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

The receipt records:

```text
policy=typed-array copy-and-swap reducer
lifecycle=two-phase generation-safe reporter transitions
manager_integration=false
external_contact=false
```

Independent review repairs in this lineage:

- highest-rank ambiguity no longer depends on insertion order;
- invalid array-macro iteration replaced by indexed duplicate detection;
- invalid authorities and property/value mismatches rejected atomically;
- dangling lifecycle references to nonexistent files removed;
- lifecycle source and focused test properly wired into Meson once the files existed;
- older green receipts kept tied to their exact tested commits.

The lifecycle model retains old active policy while a replacement connection is pending. Live integration therefore requires an authoritative first snapshot—including empty state—or another bounded handshake mechanism.

This lane is green only as a model layer. It does not yet modify live manager or Varlink behavior.

## Immediate next actions

1. Finish and inspect integration run `30914358330`.
2. Download and inspect its receipt, generated product diff, unit log, VM journal, and both testcase outcomes.
3. If live integration is green, open a separate generation/snapshot integration lane rather than expanding the temporary six-map prototype.
4. Integrate authoritative empty snapshots, stale-generation rejection, current disconnect, PID 1 stream termination/reconnect, cgroup disappearance cleanup, and source diagnostics.
5. Keep exact-head attribution after every branch movement.
6. Keep all writes internal until upstream contact is separately authorized.

## Review guard

Internal reviewers may find and repair defects. They must still preserve evidence discipline:

- a green result belongs only to the tested commit;
- internal self-review is not upstream acceptance;
- queued/skipped stages are not passes;
- harness failures are not product failures, but they still block the missing verdict;
- branch movement after a receipt requires a new exact-head gate.

## Authority

All writes and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
