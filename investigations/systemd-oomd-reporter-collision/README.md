# systemd-oomd ManagedOOM reporter collision

## TL;DR

`systemd-oomd` currently stores ManagedOOM subscriptions by cgroup path and property, while updates arrive from two authorities: PID 1 and per-user managers. An `auto` update removes the path from the shared hashmap without retaining which manager supplied the active `kill` subscription. This gives a direct mechanism for the reported failure where `user@<uid>.service` is registered by PID 1, then disappears after that user's `daemon-reload` while user-manager-owned scopes continue working.

The next decisive step is a current-head VM trace that records sender UID + path + property + mode for every ManagedOOM message around the user-manager reload. That will identify the exact colliding user-manager unit and decide between a source-aware receiver fix and a narrower producer fix.

## Explain like I'm five

Two managers can talk to oomd about cgroups. Oomd currently files both reports under the cgroup path alone. If manager A says `kill` for `/user@1000.service` and manager B later says `auto` for that same path, oomd deletes the entry and forgets manager A still wanted it. Example from the report: PID 1 registers `user@1000.service` -> the user runs `systemctl --user daemon-reload` -> the monitored entry vanishes and stays gone.

## Why care

The affected entry is a memory-pressure guardrail for the user's service tree. The service can remain active with `ManagedOOMMemoryPressure=kill` while oomd silently stops monitoring it. Desktop/user-unit reloads can therefore remove protection without stopping `systemd-oomd` or producing an obvious service failure.

## Current state

- State: `SCOPING`
- Exact working head: `teamleaderleo/linux-fieldwork@7dab6a8ff346117f95a5c03dd1af7bcc4f104510` plus this investigation branch
- Latest authoritative gate or artifact: source-read against `systemd/systemd@9b75d9bc66dc4f64e4fdd33603d199d374c0873b`; upstream report includes clean-room reproduction on systemd 261 and a second reproduction on 259
- First incomplete step: capture the exact ManagedOOM message sequence and sender identity across `systemctl --user daemon-reload`
- Cleanup state: source-read only; no VM or service state created by this worker
- Next safe action: run an instrumented current-head VM reproduction in the owned fork/test environment
- External-contact state: no upstream mutation authorized or performed by this worker

## Intent and precedent

Primary sources:

- https://github.com/systemd/systemd/issues/43174
- https://github.com/systemd/systemd/blob/9b75d9bc66dc4f64e4fdd33603d199d374c0873b/src/core/varlink.c
- https://github.com/systemd/systemd/blob/9b75d9bc66dc4f64e4fdd33603d199d374c0873b/src/oom/oomd-manager.c
- https://github.com/systemd/systemd/blob/9b75d9bc66dc4f64e4fdd33603d199d374c0873b/test/units/TEST-55-OOMD.sh

Source observations:

1. PID 1 exposes `SubscribeManagedOOMCGroups`. The initial reply is a complete array of active non-`auto` ManagedOOM policies. Later PID 1 unit changes are sent as notifications on the retained varlink connection.
2. A user manager connects to oomd separately and calls `io.systemd.oom.ReportManagedOOMCGroups`. Its initial send contains its active non-`auto` policies; later unit updates include all ManagedOOM properties, including `auto`.
3. `process_managed_oom_message()` in oomd gets the peer UID for each message and validates that a non-root sender owns the cgroup path.
4. After validation, sender identity is discarded. The monitored maps are keyed by cgroup path.
5. For `message.mode == MANAGED_OOM_AUTO`, oomd executes `hashmap_remove(monitor_hm, empty_to_root(message.path))`. That removal has no source/authority discriminator.
6. For `kill`, `oomd_insert_cgroup_context()` inserts or reuses the path and updates the effective limit/duration. This likewise carries no reporter identity.
7. The issue reports that only entries supplied by PID 1 disappear after a user-manager reload, while user-manager-owned `app-*.scope` entries survive. Restarting oomd restores the PID 1 entry until the next reload.

Interpretation: the receiver currently models one effective subscription per path/property even though the protocol permits reports from multiple manager connections whose cgroup namespaces overlap at the user-manager root.

## Question

Does `systemctl --user daemon-reload` cause the user manager to emit an `auto` ManagedOOM update for the same cgroup path that PID 1 previously registered as `kill`, and if so, what source-aware rule preserves both managers' intended state across later transitions?

## Source

- Project: systemd
- Requested revision or package version: current canonical `main` at investigation start
- Resolved commit: `9b75d9bc66dc4f64e4fdd33603d199d374c0873b`
- Candidate source commit: pending trace
- Local source path: owned fork `teamleaderleo/systemd`
- Import metadata: GitHub source-read; no local import

## Environment

The upstream issue reports successful reproductions on:

- systemd 261, Arch Linux, kernel 7.1.3-arch1-3, cgroup v2
- systemd 259, Ubuntu 26.04, kernel 7.0.0-28-generic

Candidate execution environment for this investigation is pending. The authoritative next run should use a VM/current systemd build because the behavior spans PID 1, a user manager, varlink, cgroup ownership, and oomd.

## Baseline behavior

Upstream reproduction summary:

```sh
# PID 1 has ManagedOOMMemoryPressure=kill on user@.service
systemctl daemon-reload
systemctl enable --now systemd-oomd
useradd -m testu
loginctl enable-linger testu
sleep 15

oomctl   # includes /user.slice/user-1000.slice/user@1000.service

runuser -u testu -- env XDG_RUNTIME_DIR=/run/user/1000 \
    systemctl --user daemon-reload

oomctl   # user@1000.service entry is gone
```

The report checked again at +5 s, +15 s, +30 s, and after 16 minutes. Restarting `systemd-oomd` restores the entry. On the second host, `user@1000.service` remained continuously running with zero restarts and retained `ManagedOOMMemoryPressure=kill`.

## Hypothesis or candidate

### Current leading mechanism

The monitored hashmaps collapse multiple reporters onto one `path -> OomdCGroupContext` entry. A user-manager `auto` report for an overlapping root cgroup can therefore remove a PID-1 `kill` report for the same path.

### Decisive trace

Temporarily instrument `process_managed_oom_message()` in the owned fork to record, for each element:

```text
peer_uid  path  property  mode  limit  duration
```

Capture the sequence during:

1. oomd startup and PID-1 initial subscription;
2. user-manager startup/initial report;
3. baseline `oomctl`;
4. `systemctl --user daemon-reload`;
5. the first disappearance from `oomctl`;
6. a later user-manager unit transition that should retain its own scope entry.

Required distinguishing observation:

```text
uid=0     path=/user.slice/user-1000.slice/user@1000.service  ManagedOOMMemoryPressure  kill
uid=1000  path=/user.slice/user-1000.slice/user@1000.service  ManagedOOMMemoryPressure  auto
```

If that pair occurs immediately around the loss, source collapse is demonstrated.

### Candidate families after the trace

**A. Source-aware receiver state**

Track reports by source identity plus path/property and derive the effective monitored entry from the active reporters. An `auto` transition removes only that reporter's contribution. This matches the protocol topology and handles later `kill -> auto` transitions without clobbering another manager.

Questions that must be answered before implementation:

- What is the durable source key for the PID-1 streaming connection versus user-manager senders: peer UID, connection identity, manager scope, or an explicit protocol field?
- What happens when two reporters both request `kill` with different memory-pressure limits/durations?
- How is a reporter's entire contribution removed when its varlink connection disappears?
- Can the same UID own multiple manager connections whose reports need separate lifetimes?

**B. Producer-side exclusion for the overlapping user-manager root**

Skip the user manager's root-cgroup report if that unit is outside the user manager's ManagedOOM authority. This is smaller only if source/docs/tests prove the user manager must never configure ManagedOOM on that root. A blanket skip of `auto` is insufficient because a user manager must be able to withdraw its own prior `kill` subscription.

The trace plus unit identity decides whether B is valid. Until then A is the safer semantic model.

## Reproduction

Use TEST-55-OOMD or a dedicated integration subtest with a real user manager. Minimum contract:

```sh
# arrange ManagedOOMMemoryPressure=kill for user@.service
# start oomd and a lingering test user
# assert user@UID.service appears in oomctl
# record its active timestamp and restart count
# trigger user-manager daemon-reload
# assert user@UID.service remains in oomctl
# assert service active timestamp/restart count are unchanged
# assert a user-manager-owned managed scope still appears
```

For the diagnostic run, emit the receiver trace described above. For a final candidate, remove diagnostic logging and assert externally visible state plus any focused unit-level source-accounting test.

Negative controls:

- reload PID 1 without reexec and verify expected subscription behavior;
- change a user-manager-owned unit from `kill` to `auto` and verify its own contribution disappears;
- disconnect/restart a user manager and verify stale contributions do not survive;
- restart oomd and verify both producer classes rebuild state correctly.

## Results

Source-read result only at this checkpoint. The upstream issue's runtime reproduction is strong evidence for the symptom; this worker has not yet executed the current-head VM trace.

Open-PR overlap refresh found no open canonical systemd PR matching issue `43174` at this checkpoint.

## Interpretation

The receiver has a demonstrated information-loss boundary: it receives sender UID, uses it for authorization, then throws it away before mutating a path-keyed subscription map. That is enough to reject simplistic patches that treat every `auto` as authoritative for the whole path.

The exact colliding user-manager unit remains to be observed. That identity decides whether the right product fix belongs in producer filtering or receiver state ownership.

## Evidence boundary

- Current-head source is read; current-head runtime reproduction remains pending.
- The issue's two-host reproduction belongs to the upstream reporter, not this worker.
- The exact user-manager message that removes the entry has not yet been captured.
- No final source patch is proposed until reporter identity, lifecycle, and multi-reporter limit semantics are resolved.
- DCO/sign-off identity must be supplied by the human contributor if a later candidate is prepared for upstream submission; no identity will be inferred here.

## Next step

1. Build/run current `systemd/systemd@9b75d9bc66dc4f64e4fdd33603d199d374c0873b` in an isolated VM or existing TEST-55-OOMD harness.
2. Instrument `process_managed_oom_message()` with sender UID + message fields.
3. Reproduce the reload loss and retain the exact ordered trace.
4. Identify the user-manager unit corresponding to the colliding path/update.
5. Decide receiver source-accounting versus producer exclusion from that evidence.
6. Add failure, withdrawal, disconnect, restart, and clean-rerun controls before promoting a source candidate.

## Authority

Canonical `systemd/systemd` remains read-only to this worker. No upstream issue comment, pull request, review, reaction, branch, or other mutation has been made.