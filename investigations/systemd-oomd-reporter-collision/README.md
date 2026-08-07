# systemd-oomd reporter collision across user-manager reload

Tracking: Linux Fieldwork issue `#140`, Linux Fieldwork PR `#245`, upstream report `systemd/systemd#43174`.  
Current review: `INDEPENDENT-REVIEW-2026-08-05-CONTINUATION.md`  
External contact: `false`

## Current status

`DEFECT REPRODUCED — BOUNDED LIVE CORRECTION GREEN — REDUCER/LIFECYCLE/REGISTRY/GRACE LAYERS GREEN — SENDER, LINK-ADAPTER, MESSAGE-ATOMICITY, AND STRICT-PARSER GATES ACTIVE — LIVE OOMD CALLBACK INTEGRATION NOT YET IMPLEMENTED`

Linux Fieldwork is the durable narrative and evidence home. `teamleaderleo/systemd` carries controlled executable experiments. Internal review is not upstream systemd approval.

## Defect and cause

A continuously running `user@<uid>.service` can disappear from systemd-oomd's monitored set after the nested user manager executes `daemon-reload`, although the service does not restart and its configured ManagedOOM policy remains `kill`.

PID 1 and the user manager can report the same kernel cgroup path. Current oomd receive state is keyed by property/path; reporter identity is used for authorization but is not retained as policy ownership. A later user-manager `auto` therefore removes the shared path record, including PID 1's still-live contribution.

```text
baseline run: 30693755971
job:          91352945746
artifact:     8817102322
outcome:      reproduced
sha256:       c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

Controls remained stable:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

## Selected architecture

```text
authority        = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key = (authority, property, cgroup path)
effective key    = (property, cgroup path)
```

Required behavior:

- sender-specific withdrawal;
- system-manager precedence while present;
- complete pressure tuples and rules lists selected without field mixing;
- lower-authority fallback after higher-authority withdrawal;
- authoritative complete first report, including empty state;
- monotonic per-authority connection generations;
- stale update, disconnect, and timer isolation;
- current disconnect or stream termination withdraws only that authority;
- message-level and policy-level atomicity;
- effective no-op updates preserve timing state.

## Exact-head-green executable layers

### Bounded live correction — `teamleaderleo/systemd#2`

```text
head:      2f04a87e25df0d56f01cab5de8c99472806929a7
run:       30916547610
artifact:  8895926721
sha256:    66ac9ee7c797dd776bb85c8705e93b4343deb8823b6bf6094ced10a6106c39d6
result:    test-oomd-util and focused TEST-55 VM passed; outcome=fixed
```

This proves the target behavior in a generated first slice, not the final architecture.

### Reducer and lifecycle — `teamleaderleo/systemd#3`

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
sha256:    a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
result:    test-oomd-policy and test-oomd-reporter-lifecycle passed
```

### Transactional registry continuity — `teamleaderleo/systemd#9`

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
sha256:    bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
result:    test-oomd-reporter-registry passed
```

The connected old active generation remains writable while replacement is pending. The pending generation is blocked until its complete snapshot commits, atomically replacing interim state and making the old generation stale.

### Mixed-version initialization grace — `teamleaderleo/systemd#20`

```text
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
sha256:    11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
result:    compatibility model passed with -Werror
```

Review repaired a timer-lifetime defect: a newer pending link must re-key and re-arm grace or disconnected old policy can survive indefinitely.

### Registry grace transaction — `teamleaderleo/systemd#22`

```text
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
sha256:    5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
result:    test-oomd-reporter-registry passed
```

Matching expiry withdraws retained old policy, clears only the disconnected old active generation, preserves the pending link, and ignores stale or promoted timers.

## Active controlled lanes

### Initial-empty user-manager sender — `teamleaderleo/systemd#21`

The existing method accepts `ReportManagedOOMCGroups(cgroups: ControlGroup[])`. The helper already constructs empty state; the generated product change is only:

```text
manager_varlink_send_managed_oom_initial(): allow_empty=false -> true
```

```text
current head: 7586cf535fbd93d91c9e76f3e1afd18e693e9417
state:        exact-head compile receipt pending
```

Predecessor failures were harness-only: an injector check scoped globally instead of to the initial sender, then ambiguous Meson targets. The current workflow selects `src/core/systemd:executable`, runs on branch pushes, and stores evidence outside the checkout.

### Callback-facing link adapter — `teamleaderleo/systemd#23`

```text
current head: 6180f35f349a65856ec51bf59e7297cae617cf0a
state:        exact-head compile/test receipt pending
```

The adapter maps live link IDs to `(authority, generation)` sessions and emits exact generation-qualified timer actions. Review repaired unbounded disconnected-link retention, retained-active ID aliasing, ambiguous timer cancellation, false dirty-tree checks, and unreliable stacked-PR triggering.

See `LINK-ADAPTER.md`.

### ManagedOOM message atomicity — `teamleaderleo/systemd#24`

```text
current head: 15d98da67cbd33aa6895db1a31471fbc7fe875bb
state:        exact-head compile/test receipt pending
```

One Varlink report contains a `cgroups[]` array. This lane adds one transactional array call through policy store, registry, and adapter so a malformed later typed element cannot leave earlier elements published. Complete first snapshots are fully prevalidated before candidate construction or generation promotion.

See `MESSAGE-ATOMICITY.md`.

### Strict owned message parser — `teamleaderleo/systemd#29`

```text
current head: 3b0b4712612f9dbaa0c26d27b7ccf96f80eb0cae
state:        exact-head compile/test receipt pending
```

The current live receiver explicitly skips malformed elements and continues processing the rest of the same message. PR `#29` adds an owned typed parser that rejects the complete `cgroups[]` report when any element, field, property, path, rule combination, or duplicate `(property, canonical path)` key is invalid.

Empty paths are canonicalized to `/`; JSON storage may be released immediately after successful parsing; no output batch is published until every element succeeds. Default resolution and cgroup-owner authorization remain in the next manager-side layer.

See `MESSAGE-PARSER.md`.

## Wire compatibility

New clients do not need a second method merely to express an empty initial state:

- new user manager to old oomd: `cgroups: []` is accepted as a no-op;
- old non-empty user manager to new oomd: its first existing complete report can initialize the generation;
- old empty user manager to new oomd: it sends nothing, so bounded compatibility grace remains necessary.

See `WIRE-COMPATIBILITY.md`.

## Linux Fieldwork checks

At head `56a5c911ffe03f375e95a49839ecc04e3362e8d7`:

```text
Verify systemd-oomd policy model       30980834388  success
Verify systemd-oomd reporter collision 30980834339  success
Linux Fieldwork CI                     30980834398  success
```

The four newer systemd exact heads and the refreshed Linux Fieldwork head are still queued at this checkpoint. No new pass is claimed.

## Durable records

```text
DESIGN.md
IMPLEMENTATION.md
CONNECTION-LIFECYCLE.md
WIRE-COMPATIBILITY.md
LINK-ADAPTER.md
MESSAGE-ATOMICITY.md
MESSAGE-PARSER.md
C-REDUCER.md
INDEPENDENT-REVIEW-2026-08-05-CONTINUATION.md
HANDOFF.md
artifacts/2026-08-01-current-main-vm-baseline.md
artifacts/2026-08-01-current-main-vm-receipt.json
artifacts/2026-08-01-current-main-causal-trace.txt
```

## Current disposition

- Baseline defect: **reproduced and causally attributed**.
- Bounded live correction: **exact-head green**.
- Reducer/lifecycle: **exact-head green**.
- Registry continuity: **exact-head green**.
- Mixed-version grace: **exact-head green after review repair**.
- Registry grace transaction: **exact-head green**.
- Initial-empty sender: **exact-head gate pending**.
- Callback-facing link adapter: **exact-head gate pending**.
- Message-atomicity layer: **exact-head gate pending**.
- Strict owned message parser: **exact-head gate pending**.
- Full-array authorization/default resolution, live Varlink callbacks/timers, PID 1 stream integration, and effective monitored-map publication: **not implemented**.
- Upstream-shaped candidate: **not ready**.
- Upstream contact: **none**.

## Next engineering move

Finish the four active exact-head gates. Then add the manager-side resolver that authorizes every parsed path and resolves default pressure values before calling one adapter transaction. Follow with live connect/disconnect callbacks, generation-keyed `sd_event` timers, PID 1 stream handling, atomic derived-map publication, contributor diagnostics, and a native VM matrix.

## Authority

All writes, reviews, and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No action has been taken in `systemd/systemd`.
