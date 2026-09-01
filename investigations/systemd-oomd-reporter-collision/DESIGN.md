# Design — source-aware ManagedOOM subscriptions

Updated: `2026-08-01`  
Source revision: `systemd/systemd@6a863b4dc31adc49fdfdd5deba32ed1b115adda3`  
Status: design contract for controlled-fork implementation after the baseline VM result

## Problem statement

Current systemd-oomd stores one effective `OomdCGroupContext` per cgroup path and property. The receive path is given only a peer UID. A message with mode `auto` removes the whole path from the selected effective hashmap.

That representation loses the source of a policy. It cannot distinguish:

- PID 1 subscribing `user@<uid>.service` with `kill`;
- the nested user manager reporting its root `-.slice` for the same kernel cgroup path;
- reconnects and disconnects of a reporter;
- two live reports with different thresholds.

The fix needs to preserve source contributions and continue exposing one effective policy to the existing polling and action code.

## Exact source constraints

At the pinned revision:

- `Manager` owns effective path-to-`OomdCGroupContext` maps for swap, memory pressure, and rules;
- `OomdCGroupContext` contains path, live cgroup metrics, effective pressure limit/duration, preference, and rules, but no reporter identity;
- `process_managed_oom_message()` receives `(Manager*, uid_t, parameters)` and removes a whole effective path for `auto`;
- PID 1 updates arrive through oomd's unique client subscription and `process_managed_oom_reply()`;
- user-manager updates arrive through oomd's Varlink server and `process_managed_oom_request()`;
- Varlink exposes peer UID and PID plus server connect/disconnect callbacks;
- a reconnecting user manager sends an initial snapshot containing its explicit ManagedOOM policies;
- PID 1 allows one ManagedOOM subscriber and provides an initial snapshot plus continued notifications.

These surfaces are sufficient to attach an explicit source to every contribution and clean it up on connection loss.

## Proposed model

### Reporter authority

```c
typedef enum OomdReporterKind {
        OOMD_REPORTER_SYSTEM_MANAGER,
        OOMD_REPORTER_USER_MANAGER,
} OomdReporterKind;

typedef struct OomdReporter {
        OomdReporterKind kind;
        uid_t uid;
        Set *links;                 /* live Varlink connections for this authority */
        Set *contributions;         /* reverse index for bounded disconnect cleanup */
} OomdReporter;
```

The durable authority key is:

```text
(kind, uid)
```

`kind` distinguishes PID 1 from a root user's manager even though both can have UID 0. A link remains a liveness/generation object rather than the policy identity. This prevents an old connection's disconnect callback from deleting a newer connection's contribution for the same authority.

Peer PID should be retained in diagnostic connection metadata, not used as durable authority: user-manager PIDs change across restart and reconnect.

### Contribution identity

```c
typedef struct OomdPolicyKey {
        OomdReporter *reporter;
        OomdProperty property;
        char *path;
} OomdPolicyKey;

typedef struct OomdPolicyContribution {
        OomdPolicyKey key;
        ManagedOOMMode mode;        /* stored entries are explicit, normally kill */
        loadavg_t pressure_limit;
        usec_t pressure_duration;
        char **rules;
} OomdPolicyContribution;
```

Manager additions:

```c
Hashmap *managed_oom_reporters;      /* authority key -> OomdReporter */
Hashmap *managed_oom_contributions;  /* OomdPolicyKey -> contribution */
```

The existing monitored hashmaps remain the effective runtime view used by polling, candidate discovery, and action selection.

## Update semantics

For each incoming element:

1. resolve or create the reporter authority from the channel and peer UID;
2. validate cgroup ownership exactly as current code does;
3. form `(reporter, property, normalized path)`;
4. for `auto`, remove only that contribution;
5. for an explicit policy, insert or replace that contribution;
6. recompute the effective policy for only `(property, path)`;
7. update or remove the existing effective `OomdCGroupContext`;
8. reset property-specific timers only when the effective policy actually changes or disappears.

A message from one reporter can never directly delete another reporter's contribution.

## Disconnect and reconnect semantics

### User-manager server connections

On connect:

- resolve the `(USER_MANAGER, uid)` authority;
- add the link to its live-link set;
- retain peer PID only for diagnostics.

On disconnect:

- remove that link;
- if another link for the authority remains, leave contributions intact;
- on the last link, remove the authority's contributions and recompute all affected paths.

This generation-aware link set prevents a delayed disconnect from an old socket from deleting policy already reasserted through a new socket.

A reconnecting user manager sends its explicit initial snapshot, repopulating its authority contributions.

### PID 1 client subscription

Treat the unique PID 1 subscription as `(SYSTEM_MANAGER, 0)`. When the observed subscription terminates:

- remove the live link;
- withdraw system-manager contributions;
- recompute affected paths;
- allow any surviving user-manager contribution to become effective;
- reconnect and consume PID 1's initial snapshot normally.

This also fixes the adjacent stale-policy problem where a lost reporter can leave effective entries behind indefinitely.

## Effective-policy rule

### Authority ordering

```text
SYSTEM_MANAGER > USER_MANAGER
```

For a given `(property, path)`, select the highest-authority live contribution. PID 1 therefore governs a system unit such as `user@<uid>.service` while its explicit contribution exists. A user-manager policy becomes effective when the system manager has no explicit contribution for that path/property.

This rule has useful transition behavior:

- system `kill` + user `auto`: system `kill` remains effective;
- system `kill` + user `kill` with another limit: system tuple remains effective;
- system withdrawal + user `kill`: user tuple becomes effective without a new message;
- user withdrawal or disconnect: system tuple remains effective;
- system disconnect + user `kill`: user tuple becomes effective until PID 1 reconnects.

### Why avoid field-wise "strictest" merging

Taking the minimum limit and minimum duration independently can synthesize a policy no reporter requested. For example:

```text
reporter A: 80% for 1s
reporter B: 50% for 30s
field-wise result: 50% for 1s
```

That result is materially more aggressive than either input. Whole-contribution authority preserves an explainable policy and avoids accidental cross-products.

### Same-authority conflict

There should be one durable contribution per `(kind, uid, property, path)`. Multiple live links for the same authority update that same contribution. This matches the existing trust boundary: processes of a UID may already report policy for cgroups owned by that UID.

A later update from the same authority replaces its earlier tuple. Diagnostics must show the live connection generation that supplied the latest update.

## Property behavior

### ManagedOOMMemoryPressure

Select the complete tuple from the winning contribution:

```text
(mode, limit, duration)
```

Never combine limit and duration from different reporters.

### ManagedOOMSwap

Select the winning explicit contribution by authority. There are no threshold fields in the per-cgroup contribution.

### OOMRules

Select the winning complete rules list by authority. Do not union rules across authorities in the first implementation; union changes action semantics and timer ownership. Existing per-ruleset start times must be cleared only for rules removed from the newly effective list.

## Timer and runtime-context preservation

Recomputation should compare old and new effective policy before mutating runtime state.

- identical effective policy: preserve `OomdCGroupContext`, pressure history, and timers;
- changed limit or duration: preserve cgroup metrics, reset the limit-hit timer;
- effective policy disappears: remove effective context and all property-specific timers;
- lower-authority policy becomes visible after withdrawal: apply its complete tuple and reset timing from the authority transition.

The subscription layer must stay separate from live cgroup metric acquisition. Existing context refresh code should continue operating on effective maps.

## Diagnostics

Extend the dump consumed by `oomctl` with source information while preserving the existing effective block. Suggested shape:

```text
Path: /user.slice/user-1000.slice/user@1000.service
        Memory Pressure Limit: 50.00%
        Memory Pressure Duration: 30s
        Effective Source: system-manager uid=0
        Reported Policies:
                system-manager uid=0: kill 50.00% 30s
                user-manager uid=1000: auto
```

`auto` does not need to remain as a durable contribution, though the last received update may be retained in bounded diagnostic history if maintainers prefer. The essential requirement is that the effective source and all live explicit contributors are observable.

## Required controlled-fork test matrix

1. **Reported regression** — PID 1 `kill`; user-manager reload sends `auto`; PID 1 policy remains effective.
2. **Different explicit limits** — PID 1 and user manager report different tuples; complete PID 1 tuple wins.
3. **System withdrawal** — withdrawing PID 1 reveals the existing user contribution without requiring a new user update.
4. **User withdrawal** — user `auto` removes only the user contribution.
5. **User disconnect** — last user link removes user contributions while system policy remains.
6. **Reconnect generation** — old-link disconnect after a new link is active does not erase the new generation.
7. **PID 1 disconnect** — system contributions are withdrawn and a user contribution becomes effective.
8. **PID 1 reconnect** — initial snapshot restores system authority.
9. **Rules transition** — changing the winning rules list clears only timers for rules that cease to be effective.
10. **Cgroup disappearance** — effective runtime context is removed without leaking reporter/contribution objects.
11. **Diagnostic dump** — effective source and live contributors are represented deterministically.
12. **No-op update** — an identical update preserves pressure timing state.

## Implementation sequence

1. land baseline VM evidence without product changes;
2. add receive-boundary instrumentation in the controlled fork and capture exact source transitions;
3. add reporter and contribution types plus unit tests for authority/recompute logic;
4. route both PID 1 replies and user-manager requests through a reporter-aware process function;
5. bind user-server connect/disconnect callbacks and PID 1 subscription cleanup;
6. preserve existing effective maps as derived state;
7. add the focused integration regression and lifecycle cases;
8. extend dump diagnostics;
9. run focused OOMD tests, full unit tests, mkosi integration, sanitizers, and static checks;
10. only then prepare an upstream-shaped patch series, still without contacting upstream until separately authorized.

## Patch-series shape

A reviewable product series should likely be split as:

1. `oomd: model ManagedOOM reporter authorities`
2. `oomd: derive effective cgroup policy from source contributions`
3. `oomd: withdraw contributions on reporter disconnect`
4. `oomd: expose ManagedOOM policy sources in dump output`
5. `test: cover overlapping ManagedOOM reporters across reload`

Each commit should compile and have focused tests. The baseline reproduction and temporary instrumentation remain controlled-fork evidence rather than product commits.

## Non-goals

- changing PSI calculation or victim selection;
- changing cgroup ownership authorization;
- generic Varlink identity infrastructure outside the ManagedOOM path;
- merging arbitrary policies field by field;
- periodic reassertion as a substitute for ownership;
- special-casing only `user@.service` or only mode `auto`.

## Authority

This is an internal design record. No action was taken in `systemd/systemd`, and no upstream policy decision is attributed to maintainers.