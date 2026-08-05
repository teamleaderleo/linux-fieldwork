# Wire initialization and mixed-version compatibility

## Status

The policy reducer, lifecycle model, transactional registry, bounded live source-precedence prototype, and standalone mixed-version wire model are independently green in controlled `teamleaderleo/systemd` branches.

Current registry receipt:

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
digest:    sha256:bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
focused:   test-oomd-reporter-registry 1/1 passed
```

Current wire-compatibility receipt:

```text
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
compile:   cc -std=c11 -O2 -Wall -Wextra -Werror
focused:   full compatibility model passed
identity:  direct-controlled-fork-head
```

The remaining wire work is connecting these proven contracts to live user-manager and oomd Varlink paths.

## Existing method can carry an empty snapshot

The current Varlink interface already defines:

```text
io.systemd.oom.ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

An empty array is valid. Current oomd receive processing iterates the array; `cgroups: []` is therefore a successful no-op on an old server.

The user manager already has `build_managed_oom_cgroups_json(..., allow_empty, ...)`, but its initial send currently calls it with `allow_empty=false`. If no explicit ManagedOOM policy exists, it sends no method call.

A new user manager does **not** need a second Varlink method merely to express initialization. It can send the existing method once on connect with:

```json
{"cgroups": []}
```

A new oomd can identify the first report on each connection as the authoritative complete snapshot. Later calls on the active generation remain incremental updates.

This is mixed-version friendly:

- new client to old oomd: an empty first report is accepted as a harmless no-op;
- old non-empty client to new oomd: its existing first complete report can initialize the generation;
- old empty client to new oomd: it sends nothing, so bounded compatibility grace is still required.

## Mixed-version failure mode

Consider:

1. generation N is active and owns policy P;
2. generation N+1 connects and becomes pending;
3. the old active connection disconnects;
4. generation N+1 is an older client with an empty policy set, so it sends nothing.

Retaining P forever is stale. Withdrawing P immediately creates an avoidable reconnect gap for clients that will report shortly.

## Bounded compatibility rule

When an active generation disconnects while a replacement generation is pending:

- retain the old contribution for a bounded initialization grace;
- key the timer to the pending generation;
- cancel the timer when the pending generation sends an explicit complete report, including empty, or its first legacy non-empty complete report;
- on grace expiry, withdraw the disconnected old contribution while leaving the pending connection alive;
- allow a later first legacy non-empty report to initialize that still-connected pending generation after the old policy has been withdrawn;
- ignore stale timers after promotion, replacement, or disconnect;
- if a newer pending generation supersedes an older one while old policy is retained, re-key and re-arm grace for the newer generation;
- if the pending connection disconnects after the old active connection, withdraw immediately.

The grace is compatibility behavior only. New clients should send their complete snapshot, including empty, immediately after connect.

## Controlled standalone model — `teamleaderleo/systemd#20`

```text
branch:    linux-fieldwork/oomd-wire-init-compat
base:      linux-fieldwork/oomd-reporter-registry@247f546ae1a108df0d24ea1b74854b50539c05a4
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
status:    success
```

Independent review found and repaired a grace-lifetime defect in the original model: `begin()` cleared grace whenever a newer pending generation replaced an older pending connection. The old timer then became stale while no timer belonged to the newer generation, allowing disconnected old policy to remain indefinitely. The repaired model re-keys grace to the newer pending generation and proves eventual withdrawal by the current timer.

The focused matrix covers:

- explicit empty and non-empty snapshots;
- continuity after old disconnect;
- first legacy non-empty promotion;
- legacy-empty withdrawal after grace;
- late legacy promotion after expiry;
- stale timer rejection after promotion and replacement;
- grace re-keying for a newer pending generation;
- pending disconnect ordering;
- stale disconnect isolation.

## Sender validation lane — `teamleaderleo/systemd#21`

```text
branch: linux-fieldwork/oomd-empty-initial-report
base:   linux-fieldwork/oomd-wire-init-compat@bca6cedb1904aa1a9af56c2076bea6e156b04d26
head:   b896fdc1801718bf7b22703e48edc1853a54a134
run:    30980196233
status: queued
```

This lane applies a fail-closed generated one-line change to the initial user-manager sender:

```text
allow_empty=false -> allow_empty=true
```

It reuses the existing method, verifies an exact one-addition/one-deletion product diff, and compiles the `systemd` manager target with `--werror`. It does not claim receiver registry integration.

## Registry grace transaction lane — `teamleaderleo/systemd#22`

```text
branch: linux-fieldwork/oomd-registry-grace
base:   linux-fieldwork/oomd-wire-init-compat@bca6cedb1904aa1a9af56c2076bea6e156b04d26
head:   06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:    30980672145
status: queued
```

This lane moves grace expiry into the actual `OomdReporterLifecycle` and `OomdReporterRegistry` components. The new transaction withdraws disconnected retained policy only for the matching current pending generation, leaves that pending session alive, ignores stale timers, and allows late snapshot promotion after expiry.

It does not yet schedule a real event timer or connect registry operations to live Varlink callbacks.

## Integration requirements

A live implementation needs:

1. initial user-manager send on the existing method with `allow_empty=true`;
2. first-report versus incremental classification per link;
3. legacy first-report detection on a pending link;
4. per-link authority and generation identity;
5. generation-keyed initialization timer;
6. timer re-keying when a newer pending connection supersedes an older one;
7. cancellation before publishing the promoted generation;
8. stale callback and stale timer rejection;
9. serialized transactional policy replacement and lifecycle promotion;
10. current disconnect and PID 1 stream-loss withdrawal;
11. contributor diagnostics showing authority, generation, initialization mode, and effective winner.

## Authority

Internal controlled-fork work only. No public upstream contact is authorized or performed.
