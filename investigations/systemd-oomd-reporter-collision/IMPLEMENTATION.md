# C implementation map — source-aware ManagedOOM policy

Updated: `2026-08-02`  
Target source: `systemd/systemd@6a863b4dc31adc49fdfdd5deba32ed1b115adda3`  
Status: implementation contract derived from reproduced runtime ordering and executable policy model

## File layout

Keep policy ownership and reduction independent from live cgroup metrics:

```text
src/oom/oomd-policy.h
src/oom/oomd-policy.c
src/oom/test-oomd-policy.c
```

`oomd-manager.c` should consume this layer. `oomd-util.c` and `OomdCGroupContext` remain responsible for cgroup metric acquisition, pressure history, and kill selection.

Do not put reporter bookkeeping into `OomdCGroupContext`. A context is derived runtime state and is recreated during polling; reporter contributions have a different lifecycle.

## Core types

```c
typedef enum OomdReporterKind {
        OOMD_REPORTER_SYSTEM_MANAGER,
        OOMD_REPORTER_USER_MANAGER,
        _OOMD_REPORTER_KIND_MAX,
        _OOMD_REPORTER_KIND_INVALID = -EINVAL,
} OomdReporterKind;

typedef enum OomdPolicyProperty {
        OOMD_POLICY_SWAP,
        OOMD_POLICY_MEMORY_PRESSURE,
        OOMD_POLICY_RULES,
        _OOMD_POLICY_PROPERTY_MAX,
        _OOMD_POLICY_PROPERTY_INVALID = -EINVAL,
} OomdPolicyProperty;

typedef struct OomdReporterAuthority {
        OomdReporterKind kind;
        uid_t uid;
} OomdReporterAuthority;

typedef struct OomdPolicyValue {
        ManagedOOMMode mode;       /* durable entries are explicit KILL */
        loadavg_t pressure_limit;
        usec_t pressure_duration_usec;
        char **rules;
} OomdPolicyValue;

typedef struct OomdPolicyContribution {
        OomdReporterAuthority authority;
        OomdPolicyProperty property;
        char *path;
        OomdPolicyValue value;
        uint64_t generation;
} OomdPolicyContribution;

typedef struct OomdEffectivePolicy {
        OomdReporterAuthority authority;
        OomdPolicyValue value;
        uint64_t epoch;
} OomdEffectivePolicy;
```

Reporter state:

```c
typedef struct OomdReporter {
        OomdReporterAuthority authority;
        Set *links;          /* live sd_varlink* identities; pointer hash ops */
        Set *contributions;  /* reverse index of contribution objects */
        uint64_t generation;
} OomdReporter;
```

Store:

```c
typedef struct OomdPolicyStore {
        Hashmap *reporters;       /* authority -> OomdReporter */
        Hashmap *contributions;   /* (authority, property, path) -> contribution */
        Hashmap *effective;       /* (property, path) -> effective policy */
        uint64_t next_epoch;
} OomdPolicyStore;
```

Final code should use typed key structs and private hash operations, not serialized string keys.

## Public reducer API

```c
int oomd_policy_store_new(OomdPolicyStore **ret);
OomdPolicyStore *oomd_policy_store_free(OomdPolicyStore *store);

int oomd_policy_reporter_connect(
                OomdPolicyStore *store,
                OomdReporterAuthority authority,
                sd_varlink *link);

int oomd_policy_reporter_disconnect(
                OomdPolicyStore *store,
                OomdReporterAuthority authority,
                sd_varlink *link,
                Set **ret_changed_effective_keys);

int oomd_policy_update(
                OomdPolicyStore *store,
                OomdReporterAuthority authority,
                OomdPolicyProperty property,
                const char *path,
                const OomdPolicyValue *value, /* NULL means AUTO/withdraw */
                bool *ret_effective_changed);

int oomd_policy_drop_path(
                OomdPolicyStore *store,
                const char *path,
                Set **ret_changed_effective_keys);

const OomdEffectivePolicy *oomd_policy_get_effective(
                OomdPolicyStore *store,
                OomdPolicyProperty property,
                const char *path);

int oomd_policy_dump_sources(
                OomdPolicyStore *store,
                OomdPolicyProperty property,
                const char *path,
                FILE *f,
                const char *prefix);
```

The API returns changed effective keys so `oomd-manager.c` updates only affected runtime maps.

## Update transaction

An incoming element must be atomic:

1. validate reporter is live;
2. validate normalized path and current UID ownership rules;
3. construct or locate the contribution key;
4. stage insertion, replacement, or withdrawal;
5. reduce all contributions for `(property, path)`;
6. reject an invalid equal-priority ambiguity before publishing state;
7. commit contribution and effective-policy changes together;
8. report whether the effective tuple changed.

If allocation or reduction fails, both contribution and effective maps must remain byte-for-byte equivalent to the pre-update state. The executable specification has a dedicated rollback regression for this.

## Reduction rule

Authority rank:

```text
SYSTEM_MANAGER > USER_MANAGER
```

Select one complete contribution. Never merge fields across sources.

For memory pressure, the indivisible tuple is:

```text
(mode, limit, duration)
```

For rules, the indivisible tuple is the complete ordered/deduplicated rule list. Do not union rule lists in the first implementation.

Equal-rank contributions from different user UIDs for the same path should be impossible after cgroup-owner validation. Treat their appearance as an invariant violation or reject the update with a clear error; do not choose by message arrival time.

## Epoch and timer semantics

Every effective `(property, path)` has an epoch.

- identical effective authority and tuple: preserve epoch and runtime pressure timers;
- lower-authority update hidden by a live system policy: preserve epoch;
- changed winning tuple: increment epoch and reset property-specific timing;
- authority transition with an otherwise identical tuple: increment epoch, because ownership and disconnect behavior changed;
- effective policy disappears: remove context and clear timers;
- effective policy reappears: allocate a fresh epoch and timing state.

This keeps the reducer deterministic and prevents no-op reloads from resetting pressure-duration accounting.

## Manager integration points

### User-manager request channel

`process_managed_oom_request()` already has the accepted `sd_varlink *` and peer UID. Resolve:

```text
authority = (USER_MANAGER, peer_uid)
```

Use `sd_varlink_get_peer_pid()` only for diagnostics. The PID is not durable authority.

Bind both callbacks in `manager_varlink_init()`:

```c
sd_varlink_server_bind_connect(...)
sd_varlink_server_bind_disconnect(...)
```

The connect callback adds the link to the authority's live-link set. The disconnect callback removes it and withdraws contributions only when it was the last live link for that authority.

### PID 1 subscription channel

`process_managed_oom_reply()` is a separate channel initiated by oomd and is therefore unambiguously:

```text
authority = (SYSTEM_MANAGER, 0)
```

Register the link when the subscription is established. When the continued reply stream terminates, withdraw system-manager contributions before reconnecting. Surviving user-manager contributions then become effective until PID 1's initial snapshot is consumed.

### Receive processing

Change the internal processing signature from UID-only to explicit authority:

```c
process_managed_oom_message(
        Manager *m,
        OomdReporterAuthority authority,
        sd_json_variant *parameters);
```

Keep ownership validation based on peer UID. Policy identity and access control are related but separate concerns.

## Deriving existing runtime maps

The current maps remain:

```text
monitored_swap_cgroup_contexts
monitored_mem_pressure_cgroup_contexts
monitored_rules_cgroup_contexts
```

After a reducer update:

1. fetch old and new effective policy for the affected key;
2. if unchanged, do nothing;
3. if removed, unref/remove the effective `OomdCGroupContext` and clean property timers;
4. if added, insert/acquire the context and copy the complete effective tuple;
5. if changed, retain live metric fields where safe, replace policy fields, and reset only the affected timers;
6. toggle event sources from effective-map emptiness exactly as current code does.

Do not rebuild all monitored maps for one message.

## OOMRules cleanup

Current code clears ruleset `start_times` directly during an `auto` message. With source-aware policy this must move to effective-policy transition handling.

Compare old and new effective rule lists:

- clear timers only for rules no longer effective;
- preserve timers for unchanged rules;
- on authority transition with identical rules, choose deliberately whether timing is preserved. The current design resets the epoch but can preserve rule timers if the effective action tuple is identical; encode this explicitly in tests.

## Diagnostics

Keep existing effective `oomctl` fields and append source information:

```text
Effective Source: system-manager uid=0
Reported Policies:
        system-manager uid=0: kill limit=50.00% duration=30s
        user-manager uid=4711: kill limit=70.00% duration=5s
```

A withdrawn `auto` is not a durable contribution. Optional bounded last-update history may show it for debugging, but must not affect reduction.

Sort contributors deterministically by authority rank, UID, property, and path.

## Focused C unit-test matrix

`src/oom/test-oomd-policy.c` should cover without cgroups or Varlink sockets:

1. reported system `kill` plus user `auto` collision;
2. complete-tuple system precedence under conflicting limits/durations;
3. system withdrawal revealing an existing user tuple;
4. user withdrawal leaving system effective;
5. last-link user disconnect cleanup;
6. old-generation disconnect while a new link remains;
7. PID 1 disconnect revealing user policy;
8. PID 1 reconnect restoring system authority;
9. complete OOMRules selection without union;
10. path disappearance cleanup;
11. deterministic source dump;
12. no-op update preserving epoch;
13. equal-priority ambiguity rejection;
14. atomic rollback after rejected update;
15. allocation-failure rollback using systemd's allocation-failure test hooks where practical.

## Integration-test sequence

After the reducer unit tests are green:

1. route receive paths through the store without changing effective behavior;
2. add source-aware reduction and run the existing reproduced testcase;
3. assert PID 1 remains effective after user reload;
4. add explicit conflicting-limit case;
5. add user disconnect/reconnect generation case;
6. add PID 1 disconnect/reconnect case;
7. run full `TEST-55-OOMD`, unit tests, sanitizer matrix, lint, and mkosi variants.

## Proposed commit series

1. `oomd: add source-aware ManagedOOM policy reducer`
2. `oomd: identify system and user ManagedOOM reporters`
3. `oomd: derive monitored contexts from reporter contributions`
4. `oomd: withdraw reporter contributions on disconnect`
5. `oomd: expose ManagedOOM policy sources in diagnostics`
6. `test: cover overlapping ManagedOOM reporters across reload`

Temporary `FIELDWORK_*` instrumentation and experiment workflows do not belong in the product series.

## Authority

This is internal design work in `teamleaderleo`-owned repositories. It is not an upstream proposal or contact.
