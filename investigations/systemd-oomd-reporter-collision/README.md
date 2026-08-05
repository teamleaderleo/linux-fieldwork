# systemd-oomd reporter collision across user-manager reload

Tracking: Linux Fieldwork issue `#140`, Linux Fieldwork PR `#245`, upstream report `systemd/systemd#43174`.  
Current review: `INDEPENDENT-REVIEW-2026-08-05-CONTINUATION.md`  
External contact: `false`

## Current status

`DEFECT REPRODUCED — BOUNDED LIVE CORRECTION GREEN — REDUCER, LIFECYCLE, REGISTRY, AND MIXED-VERSION GRACE MODELS GREEN — INITIAL-EMPTY SENDER GATE ACTIVE — NATIVE OOMD CALLBACK INTEGRATION NOT YET IMPLEMENTED`

Linux Fieldwork is the durable narrative and evidence home. `teamleaderleo/systemd` carries controlled executable experiments. Internal review is not upstream systemd approval.

## Defect and cause

A continuously running `user@<uid>.service` can disappear from systemd-oomd's monitored set after the nested user manager executes `daemon-reload` even though the service does not restart and its configured ManagedOOM policy remains `kill`.

PID 1 and the user manager can report the same kernel cgroup path. Current oomd receive state is keyed by property and path, while reporter identity is used for authorization but is not retained as policy ownership. A later user-manager `auto` therefore removes the shared path-level record, including PID 1's still-live contribution.

Baseline evidence:

```text
run:       30693755971
job:       91352945746
artifact:  8817102322
outcome:   reproduced
sha256:    c5257b5e3f230722d50f4f2f8a5a98ff94fc2fdc2644deecd4e9de5cd07c5aa9
```

Stable controls:

```text
ActiveEnterTimestampMonotonic 6615081 -> 6615081
NRestarts                    0 -> 0
ManagedOOMMemoryPressure     kill -> kill
```

Observed order:

```text
9.527279  PID 1: pressure=kill, limit=50%
9.552473  user manager: pressure=auto
10.524699 exact target path absent
```

## Selected architecture

```text
authority        = (SYSTEM_MANAGER | USER_MANAGER, uid)
contribution key = (authority, property, cgroup path)
effective key    = (property, cgroup path)
```

Required behavior:

- withdrawal affects only the sending authority;
- system-manager policy wins while present;
- a complete pressure tuple or complete rules list wins without field mixing;
- higher-authority withdrawal reveals an already-live fallback;
- the first report on a connection generation is a complete authoritative snapshot, including empty state;
- stale generations cannot update or withdraw current policy;
- current disconnect or stream termination withdraws only that authority;
- validation and allocation failures publish no partial policy transaction;
- effective no-op updates preserve timing state.

## Controlled executable lanes

### Baseline and reporter trace — `teamleaderleo/systemd#1`

Evidence-only reproduction and receive-boundary attribution.

### Bounded live source-precedence prototype — `teamleaderleo/systemd#2`

```text
head:            2f04a87e25df0d56f01cab5de8c99472806929a7
run:             30916547610
artifact:        8895926721
digest:          sha256:66ac9ee7c797dd776bb85c8705e93b4343deb8823b6bf6094ced10a6106c39d6
build:           557/557
unit:            test-oomd-util 1/1 passed
integration:     TEST-55-OOMD 1/1 passed in 35.59s
outcome:         fixed
```

The VM proves reload preservation, system-over-user precedence, user fallback after system withdrawal, and final removal after user withdrawal. This generated six-map slice is proof of behavior, not the final architecture.

### Policy reducer and reporter lifecycle — `teamleaderleo/systemd#3`

```text
head:      76749bfd3dda498c15a88c4e572340d8ade3e82b
run:       30915443613
artifact:  8894962609
digest:    sha256:a9e87098bcd7c9ef5ad154e2e884150233ed0cb09a53c203b378a1dc28db5f37
focused:   test-oomd-policy and test-oomd-reporter-lifecycle passed
```

This is an isolated model layer. It does not change live manager or Varlink behavior.

### Transactional reporter registry — `teamleaderleo/systemd#9`

```text
head:      247f546ae1a108df0d24ea1b74854b50539c05a4
run:       30978911539
artifact:  8919529118
digest:    sha256:bdfb0a47195b157ac1e8623f735a3d873b83095d2d4a99540c336b275a396ee2
focused:   test-oomd-reporter-registry 1/1 passed
```

The registry encapsulates policy and lifecycle state. Policy snapshot operations are copy-and-swap internally; lifecycle promotion or withdrawal commits only after policy mutation succeeds. The contract depends on serialized non-reentrant registry ownership.

Review corrected reconnect wording and added a test proving that a still-connected old active generation remains writable while replacement is pending; the pending generation is blocked until its authoritative snapshot commits, which atomically replaces interim state and makes the old generation stale.

### Mixed-version initialization grace — `teamleaderleo/systemd#20`

```text
head:      bca6cedb1904aa1a9af56c2076bea6e156b04d26
run:       30979635398
artifact:  8919990350
digest:    sha256:11981b8da73450f2e9680f14652746b8ba0b573bd38762dc38f78ad73e7ca55c
focused:   compatibility model passed with -Wall -Wextra -Werror
```

This model handles old clients that cannot send an empty initial report. It retains disconnected old policy for a bounded generation-keyed grace. Review found and repaired a substantive bug where a newer pending connection could orphan the grace and retain stale policy forever; grace is now re-keyed to the newest pending generation.

### Registry grace-expiry transaction — `teamleaderleo/systemd#22`

```text
head:      06f0add4bdb24c0185a091b0b4cf63aaad8266b5
run:       30980672145
artifact:  8921163776
digest:    sha256:5eae85dfbcf07fb46f0b4bdb4d573de5919092a77c44bd9ba8fe43f17ab22b86
focused:   test-oomd-reporter-registry 1/1 passed
```

The actual lifecycle and registry components now expose the transaction a live generation-keyed timer must invoke. Matching expiry withdraws retained policy and clears only the disconnected old active generation while preserving the pending connection. Timer scheduling and live callbacks remain outside this slice.

### Initial-empty user-manager sender — `teamleaderleo/systemd#21`

The existing method already accepts:

```text
io.systemd.oom.ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

An empty array is valid and is a harmless no-op for an older oomd receiver. The user-manager helper already supports empty construction. The generated sender slice changes only the initial call from `allow_empty=false` to `allow_empty=true`.

Current validation head:

```text
head: 50ed2893e37c66366401d51e4a9a579ad70a4210
run:  31020281327
state: queued at this checkpoint
```

Earlier runs repaired two harness defects: an injector uniqueness check that was scoped too broadly, and an ambiguous Meson `systemd` target now replaced by `./systemd:executable`. No product-source failure has been observed in those predecessor runs.

## Wire compatibility

New clients do not need a second Varlink method merely to express an empty initial state:

- new user manager to old oomd: `cgroups: []` is accepted as a no-op;
- old non-empty user manager to new oomd: its first existing complete report can initialize the generation;
- old empty user manager to new oomd: it sends nothing, so bounded compatibility grace remains necessary.

See `WIRE-COMPATIBILITY.md`.

## Linux Fieldwork checks

The policy-model workflow was repaired to place Python bytecode outside the checkout. At head `56a5c911ffe03f375e95a49839ecc04e3362e8d7`:

```text
Verify systemd-oomd policy model       30980834388  success
Verify systemd-oomd reporter collision 30980834339  success
Linux Fieldwork CI                     30980834398  success
```

## Durable records

```text
DESIGN.md
IMPLEMENTATION.md
CONNECTION-LIFECYCLE.md
PROTOTYPE-AUDIT.md
C-REDUCER.md
WIRE-COMPATIBILITY.md
INDEPENDENT-REVIEW-2026-08-04.md
INDEPENDENT-REVIEW-2026-08-05.md
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
- Initial-empty sender: **exact-head compile gate active**.
- Native oomd callback and timer integration: **not implemented**.
- Upstream-shaped candidate: **not ready**.
- Upstream contact: **none**.

## Next engineering move

Finish the sender gate, then build a controlled native adapter lane around the registry: per-link authority/generation userdata, first-report versus incremental classification, connect/disconnect callbacks, generation-keyed grace timers, PID 1 stream loss/reconnect, cgroup cleanup, timing preservation, and contributor diagnostics. A native VM matrix is required before promotion to the user's review desk.

## Authority

All writes, reviews, and execution are confined to `teamleaderleo/linux-fieldwork` and `teamleaderleo/systemd`. No issue comment, pull request, review, reaction, patch submission, email, or other action has been made in `systemd/systemd`.
