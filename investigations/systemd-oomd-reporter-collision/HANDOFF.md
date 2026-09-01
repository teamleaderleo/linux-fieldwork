# Handoff — systemd-oomd reporter ownership

Updated: `2026-08-06`  
State: `ACTIVE — DEFECT REPRODUCED; LIVE BOUNDED CORRECTION AND CORE MODEL LAYERS GREEN; FOUR EXACT-HEAD GATES ACTIVE; MANAGER INTEGRATION NEXT`  
Linux Fieldwork issue: `#140`  
Linux Fieldwork PR: `#245`  
Current review: `INDEPENDENT-REVIEW-2026-08-05-CONTINUATION.md`  
External contact: `false`

## Durable home

Use Linux Fieldwork for narrative, evidence, architecture contracts, independent-review findings, and handoff. Use `teamleaderleo/systemd` for executable controlled-fork experiments.

Internal review and repair are authorized in these owned repositories. Internal green is not upstream systemd approval.

## Proven baseline

```text
run:       30693755971
job:       91352945746
artifact:  8817102322
outcome:   reproduced
sha256:    c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

The exact `user@4711.service` registration disappeared after the user manager reported `auto` for the same cgroup path as PID 1's live 50% `kill` contribution. The service did not restart and its configured property did not change.

Root cause: oomd retains effective property/path state without reporter ownership.

## Architecture contract

```text
authority        = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key = (authority, property, cgroup path)
effective key    = (property, cgroup path)
```

Keep sender-specific withdrawal, whole-value system precedence, lower-authority fallback, authoritative complete first snapshots including empty state, monotonic generations, stale-callback isolation, current disconnect/stream withdrawal, whole-message and policy-level atomicity, and effective no-op timing preservation.

## Exact-head-green receipts

### Live bounded correction — systemd PR `#2`

```text
head:      2f04a87e25df0d56f01cab5de8c99472806929a7
run:       30916547610
artifact:  8895926721
sha256:    66ac9ee7c797dd776bb85c8705e93b4343deb8823b6bf6094ced10a6106c39d6
result:    unit and TEST-55 VM passed; outcome=fixed
```

### Reducer and lifecycle — systemd PR `#3`

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
sha256:    a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
result:    2/2 focused tests passed
```

### Registry continuity — systemd PR `#9`

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
sha256:    bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
result:    registry focused test passed
```

The connected old active generation remains writable while replacement is pending; the pending generation is blocked. Complete replacement atomically supersedes interim state and makes the old generation stale.

### Mixed-version grace — systemd PR `#20`

```text
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
sha256:    11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
result:    compatibility model passed with -Werror
```

A newer pending generation re-keys and re-arms grace so a stale timer cannot retain disconnected old policy forever.

### Registry grace transaction — systemd PR `#22`

```text
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
sha256:    5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
result:    registry focused test passed
```

Matching expiry withdraws retained old policy, clears only the disconnected old active generation, preserves the pending generation, and ignores stale or promoted timers.

## Active gates

### Initial-empty sender — systemd PR `#21`

```text
head:   7586cf535fbd93d91c9e76f3e1afd18e693e9417
status: exact-head compile receipt pending
```

The generated product change is only `manager_varlink_send_managed_oom_initial(): allow_empty=false -> true`. The current workflow compiles `src/core/systemd:executable`; predecessor failures were harness-only.

### Callback-facing link adapter — systemd PR `#23`

```text
head:   6180f35f349a65856ec51bf59e7297cae617cf0a
status: exact-head compile/test receipt pending
```

The adapter maps live link IDs to registry sessions and emits generation-qualified arm/replace/cancel timer actions. Read `LINK-ADAPTER.md`.

### Message atomicity — systemd PR `#24`

```text
head:   15d98da67cbd33aa6895db1a31471fbc7fe875bb
status: exact-head compile/test receipt pending
```

The complete typed update array is one transaction through adapter, registry, and policy store. Complete first snapshots are prevalidated before generation promotion. Read `MESSAGE-ATOMICITY.md`.

### Strict owned message parser — systemd PR `#29`

```text
head:   3b0b4712612f9dbaa0c26d27b7ccf96f80eb0cae
status: exact-head compile/test receipt pending
```

The parser owns and validates the entire existing `cgroups[]` method payload before exposing a typed batch. A malformed later element, unknown field/property, bad path, incoherent rules entry, or duplicate `(property, canonical path)` rejects the whole message. Empty path is canonicalized to `/`, and the JSON variant may be released immediately after success.

The parser deliberately does not read cgroupfs, resolve manager defaults, call the registry, or modify live `oomd-manager.c`. Read `MESSAGE-PARSER.md`.

## Linux Fieldwork gate

Last completed green checkpoint:

```text
head:                56a5c911ffe03f375e95a49839ecc04e3362e8d7
policy model:        30980834388  success
collision verifier: 30980834339  success
Linux Fieldwork CI:  30980834398  success
```

The current refreshed Fieldwork head and all four active systemd heads are queued. Do not promote them without exact receipts.

## Immediate engineering sequence

1. Inspect and record exact-head completion for PRs `#21`, `#23`, `#24`, and `#29`.
2. Repair only attributable source or harness failures and move every receipt with its exact head.
3. Add a manager-side resolver that authorizes every parsed canonical path and resolves default pressure values into one owned policy array.
4. Call the adapter exactly once as a complete snapshot or incremental transaction.
5. Publish derived monitored-map changes only after registry success.
6. Bind user-manager Varlink connect/disconnect callbacks and attach `(authority, generation)` link state.
7. Translate adapter arm/cancel actions into generation-keyed `sd_event` timers.
8. Handle PID 1 subscription termination/reconnect as the system authority lane.
9. Add cgroup-disappearance cleanup, timing preservation, and contributor diagnostics.
10. Run a native VM matrix before promotion to the user's review desk.
11. Keep all work internal until upstream contact is separately authorized.

## Read order

```text
README.md
DESIGN.md
IMPLEMENTATION.md
CONNECTION-LIFECYCLE.md
WIRE-COMPATIBILITY.md
LINK-ADAPTER.md
MESSAGE-ATOMICITY.md
MESSAGE-PARSER.md
INDEPENDENT-REVIEW-2026-08-05-CONTINUATION.md
```

## Authority

All writes and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No action has been taken in `systemd/systemd`.
