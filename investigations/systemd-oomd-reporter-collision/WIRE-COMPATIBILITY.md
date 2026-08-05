# Wire initialization and mixed-version compatibility

## Status

The policy reducer, lifecycle model, transactional registry, and bounded live source-precedence prototype are independently green in controlled `teamleaderleo/systemd` branches.

The current registry receipt is:

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
digest:    sha256:bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
focused:   test-oomd-reporter-registry 1/1 passed
```

The remaining wire problem is preserving correct initialization and disconnect behavior across both new and legacy user managers.

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

## Controlled model

Draft PR: `teamleaderleo/systemd#20`

```text
branch: linux-fieldwork/oomd-wire-init-compat
base:   linux-fieldwork/oomd-reporter-registry@247f546ae1a108df0d24ea1b74854b50539c05a4
head:   bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:    30979635398
status: queued
```

The branch was restacked after the registry continuity test moved PR `#9`.

Independent review found and repaired a grace-lifetime defect in the original model: `begin()` cleared grace whenever a newer pending generation replaced an older pending connection. The old timer then became stale while no timer belonged to the newer generation, allowing disconnected old policy to remain indefinitely. The repaired model re-keys grace to the newer pending generation and tests eventual withdrawal by the current timer.

The standalone C model now covers eleven cases:

- new explicit empty snapshot;
- new non-empty replacement;
- replacement after old disconnect without policy gap;
- first legacy non-empty report promotion;
- legacy-empty withdrawal after grace;
- late legacy non-empty promotion after grace expiry;
- stale grace after successful promotion;
- stale old grace after a newer pending generation;
- current grace withdrawal for that newer pending generation;
- pending disconnect before and after old-active disconnect;
- stale disconnect after promotion.

Local review compilation used:

```text
cc -std=c11 -O2 -Wall -Wextra -Werror
```

and produced:

```text
FIELDWORK_OOMD_WIRE_INIT_COMPAT=PASSED
```

The workflow keeps generated binary/evidence outside the checkout and verifies a clean worktree. The GitHub exact-head run remains required before this repaired head is promoted.

## Integration requirements

A live implementation needs:

1. initial user-manager send on the existing method with `allow_empty=true`;
2. first-report versus incremental classification per link;
3. legacy first-report detection on a pending link;
4. per-link authority and generation userdata;
5. generation-keyed initialization timer;
6. timer re-keying when a newer pending connection supersedes an older one;
7. cancellation before publishing the promoted generation;
8. stale callback and stale timer rejection;
9. serialized transactional policy replacement and lifecycle promotion;
10. current disconnect and PID 1 stream-loss withdrawal;
11. contributor diagnostics showing authority, generation, initialization mode, and effective winner.

## Authority

Internal controlled-fork work only. No public upstream contact is authorized or performed.
