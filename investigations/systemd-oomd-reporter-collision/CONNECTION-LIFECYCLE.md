# ManagedOOM reporter connection lifecycle

Updated: `2026-08-02`  
Source revision: `systemd/systemd@6a863b4dc31adc49fdfdd5deba32ed1b115adda3`  
Status: refined lifecycle contract after current-main reproduction and source review

## Why a live-link set is insufficient

The initial design treated `(reporter kind, uid)` as durable authority and retained contributions while any link for that authority remained alive. That prevents an old-link disconnect from deleting policy reasserted on a newer link, but it misses an empty-restart case.

Current user-manager reconnect code builds an initial list with:

```c
build_managed_oom_cgroups_json(m, /* allow_empty= */ false, &v)
```

If the restarted user manager has no explicit ManagedOOM policies, the builder returns no object and the client sends no initial method call.

A naive generation model can therefore do this:

```text
old user-manager link: explicit kill contribution
new user-manager link: connects with no explicit policies
new link sends no initial message
old link disconnects while new link remains
last-link cleanup does not run
old contribution survives indefinitely
```

The server needs an explicit full-state boundary for each new connection generation, including an empty state.

## Existing channel behavior

### User-manager channel

`systemd-oomd` creates a Varlink server with `SD_VARLINK_SERVER_INHERIT_USERDATA` and binds `ReportManagedOOMCGroups`, but it does not currently bind connect or disconnect callbacks.

The user manager:

1. connects to `VARLINK_PATH_MANAGED_OOM_USER`;
2. attaches the link to its event loop;
3. queues an initial ManagedOOM update;
4. currently skips that update when no explicit policy exists;
5. sends later per-unit updates as one-way method calls.

### PID 1 channel

`systemd-oomd` connects to PID 1 and observes `SubscribeManagedOOMCGroups`.

PID 1's subscription response already has full-snapshot semantics because its builder is called with `allow_empty=true`. Continued replies then carry incremental updates.

When the stream stops, `process_managed_oom_reply()` currently only closes `m->varlink_client`. Monitored policy state is left untouched until another update or cgroup refresh changes it.

## Revised authority and session model

Durable authority remains:

```text
(SYSTEM_MANAGER, uid=0)
(USER_MANAGER, uid)
```

Connection state is separate:

```c
typedef struct OomdReporterSession {
        OomdReporterAuthority authority;
        sd_varlink *link;          /* borrowed while connected */
        uint64_t generation;
        bool snapshot_received;
        pid_t peer_pid;            /* diagnostics only */
} OomdReporterSession;
```

Each authority has one **current initialized generation**. Older connections may remain alive briefly, but they become stale after a newer generation commits its first snapshot.

## User-manager snapshot handshake

### Client change

Always send an initial call, even when the explicit policy list is empty:

```c
build_managed_oom_cgroups_json(m, /* allow_empty= */ true, &v)
```

No protocol schema change is required; `cgroups: []` is already valid input.

### Server connect

Bind established Varlink callbacks:

```c
sd_varlink_server_bind_connect(s, managed_oom_user_connect)
sd_varlink_server_bind_disconnect(s, managed_oom_user_disconnect)
```

On connect:

- read peer UID and PID;
- create a pending session generation;
- do not change durable contributions yet;
- keep Manager as link userdata so existing method callbacks continue receiving `Manager *`;
- store session records in a manager-owned hashmap keyed by the borrowed `sd_varlink *`.

### First method call

The first `ReportManagedOOMCGroups` call from a pending session is a complete snapshot for that authority.

Process it transactionally:

1. parse and validate every element into staged contribution values;
2. validate path ownership using peer UID;
3. derive all affected effective policies in temporary state;
4. if any allocation, parse, or invariant check fails, retain the previous initialized generation unchanged;
5. on success, replace all prior contributions for that authority with the snapshot, including the empty snapshot;
6. mark this session as the current initialized generation;
7. mark older sessions stale;
8. publish only effective transitions.

A partial snapshot must never be committed.

### Later method calls

Only the current initialized generation may send incremental updates.

- current generation: apply one authority-scoped update transaction;
- stale generation: ignore and log at debug level;
- pending generation sending a second call before its snapshot commits: reject or close as protocol misuse.

This prevents buffered messages from an old connection from overwriting state restored by a new manager.

## User-manager disconnect

### Pending or stale session disconnect

Remove the session record only. Do not change contributions.

### Current initialized session disconnect

Withdraw all contributions for that authority immediately, even if stale older links are still technically open. Recompute affected effective keys and expose surviving lower/higher authority contributions.

Do not reactivate an older stale generation.

This is stronger and safer than last-link cleanup.

## PID 1 subscription lifecycle

Treat each successful `SubscribeManagedOOMCGroups` observation as a system-manager generation.

### Initial reply

The first reply is a complete snapshot and may be empty. Replace the previous system authority snapshot atomically, then mark the link initialized/current.

### Continued replies

Apply incremental system-authority updates only from the current initialized link.

### Stream termination

When `SD_VARLINK_REPLY_CONTINUES` is absent or a local/error termination closes the current link:

1. withdraw all system-manager contributions;
2. recompute affected effective policies;
3. reveal surviving user contributions immediately;
4. close and clear `m->varlink_client`;
5. allow the existing timer-driven reconnect path to acquire a new stream;
6. replace system contributions from the next complete initial snapshot.

If the stream terminates before its first snapshot commits, leave the previous initialized generation unchanged until an explicit policy decision is made. The preferred implementation, however, should retire the previous link when establishing a new observe request so only one system generation is pending/current.

## Data structures

Manager additions should be distinct from policy values:

```c
Hashmap *managed_oom_sessions;   /* borrowed sd_varlink* -> session */
Hashmap *managed_oom_reporters;  /* authority -> authority state */
```

Authority state contains:

```c
OomdReporterSession *current;
Set *contributions;              /* reverse index for bounded replace/withdraw */
uint64_t next_generation;
```

Do not change link userdata away from `Manager *`; method dispatch depends on inherited userdata.

## Atomic snapshot API

The reducer needs an explicit snapshot operation in addition to incremental update:

```c
int oomd_policy_replace_authority_snapshot(
                OomdPolicyStore *store,
                OomdReporterAuthority authority,
                OrderedHashmap *staged_contributions,
                Set **ret_changed_effective_keys);
```

Requirements:

- all-or-nothing replacement;
- empty snapshot supported;
- old and new effective tuples compared before runtime timer mutation;
- deterministic changed-key set;
- no message-arrival-order policy between reporter classes;
- no field-wise tuple merging.

## Required lifecycle tests

1. **Empty reconnect snapshot** — old explicit policy is cleared by a newer empty snapshot before old disconnect.
2. **Stale update rejection** — an old link cannot update policy after a newer snapshot commits.
3. **Stale disconnect isolation** — old-link disconnect does not remove new-generation policy.
4. **Current disconnect withdrawal** — current contributions are withdrawn even if stale links remain open.
5. **Pending disconnect** — a new link that disconnects before its snapshot leaves current policy unchanged.
6. **Snapshot rollback** — malformed or allocation-failed snapshot leaves the prior generation and effective policy unchanged.
7. **Snapshot replacement** — paths absent from the new complete snapshot are withdrawn.
8. **PID 1 empty snapshot** — reconnect can explicitly replace system policy with no contributions.
9. **PID 1 termination fallback** — system stream loss reveals an existing user contribution.
10. **No stale reactivation** — an older system/user generation never becomes current again after newer-generation failure or disconnect.

## Integration probes

### User-manager empty restart

1. establish an explicit user-root policy;
2. restart the user manager with no persistent policy;
3. verify an empty initial snapshot is sent;
4. verify the old contribution disappears before/independent of old-link disconnect ordering.

### Reconnect overlap

Use temporary receive-boundary logging to record:

```text
authority uid
peer pid
session generation
snapshot/incremental classification
stale/current status
property/path/mode
```

Force reconnect overlap and prove old buffered updates are ignored after the new snapshot commits.

### PID 1 stream loss

Use a controlled PID 1 daemon-reexec or deliberately closed observer connection, then verify:

- system contributions withdraw;
- user fallback becomes effective;
- reconnect initial snapshot restores system precedence;
- service identity and cgroup remain stable.

## Product series impact

The lifecycle work should be split after the pure reducer:

1. always send user-manager initial snapshots, including empty;
2. model reporter sessions and generations;
3. replace authority state on first-message snapshots;
4. reject stale-generation updates;
5. withdraw current generation on disconnect/stream termination;
6. add reconnect overlap and empty-snapshot integration tests.

## Authority

This is internal source analysis and design in `teamleaderleo`-owned repositories. No upstream interaction occurred.
