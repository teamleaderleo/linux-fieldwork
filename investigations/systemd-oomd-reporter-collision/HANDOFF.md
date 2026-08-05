# Handoff — systemd-oomd reporter ownership

Updated: `2026-08-05`  
State: `ACTIVE — DEFECT REPRODUCED; LIVE BOUNDED CORRECTION AND MODEL LAYERS GREEN; INITIAL-EMPTY SENDER GATE ACTIVE; NATIVE CALLBACK INTEGRATION NEXT`  
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

Keep sender-specific withdrawal, whole-value system precedence, lower-authority fallback, authoritative complete first snapshots including empty state, monotonic generations, stale-callback isolation, current disconnect/stream withdrawal, atomic mutation, and effective no-op timing preservation.

## Exact executable receipts

### Live bounded correction — systemd PR `#2`

```text
head:      2f04a87e25df0d56f01cab5de8c99472806929a7
run:       30916547610
artifact:  8895926721
digest:    sha256:66ac9ee7c797dd776bb85c8705e93b4343deb8823b6bf6094ced10a6106c39d6
result:    unit and TEST-55 VM passed; outcome=fixed
```

This proves the target behavior in a generated first slice, not the final architecture.

### Reducer and lifecycle — systemd PR `#3`

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
digest:    sha256:a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
result:    2/2 focused tests passed
```

### Transactional registry continuity — systemd PR `#9`

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
digest:    sha256:bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
result:    registry focused test passed
```

Executable contract: the still-connected old active generation remains writable while replacement is pending; the pending generation is blocked. The complete replacement snapshot atomically supersedes interim old-active values and makes the old generation stale.

Integration guard: registry ownership must remain serialized and non-reentrant, or validate/commit must become version-checked and atomic.

### Mixed-version grace — systemd PR `#20`

```text
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
result:    compatibility model passed with -Werror
```

Review repair: a newer pending generation must re-key and re-arm compatibility grace; otherwise the old timer becomes stale and disconnected old policy can survive forever.

### Registry grace transaction — systemd PR `#22`

```text
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
digest:    sha256:5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
result:    registry focused test passed
```

The actual lifecycle/registry model now supports matching grace expiry: withdraw retained old-authority policy, clear the disconnected old active generation, preserve the pending generation, and ignore stale or promoted timers.

## Active sender lane — systemd PR `#21`

The existing `ReportManagedOOMCGroups(cgroups: ControlGroup[])` method accepts `cgroups: []`; current old-server receive logic treats it as an empty iteration. The user-manager helper already supports empty construction.

The generated source change is only:

```text
manager_varlink_send_managed_oom_initial(): allow_empty=false -> true
```

Current head and gate:

```text
head: 50ed2893e37c66366401d51e4a9a579ad70a4210
run:  31020281327
state: queued at this handoff
```

Predecessor classifications:

- global injector uniqueness check was too broad; repaired by scoping it to the initial sender function;
- Meson target `systemd` was ambiguous; repaired to compile `./systemd:executable` explicitly.

Do not call this sender slice green until the exact-head compile receipt completes.

## Linux Fieldwork gate

The policy-model workflow now sends Python bytecode to runner temporary storage rather than dirtying the checkout. At `56a5c911ffe03f375e95a49839ecc04e3362e8d7`:

```text
policy model        30980834388  success
collision verifier  30980834339  success
Linux Fieldwork CI  30980834398  success
```

## Immediate engineering sequence

1. Inspect and record PR `#21` exact-head completion.
2. Build a controlled native oomd Varlink adapter lane around the proven registry components.
3. Attach `(authority, generation)` to each user-manager link.
4. Treat the first report on a link as complete authority state; treat later reports as incrementals.
5. Bind connect/disconnect callbacks and generation-keyed grace timers.
6. Re-key timers on superseding pending connections; cancel on promotion and disconnect; reject stale callbacks.
7. Handle PID 1 subscription termination and reconnect as the system authority lane.
8. Add cgroup-disappearance cleanup, effective-state timer preservation, and contributor diagnostics.
9. Run a native live VM matrix before promotion to the user's review desk.
10. Preserve exact-head receipts and keep all work internal until upstream contact is separately authorized.

## Read order

```text
README.md
DESIGN.md
IMPLEMENTATION.md
CONNECTION-LIFECYCLE.md
WIRE-COMPATIBILITY.md
INDEPENDENT-REVIEW-2026-08-05-CONTINUATION.md
```

## Authority

All writes and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No action has been taken in `systemd/systemd`.
