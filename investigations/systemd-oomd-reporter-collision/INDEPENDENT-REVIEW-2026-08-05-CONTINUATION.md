# Independent internal review continuation — 2026-08-05

Investigation: `teamleaderleo/linux-fieldwork#140`  
Fieldwork carrier: `teamleaderleo/linux-fieldwork#245`  
Controlled systemd fork: `teamleaderleo/systemd`  
External contact: `false`

## Review boundary

This continuation records internal review, repair, and exact-head evidence in repositories owned by `teamleaderleo`. A positive bounded result is not an upstream systemd review, approval, submission, or acceptance.

Linux Fieldwork is the durable record. Controlled-fork pull requests remain executable research lanes.

## Current progression

The reporter-collision work now has these distinct layers:

1. current-main baseline reproduction and causal attribution;
2. bounded live generated source-precedence correction;
3. isolated policy reducer and reporter lifecycle;
4. transactional policy-plus-lifecycle reporter registry;
5. mixed-version initialization/grace model;
6. grace-expiry transaction integrated into the registry model;
7. initial-empty user-manager sender validation on the existing Varlink method.

A receipt belongs only to the tested commit and its declared layer.

## Registry continuity contract — corrected and exact-head green

Controlled draft: `teamleaderleo/systemd#9`

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
digest:    sha256:bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
focused:   test-oomd-reporter-registry 1/1 passed
identity:  direct-controlled-fork-head
```

Review found documentation drift around reconnect continuity. The executable lifecycle deliberately permits the still-connected active generation to send incremental updates while a replacement generation is pending. The pending generation itself is blocked until its authoritative snapshot commits. Snapshot promotion atomically replaces any interim value and makes the former active generation stale.

An explicit registry test now pins that contract. The exact-head workflow passed checkout, identity, build, focused execution, clean-diff, receipt, and artifact gates.

The live integration invariant remains: registry mutation must be serialized and non-reentrant, or validate/commit must become a version-checked atomic transaction.

## Mixed-version initialization grace — repaired and exact-head green

Controlled draft: `teamleaderleo/systemd#20`

```text
base:      linux-fieldwork/oomd-reporter-registry@247f546ae1a108df0d24ea1b74854b50539c05a4
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
compile:   cc -std=c11 -O2 -Wall -Wextra -Werror
focused:   compatibility model passed
identity:  direct-controlled-fork-head
```

Independent review found a real lifetime defect in the first model. When a newer pending connection superseded an older pending connection while policy from a disconnected active generation was retained, `begin()` disarmed grace. The old timer became stale and no timer belonged to the newer generation, allowing stale policy to survive indefinitely.

The repaired model re-keys and re-arms grace for the newest pending generation. It proves that the stale old timer is ignored and the current timer eventually withdraws retained policy. It also proves that a still-connected pending legacy client may later send its first non-empty report and promote after grace has withdrawn the old policy.

The workflow was repaired so its binary and evidence live outside the checkout; the clean-worktree gate now measures repository cleanliness rather than generated files.

## Existing method supports explicit empty initialization

The current interface already defines:

```text
io.systemd.oom.ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

`cgroups: []` is valid. Current oomd receive processing obtains the array and iterates its elements, so an empty first report is a successful no-op for an older server.

The user-manager helper already implements its `allow_empty` parameter by constructing an empty array before scanning units. The required sender change is therefore only the initial call:

```text
allow_empty=false -> allow_empty=true
```

A prior review statement that the helper would assert on the empty case was incorrect and is superseded by direct source inspection.

This gives a mixed-version path without inventing another Varlink method:

- new user manager to old oomd: empty first report is accepted as a no-op;
- old non-empty user manager to new oomd: its first existing complete report can initialize the pending generation;
- old empty user manager to new oomd: it sends nothing, so bounded compatibility grace remains necessary.

## Initial-empty sender validation — active

Controlled draft: `teamleaderleo/systemd#21`

Current exact head:

```text
head: 50ed2893e37c66366401d51e4a9a579ad70a4210
run:  31020281327
state: queued at this checkpoint
```

The fail-closed generated slice changes only `manager_varlink_send_managed_oom_initial()` in `src/core/varlink.c` and requires an exact one-addition/one-deletion product diff.

Two harness defects were repaired before a product verdict:

1. the first injector counted identical `allow_empty=true` text globally and collided with a pre-existing system-manager call; matching is now scoped to the initial user-manager sender function;
2. Meson target `systemd` was ambiguous between a shared library and executable; the workflow now compiles `./systemd:executable` explicitly.

The immediately preceding run `30985433921` had already passed wire compatibility, injection, verification, exact product-diff, and Meson configuration. It stopped only at the ambiguous target selection. No source failure was observed.

This lane proves only sender-side initialization and old-server method compatibility. It does not integrate the registry into live oomd callbacks.

## Registry grace transaction — exact-head green

Controlled draft: `teamleaderleo/systemd#22`

```text
base:      linux-fieldwork/oomd-wire-init-compat@bca6cedb1904aa1a9af56c2076bea6e156b04d26
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
digest:    sha256:5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
focused:   test-oomd-reporter-registry 1/1 passed
identity:  direct-controlled-fork-head
```

The lifecycle now prepares a generation-keyed grace-expiry transition. The registry withdraws retained authority policy before committing lifecycle state. Stale, promoted, disconnected, and still-active cases are no-ops. A matching expiry clears only the disconnected old active generation and leaves the pending generation connected for a late first snapshot.

Independent review is positive for the bounded component. Live integration must still own and re-arm the actual timer on newer pending generations, cancel it on promotion/disconnect, reject stale callbacks, and preserve serialized registry access.

## Linux Fieldwork workflow repair

The policy-model workflow previously ran all 30 executable-specification tests successfully, then failed its clean-tree gate because `python -m py_compile` wrote `__pycache__` into the checkout.

The workflow now places bytecode under the runner temporary directory. At Linux Fieldwork head `56a5c911ffe03f375e95a49839ecc04e3362e8d7`, all relevant checks were green:

```text
Verify systemd-oomd policy model     30980834388  success
Verify systemd-oomd reporter collision 30980834339 success
Linux Fieldwork CI                   30980834398  success
```

The 30-test model result and clean-worktree result are now both attributable.

## Current review disposition

- Baseline defect: **reproduced and causally attributed**.
- Live bounded source-precedence correction: **exact-head green**.
- Policy reducer and lifecycle: **exact-head green**.
- Transactional registry continuity: **exact-head green at `247f546a…`**.
- Mixed-version initialization/grace model: **exact-head green at `bca6cedb…` after a substantive timer-lifetime repair**.
- Registry grace-expiry transaction: **exact-head green at `06f0add4…`**.
- Initial-empty sender validation: **current head `50ed2893…` queued; no final compile verdict yet**.
- Native oomd Varlink callback integration: **not implemented**.
- Upstream-shaped submission: **not ready**.
- Public upstream contact: **none**.

## Next engineering sequence

1. finish and inspect the exact-head sender compile for PR `#21`;
2. add live per-link `(authority, generation)` state to a controlled oomd Varlink adapter lane;
3. classify the first report on a link as the complete authority snapshot and later calls as incrementals;
4. bind connect/disconnect callbacks and generation-keyed grace timers;
5. transactionally call the registry for snapshot, incremental, disconnect, and expiry events;
6. handle PID 1 subscription termination and reconnect as the system reporter lane;
7. retain cgroup cleanup, timer preservation, and contributor diagnostics as explicit gates;
8. run a native live VM matrix before presenting anything as an upstream-shaped candidate.

## Authority

All writes, reviews, and execution remain confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
