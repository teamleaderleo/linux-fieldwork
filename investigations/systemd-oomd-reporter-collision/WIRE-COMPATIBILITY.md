# Wire initialization and mixed-version compatibility

## Status

The policy reducer, lifecycle model, transactional registry, bounded live source-precedence prototype, standalone mixed-version grace model, and registry grace-expiry transaction are exact-head green in controlled `teamleaderleo/systemd` branches.

Current receipts:

```text
registry continuity
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
digest:    sha256:bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2

mixed-version grace
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c

registry grace transaction
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
digest:    sha256:5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
```

The remaining wire work is connecting these contracts to live user-manager and oomd Varlink paths.

## Existing method can carry an empty snapshot

The current interface already defines:

```text
io.systemd.oom.ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

An empty array is valid. Current oomd receive processing looks up the array and iterates its elements; `cgroups: []` is therefore a successful no-op on an older server.

The user manager already has `build_managed_oom_cgroups_json(..., allow_empty, ...)`. When `allow_empty=true`, that helper constructs an empty array before scanning units. The initial sender currently calls it with `allow_empty=false`; an empty policy set therefore produces no method call.

A new user manager does not need a second method merely to express initialization. It can use the existing method once on connect with:

```json
{"cgroups": []}
```

A new oomd can classify the first report on each connection as the complete authoritative snapshot. Later reports from the active generation remain incrementals.

Mixed-version behavior:

- new client to old oomd: empty first report is accepted as a harmless no-op;
- old non-empty client to new oomd: its existing first complete report can initialize the generation;
- old empty client to new oomd: it sends nothing, so bounded compatibility grace remains necessary.

## Mixed-version failure mode

1. generation N is active and owns policy P;
2. generation N+1 connects and becomes pending;
3. generation N disconnects;
4. generation N+1 is an older client with an empty policy set and sends nothing.

Retaining P forever is stale. Withdrawing it immediately creates an avoidable reconnect gap for clients that will report shortly.

## Bounded compatibility rule

When the active generation disconnects while a replacement is pending:

- retain old policy for a bounded initialization grace;
- key the timer to the pending generation;
- cancel it when that generation sends an explicit complete report, including empty, or its first legacy non-empty complete report;
- on expiry, withdraw disconnected old policy while leaving the pending link alive;
- allow a later first legacy non-empty report to promote that still-connected pending generation;
- ignore stale timers after promotion, replacement, or disconnect;
- re-key and re-arm grace when a newer pending generation supersedes an older one while old policy is retained;
- withdraw immediately if the pending link disconnects after the old active link.

The grace is compatibility behavior only. New clients should send complete state immediately after connect.

## Standalone compatibility model — systemd PR `#20`

```text
base:      linux-fieldwork/oomd-reporter-registry@247f546ae1a108df0d24ea1b74854b50539c05a4
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
status:    success
```

Review found and repaired a grace-lifetime defect: a newer pending connection used to disarm grace, making the old timer stale and allowing disconnected old policy to remain indefinitely. The current model re-keys grace to the newer generation and proves eventual withdrawal by the current timer.

## Registry grace transaction — systemd PR `#22`

```text
base:      linux-fieldwork/oomd-wire-init-compat@bca6cedb1904aa1a9af56c2076bea6e156b04d26
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
digest:    sha256:5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
status:    success
```

The actual lifecycle and registry components now expose matching grace expiry. The registry withdraws retained policy before lifecycle commit. Stale, promoted, disconnected, and still-active cases are no-ops. A successful expiry clears only the disconnected old active generation and preserves the pending generation for a late first report.

This lane does not schedule a real timer or bind live callbacks.

## Initial-empty sender validation — systemd PR `#21`

```text
base:   linux-fieldwork/oomd-wire-init-compat@bca6cedb1904aa1a9af56c2076bea6e156b04d26
head:   50ed2893e37c66366401d51e4a9a579ad70a4210
run:    31020281327
status: queued at this checkpoint
```

The fail-closed generated product slice changes only the initial user-manager caller:

```text
allow_empty=false -> allow_empty=true
```

It requires an exact one-addition/one-deletion diff and compiles the explicit Meson target `./systemd:executable` with `--werror`.

Predecessor runs repaired two harness defects rather than product defects:

- injector uniqueness was originally global and collided with a pre-existing `allow_empty=true` system-manager call; it is now scoped to `manager_varlink_send_managed_oom_initial()`;
- the Meson target name `systemd` was ambiguous between a shared library and executable; the workflow now selects the executable target explicitly.

No final sender compile verdict is claimed until the exact-head run completes.

## Live integration requirements

1. initial user-manager send on the existing method with `allow_empty=true`;
2. first-report versus incremental classification per link;
3. legacy first-report detection on a pending link;
4. per-link authority and generation userdata;
5. generation-keyed initialization timer;
6. timer re-keying on superseding pending connections;
7. cancellation on promotion and disconnect;
8. stale callback and timer rejection;
9. serialized transactional registry ownership;
10. current user-link disconnect and PID 1 stream-loss withdrawal;
11. contributor diagnostics showing authority, generation, initialization mode, and effective winner.

## Authority

Internal controlled-fork work only. No public upstream contact is authorized or performed.
